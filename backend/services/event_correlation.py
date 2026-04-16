from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from typing import Any, Deque, Dict, Iterable, Optional, Tuple
from uuid import uuid4

from utils.time_filter import parse_timestamp_to_utc


@dataclass
class _Event:
    event_id: str
    service: str
    template: str
    start_time: datetime
    end_time: datetime
    logs: list[dict[str, Any]]


class EventCorrelator:
    """
    Correlates structured logs into higher-level events.

    Clustering dimensions:
    - time proximity (within window_seconds)
    - similar templates (exact match preferred; optional fuzzy similarity)
    - service/component name
    """

    def __init__(
        self,
        *,
        window_seconds: int = 30,
        template_similarity_threshold: float = 1.0,
        service_keys: tuple[str, ...] = ("service", "component", "source", "logger", "app", "svc"),
        timestamp_key: str = "timestamp",
        template_key: str = "template",
        max_fuzzy_candidates_per_service: int = 25,
        include_untimed: bool = False,
    ) -> None:
        self.window_seconds = max(0, int(window_seconds))
        self.template_similarity_threshold = float(template_similarity_threshold)
        self.service_keys = service_keys
        self.timestamp_key = timestamp_key
        self.template_key = template_key
        self.max_fuzzy_candidates_per_service = max(1, int(max_fuzzy_candidates_per_service))
        self.include_untimed = include_untimed

    def correlate(self, structured_logs: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        window = timedelta(seconds=self.window_seconds)

        # Parse and sort once to allow linear-time clustering.
        timed: list[tuple[datetime, dict[str, Any]]] = []
        untimed: list[dict[str, Any]] = []

        reference_year: Optional[int] = None
        for log in structured_logs:
            ts_raw = log.get(self.timestamp_key)
            ts = parse_timestamp_to_utc(ts_raw, reference_year=reference_year)
            if ts is None:
                untimed.append(log)
                continue
            if reference_year is None:
                reference_year = ts.year
            timed.append((ts, log))

        timed.sort(key=lambda pair: pair[0])

        # Active events per service for fuzzy matching. Deques are kept time-window bounded.
        active_by_service: Dict[str, Deque[_Event]] = defaultdict(deque)
        # Fast path: last event for exact (service, template).
        last_by_key: Dict[Tuple[str, str], _Event] = {}
        # Output in chronological creation order.
        events: list[_Event] = []

        for ts, log in timed:
            service = _extract_service(log, self.service_keys)
            template = str(log.get(self.template_key) or "")
            if not template:
                template = str(log.get("message") or log.get("msg") or "")

            # Prune old active events for this service to keep fuzzy matching cheap.
            service_deque = active_by_service[service]
            cutoff = ts - window
            while service_deque and service_deque[0].end_time < cutoff:
                service_deque.popleft()

            # Exact template match path.
            exact_key = (service, template)
            exact_event = last_by_key.get(exact_key)
            if exact_event is not None and (ts - exact_event.end_time) <= window:
                exact_event.logs.append(log)
                exact_event.end_time = ts
                continue

            # Optional fuzzy matching against recent events in the same service.
            matched_event: Optional[_Event] = None
            if self.template_similarity_threshold < 1.0 and service_deque:
                matched_event = _find_fuzzy_match(
                    template=template,
                    candidates=service_deque,
                    ts=ts,
                    window=window,
                    threshold=self.template_similarity_threshold,
                    max_candidates=self.max_fuzzy_candidates_per_service,
                )

            if matched_event is not None:
                matched_event.logs.append(log)
                matched_event.end_time = ts
                # Keep exact map updated for future exact hits.
                last_by_key[(service, matched_event.template)] = matched_event
                continue

            # Create a new event.
            new_event = _Event(
                event_id=uuid4().hex,
                service=service,
                template=template,
                start_time=ts,
                end_time=ts,
                logs=[log],
            )
            events.append(new_event)
            service_deque.append(new_event)
            last_by_key[exact_key] = new_event

        # Optionally include untimed logs as best-effort singleton events.
        if self.include_untimed and untimed:
            for log in untimed:
                service = _extract_service(log, self.service_keys)
                template = str(log.get(self.template_key) or "")
                if not template:
                    template = str(log.get("message") or log.get("msg") or "unknown")
                now = datetime.now(tz=timezone.utc)
                events.append(
                    _Event(
                        event_id=uuid4().hex,
                        service=service,
                        template=template,
                        start_time=now,
                        end_time=now,
                        logs=[log],
                    )
                )

        return [
            {
                "event_id": ev.event_id,
                "logs": ev.logs,
                "start_time": _to_iso_z(ev.start_time),
                "end_time": _to_iso_z(ev.end_time),
            }
            for ev in events
        ]


def correlate_events(
    structured_logs: Iterable[dict[str, Any]],
    *,
    window_seconds: int = 30,
    template_similarity_threshold: float = 1.0,
    service_keys: tuple[str, ...] = ("service", "component", "source", "logger", "app", "svc"),
) -> list[dict[str, Any]]:
    return EventCorrelator(
        window_seconds=window_seconds,
        template_similarity_threshold=template_similarity_threshold,
        service_keys=service_keys,
    ).correlate(structured_logs)


def _extract_service(log: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = log.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "unknown"


def _find_fuzzy_match(
    *,
    template: str,
    candidates: deque[_Event],
    ts: datetime,
    window: timedelta,
    threshold: float,
    max_candidates: int,
) -> Optional[_Event]:
    # Search newest-to-oldest to bias toward the most recent active event.
    best_event: Optional[_Event] = None
    best_score = threshold

    checked = 0
    for ev in reversed(candidates):
        if (ts - ev.end_time) > window:
            break
        checked += 1
        if checked > max_candidates:
            break

        score = _template_similarity(template, ev.template)
        if score >= best_score:
            best_score = score
            best_event = ev

    return best_event


def _template_similarity(a: str, b: str) -> float:
    if a == b:
        return 1.0
    # SequenceMatcher is O(n)ish and good enough for short templates.
    return SequenceMatcher(None, a, b).ratio()


def _to_iso_z(dt: datetime) -> str:
    utc_dt = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return utc_dt.isoformat().replace("+00:00", "Z")
