from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Optional, Set

from utils.time_filter import parse_timestamp_to_utc


_ERROR_LEVELS = {"ERROR", "FATAL", "CRITICAL", "PANIC"}
_WARN_LEVELS = {"WARN", "WARNING"}


@dataclass(frozen=True)
class RankedRootCause:
    event_id: str
    score: float
    reason: str


class RootCauseDetector:
    """
    Simple statistical anomaly scoring to rank correlated events as root-cause candidates.

    Heuristic signals per event:
    - error ratio (ERROR/FATAL/CRITICAL)
    - error count
    - log volume
    - event duration
    - (small) preference for earlier events in the incident window

    Scoring is robust (median/MAD), then mapped to [0,1] via a sigmoid.
    """

    def __init__(
        self,
        *,
        error_levels: Optional[Set[str]] = None,
        warn_levels: Optional[Set[str]] = None,
        timestamp_key: str = "timestamp",
        level_key: str = "log_level",
        window_earliness_weight: float = 0.25,
    ) -> None:
        self.error_levels = {lvl.upper() for lvl in (error_levels or _ERROR_LEVELS)}
        self.warn_levels = {lvl.upper() for lvl in (warn_levels or _WARN_LEVELS)}
        self.timestamp_key = timestamp_key
        self.level_key = level_key
        self.window_earliness_weight = float(window_earliness_weight)

    def rank(self, correlated_events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        events = list(correlated_events)
        if not events:
            return []

        feature_rows: list[_Features] = []
        for ev in events:
            feature_rows.append(self._extract_features(ev))

        # Robust stats for anomaly scoring.
        log_counts = [row.log_count for row in feature_rows]
        error_counts = [row.error_count for row in feature_rows]
        error_ratios = [row.error_ratio for row in feature_rows]
        durations = [row.duration_seconds for row in feature_rows]

        stats = _StatsBundle(
            log_count=_robust_stats(log_counts),
            error_count=_robust_stats(error_counts),
            error_ratio=_robust_stats(error_ratios),
            duration=_robust_stats(durations),
        )

        # Determine incident window start for "earliness" tie-break.
        incident_start = min((row.start_time for row in feature_rows if row.start_time is not None), default=None)
        incident_end = max((row.end_time for row in feature_rows if row.end_time is not None), default=None)
        window_seconds = None
        if incident_start is not None and incident_end is not None and incident_end >= incident_start:
            window_seconds = max(1.0, (incident_end - incident_start).total_seconds())

        ranked: list[RankedRootCause] = []
        for ev, row in zip(events, feature_rows):
            z_log = _positive_z(row.log_count, stats.log_count)
            z_err = _positive_z(row.error_count, stats.error_count)
            z_ratio = _positive_z(row.error_ratio, stats.error_ratio)
            z_dur = _positive_z(row.duration_seconds, stats.duration)

            # Weighted sum; ratio and errors dominate.
            raw_score = (1.4 * z_ratio) + (1.2 * z_err) + (0.7 * z_log) + (0.5 * z_dur)

            # Earlier events get a small boost (root causes are often upstream in time).
            if window_seconds and incident_start and row.start_time:
                earliness = 1.0 - ((row.start_time - incident_start).total_seconds() / window_seconds)
                raw_score += self.window_earliness_weight * max(0.0, min(1.0, earliness))

            probability = _sigmoid(raw_score)
            reason = _build_reason(row, z_ratio=z_ratio, z_err=z_err, z_log=z_log, z_dur=z_dur)
            ranked.append(
                RankedRootCause(
                    event_id=str(ev.get("event_id") or ""),
                    score=float(probability),
                    reason=reason,
                )
            )

        ranked.sort(key=lambda r: r.score, reverse=True)
        return [{"event_id": r.event_id, "score": r.score, "reason": r.reason} for r in ranked]

    def _extract_features(self, event: dict[str, Any]) -> "_Features":
        start_time = _parse_event_time(event.get("start_time"))
        end_time = _parse_event_time(event.get("end_time"))
        if start_time and end_time and end_time < start_time:
            start_time, end_time = end_time, start_time

        logs = event.get("logs") or []
        if not isinstance(logs, list):
            logs = []

        log_count = len(logs)
        error_count = 0
        warn_count = 0
        first_error_ts: Optional[datetime] = None

        for log in logs:
            if not isinstance(log, dict):
                continue
            level_raw = log.get(self.level_key)
            level = str(level_raw).upper() if level_raw is not None else ""
            if level in self.error_levels:
                error_count += 1
                if first_error_ts is None:
                    ts = parse_timestamp_to_utc(log.get(self.timestamp_key))
                    first_error_ts = ts
            elif level in self.warn_levels:
                warn_count += 1

        error_ratio = (error_count / log_count) if log_count else 0.0

        duration_seconds = 0.0
        if start_time and end_time:
            duration_seconds = max(0.0, (end_time - start_time).total_seconds())

        return _Features(
            start_time=start_time,
            end_time=end_time,
            log_count=log_count,
            error_count=error_count,
            warn_count=warn_count,
            error_ratio=error_ratio,
            duration_seconds=duration_seconds,
            first_error_time=first_error_ts,
        )


def rank_root_causes(correlated_events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return RootCauseDetector().rank(correlated_events)


@dataclass(frozen=True)
class _Features:
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    log_count: int
    error_count: int
    warn_count: int
    error_ratio: float
    duration_seconds: float
    first_error_time: Optional[datetime]


@dataclass(frozen=True)
class _RobustStats:
    median: float
    mad: float


@dataclass(frozen=True)
class _StatsBundle:
    log_count: _RobustStats
    error_count: _RobustStats
    error_ratio: _RobustStats
    duration: _RobustStats


def _parse_event_time(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    # ISO Z handling
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return parse_timestamp_to_utc(text)


def _robust_stats(values: list[float]) -> _RobustStats:
    if not values:
        return _RobustStats(median=0.0, mad=1.0)
    sorted_vals = sorted(float(v) for v in values)
    med = _median(sorted_vals)
    deviations = [abs(v - med) for v in sorted_vals]
    mad = _median(sorted(deviations))
    # Avoid divide-by-zero; 1e-9 keeps z stable.
    return _RobustStats(median=med, mad=max(mad, 1e-9))


def _median(sorted_values: list[float]) -> float:
    n = len(sorted_values)
    if n == 0:
        return 0.0
    mid = n // 2
    if n % 2 == 1:
        return sorted_values[mid]
    return (sorted_values[mid - 1] + sorted_values[mid]) / 2.0


def _positive_z(value: float, stats: _RobustStats) -> float:
    # Robust z: (x - median) / (1.4826 * MAD)
    z = (float(value) - stats.median) / (1.4826 * stats.mad)
    return max(0.0, z)


def _sigmoid(x: float) -> float:
    # Stable-ish sigmoid.
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def _build_reason(row: _Features, *, z_ratio: float, z_err: float, z_log: float, z_dur: float) -> str:
    parts: list[str] = []

    if row.log_count == 0:
        return "Empty event (no logs)."

    if row.error_count > 0:
        parts.append(f"Contains {row.error_count} error-level logs ({row.error_ratio:.0%} of event).")
    elif row.warn_count > 0:
        parts.append(f"Contains {row.warn_count} warning-level logs.")
    else:
        parts.append("No explicit error-level logs detected.")

    contributions: list[tuple[str, float]] = [
        ("high error ratio", z_ratio),
        ("high error count", z_err),
        ("high log volume", z_log),
        ("long duration", z_dur),
    ]
    contributions.sort(key=lambda pair: pair[1], reverse=True)

    top = [label for label, score in contributions[:2] if score > 0.5]
    if top:
        parts.append("Anomalies: " + ", ".join(top) + ".")

    if row.first_error_time is not None:
        parts.append(f"First error observed at {row.first_error_time.isoformat().replace('+00:00', 'Z')}.")

    return " ".join(parts)
