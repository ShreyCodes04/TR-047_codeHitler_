from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

from pydantic import BaseModel, Field

from utils.settings import settings
from utils.time_filter import parse_timestamp_to_utc


class TimelineItem(BaseModel):
    time: str = Field(description="ISO-8601 timestamp (UTC preferred) or best available time string.")
    event_id: str
    summary: str


class PostmortemJSON(BaseModel):
    summary: str
    timeline: list[TimelineItem]
    root_cause: str
    impact: str
    action_items: list[str]


@dataclass(frozen=True)
class LLMInputs:
    architecture_description: str
    correlated_events: list[dict[str, Any]]
    suspected_root_causes: list[dict[str, Any]]


def generate_sre_postmortem(inputs: LLMInputs) -> dict[str, Any]:
    """
    Groq + LangChain report generator.

    Input:
    - architecture description
    - correlated events
    - suspected root causes (ranked)

    Output (JSON):
      {
        "summary": "",
        "timeline": [{ "time": "", "event_id": "", "summary": "" }],
        "root_cause": "",
        "impact": "",
        "action_items": []
      }
    """

    llm = _build_llm()
    prompt_input = _build_prompt_input(inputs)

    # Lazy imports keep the module importable even before deps are installed.
    from langchain_core.output_parsers import JsonOutputParser
    from langchain_core.prompts import ChatPromptTemplate

    parser: JsonOutputParser = JsonOutputParser(pydantic_object=PostmortemJSON)
    format_instructions = parser.get_format_instructions()

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "\n".join(
                    [
                        "You are a senior Site Reliability Engineer (SRE) writing a blameless incident postmortem.",
                        "Your job is to correlate events, pick the most likely root-cause chain, describe impact, and propose precise action items.",
                        "Be factual and specific. If you must assume, say so explicitly.",
                        "Output MUST be valid JSON only (no markdown, no extra keys, no trailing commentary).",
                        "Keep it deterministic: do not invent metrics; prefer 'Unknown' when data is missing.",
                    ]
                ),
            ),
            (
                "user",
                "\n".join(
                    [
                        "Architecture description:",
                        "{architecture}",
                        "",
                        "Correlated events (compressed):",
                        "{events_json}",
                        "",
                        "Suspected root causes (ranked):",
                        "{root_causes_json}",
                        "",
                        "Instructions:",
                        "- Use the ranked suspected root causes as hints, but you can disagree if evidence suggests otherwise.",
                        "- Build a short timeline using the correlated events (chronological).",
                        "- Root cause should describe the causal chain, not just the symptom.",
                        "- Action items must be concrete and testable.",
                        "",
                        "{format_instructions}",
                    ]
                ),
            ),
        ]
    )

    chain = prompt | llm | parser
    result = chain.invoke(
        {
            "architecture": inputs.architecture_description.strip() or "Unknown",
            "events_json": json.dumps(prompt_input.events, ensure_ascii=True),
            "root_causes_json": json.dumps(prompt_input.root_causes, ensure_ascii=True),
            "format_instructions": format_instructions,
        }
    )

    # JsonOutputParser returns a dict, but we validate to enforce schema.
    validated = PostmortemJSON.model_validate(result)
    return validated.model_dump()


def _build_llm():
    provider = settings.llm_provider
    if provider not in {"auto", "groq", "gemini"}:
        provider = "auto"

    if provider == "groq":
        return _build_groq_llm()
    if provider == "gemini":
        return _build_gemini_llm()

    if settings.groq_api_key:
        return _build_groq_llm()
    if settings.google_api_key or settings.gemini_api_key:
        return _build_gemini_llm()

    raise RuntimeError(
        "Missing GROQ_API_KEY or GOOGLE_API_KEY or GEMINI_API_KEY in environment."
    )


def _build_groq_llm():
    if not settings.groq_api_key:
        raise RuntimeError("Missing GROQ_API_KEY in environment.")

    try:
        from langchain_groq import ChatGroq
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "langchain-groq is not installed. Add it to requirements and install deps."
        ) from exc

    return ChatGroq(
        model=settings.groq_model,
        api_key=settings.groq_api_key,
        temperature=0,
        max_retries=2,
        timeout=float(settings.llm_timeout_seconds),
    )


def _build_gemini_llm():
    api_key = settings.google_api_key or settings.gemini_api_key
    if not api_key:
        raise RuntimeError("Missing GOOGLE_API_KEY or GEMINI_API_KEY in environment.")

    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "langchain-google-genai is not installed. Add it to requirements and install deps."
        ) from exc

    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        api_key=api_key,
        temperature=0,
        retries=2,
        request_timeout=float(settings.llm_timeout_seconds),
        response_mime_type="application/json",
    )


@dataclass(frozen=True)
class _PromptInput:
    events: list[dict[str, Any]]
    root_causes: list[dict[str, Any]]


def _build_prompt_input(inputs: LLMInputs) -> _PromptInput:
    # Compress correlated events aggressively to keep token usage sane for large incidents.
    events = _compress_events(
        inputs.correlated_events,
        max_events=settings.llm_max_events,
        max_logs_per_event=settings.llm_max_logs_per_event,
    )

    # Root causes already ranked; keep top-N and trim reasons.
    root_causes: list[dict[str, Any]] = []
    for item in inputs.suspected_root_causes[: min(10, len(inputs.suspected_root_causes))]:
        if not isinstance(item, dict):
            continue
        root_causes.append(
            {
                "event_id": str(item.get("event_id") or ""),
                "score": float(item.get("score") or 0.0),
                "reason": str(item.get("reason") or "")[:400],
            }
        )

    return _PromptInput(events=events, root_causes=root_causes)


def _compress_events(
    correlated_events: list[dict[str, Any]],
    *,
    max_events: int,
    max_logs_per_event: int,
) -> list[dict[str, Any]]:
    rows: list[tuple[Any, dict[str, Any]]] = []

    reference_year: Optional[int] = None
    for ev in correlated_events:
        if not isinstance(ev, dict):
            continue
        start = parse_timestamp_to_utc(ev.get("start_time"), reference_year=reference_year)
        if start is not None and reference_year is None:
            reference_year = start.year
        rows.append((start or ev.get("start_time") or "", ev))

    # Sort chronologically where possible.
    rows.sort(key=lambda pair: (pair[0] is None, pair[0]))

    compressed: list[dict[str, Any]] = []
    for _, ev in rows[:max_events]:
        event_id = str(ev.get("event_id") or "")
        start_time = str(ev.get("start_time") or "")
        end_time = str(ev.get("end_time") or "")
        logs = ev.get("logs") or []
        if not isinstance(logs, list):
            logs = []

        sample_logs: list[dict[str, Any]] = []
        for log in logs[:max_logs_per_event]:
            if not isinstance(log, dict):
                continue
            sample_logs.append(
                {
                    "timestamp": log.get("timestamp"),
                    "service": log.get("service") or log.get("component") or log.get("source"),
                    "log_level": log.get("log_level"),
                    "template": log.get("template"),
                    "variables": log.get("variables"),
                    "message": (log.get("message") or log.get("msg") or ""),
                }
            )

        compressed.append(
            {
                "event_id": event_id,
                "start_time": start_time,
                "end_time": end_time,
                "log_count": len(logs),
                "samples": sample_logs,
            }
        )

    return compressed
