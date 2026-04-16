from __future__ import annotations

import logging
import codecs
import asyncio
from datetime import timezone
from pathlib import Path
from typing import Any, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from services.event_correlation import correlate_events
from services.llm_postmortem import LLMInputs, generate_sre_postmortem
from services.log_parser import LogParser
from services.root_cause import rank_root_causes
from utils.time_filter import parse_timestamp_to_utc


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/generate-report")
async def generate_report(
    # Accept both field names for compatibility: "logs" (frontend snippet) and "files".
    logs: Optional[List[UploadFile]] = File(None),
    files: Optional[List[UploadFile]] = File(None),
    start_time: str = Form(...),
    end_time: str = Form(...),
    # Accept both field names: "architecture" and "architecture_description".
    architecture: Optional[str] = Form(None),
    architecture_description: Optional[str] = Form(None),
) -> dict[str, Any]:
    selected_files = (logs or []) + (files or [])
    if not selected_files:
        raise HTTPException(
            status_code=400,
            detail="No files uploaded. Use form field name 'logs' (preferred) or 'files'.",
        )

    arch = (architecture_description or architecture or "").strip()
    if not arch:
        raise HTTPException(status_code=400, detail="Architecture description is required.")

    start_dt = parse_timestamp_to_utc(start_time)
    end_dt = parse_timestamp_to_utc(end_time)
    if start_dt is None or end_dt is None:
        raise HTTPException(status_code=400, detail="start_time/end_time must be valid timestamps.")
    if start_dt > end_dt:
        start_dt, end_dt = end_dt, start_dt

    parser = LogParser()
    filtered_logs: list[dict[str, Any]] = []
    reference_year = start_dt.year

    try:
        for upload in selected_files:
            filename = upload.filename or "upload.log"
            service_name = Path(filename).stem or "unknown"

            async for line in _iter_upload_lines(upload):
                structured = parser.parse_line(line)
                structured["source"] = filename
                structured["service"] = service_name

                ts = parse_timestamp_to_utc(structured.get("timestamp"), reference_year=reference_year)
                if ts is None:
                    continue
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if start_dt <= ts <= end_dt:
                    filtered_logs.append(structured)
    finally:
        for upload in selected_files:
            try:
                await upload.close()
            except Exception:
                pass

    if not filtered_logs:
        raise HTTPException(status_code=422, detail="No logs found within the provided time range.")

    # 3) Correlate events
    events = correlate_events(filtered_logs, window_seconds=30, template_similarity_threshold=1.0)
    # 4) Root cause scoring
    suspected = rank_root_causes(events)

    # 5) LLM report: run in worker thread since LangChain calls are blocking.
    try:
        report = await asyncio.to_thread(
            generate_sre_postmortem,
            LLMInputs(
                architecture_description=arch,
                correlated_events=events,
                suspected_root_causes=suspected,
            ),
        )
    except RuntimeError as exc:
        # Common misconfig: missing key/env. Return 400 so the UI can display a clear fix.
        msg = str(exc)
        logger.exception("LLM report generation failed (runtime)")
        if (
            "Missing GOOGLE_API_KEY or GEMINI_API_KEY" in msg
            or "Missing GROQ_API_KEY" in msg
            or "Missing GROQ_API_KEY or GOOGLE_API_KEY or GEMINI_API_KEY" in msg
        ):
            raise HTTPException(
                status_code=400,
                detail="Missing LLM API key. Set GROQ_API_KEY, or GEMINI_API_KEY/GOOGLE_API_KEY in backend/.env, then restart the server.",
            ) from exc
        raise HTTPException(status_code=502, detail=f"LLM runtime error: {msg}") from exc
    except Exception as exc:
        logger.exception("LLM report generation failed")
        error_type = type(exc).__name__
        detail = f"LLM report generation failed: {error_type}. Check server logs for details."
        if error_type == "ResourceExhausted":
            detail = (
                "Gemini quota or model capacity was exhausted. Try again in a minute, "
                "use a different API key/project with available quota, or reduce the report size."
            )
        raise HTTPException(
            status_code=429 if error_type == "ResourceExhausted" else 502,
            detail=detail,
        ) from exc

    # 6) Return JSON
    return report


async def _iter_upload_lines(upload: UploadFile, *, chunk_size: int = 1024 * 1024):
    decoder = codecs.getincrementaldecoder("utf-8")("ignore")
    text_buf = ""

    while True:
        chunk = await upload.read(chunk_size)
        if not chunk:
            break
        text_buf += decoder.decode(chunk)
        while True:
            idx = text_buf.find("\n")
            if idx == -1:
                break
            line = text_buf[:idx]
            text_buf = text_buf[idx + 1 :]
            yield line.rstrip("\r")

    # Flush decoder and remaining buffer
    text_buf += decoder.decode(b"", final=True)
    if text_buf:
        for line in text_buf.splitlines():
            if line:
                yield line.rstrip("\r")


def _event_summary(ev: dict[str, Any]) -> str:
    logs = ev.get("logs") or []
    if isinstance(logs, list) and logs:
        first = logs[0]
        if isinstance(first, dict):
            template = first.get("template")
            if isinstance(template, str) and template:
                return template[:200]
    return "Correlated event"
