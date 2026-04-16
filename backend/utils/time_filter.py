from __future__ import annotations

import re
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Iterable, Optional, Union


_EPOCH_RE = re.compile(r"^\d{10}(?:\.\d+)?$|^\d{13}$")

# ISO-ish datetimes. We also support minute-resolution inputs like `2026-04-16T09:10`
# which come from `<input type="datetime-local">`.
_ISO_DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")

# Syslog-ish: "Apr 16 09:15:12" (no year / tz)
_SYSLOG_RE = re.compile(r"^(?P<mon>[A-Z][a-z]{2})\s+(?P<day>\d{1,2})\s+(?P<hms>\d{2}:\d{2}:\d{2})$")

_MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


def filter_logs_by_timestamp(
    structured_logs: Iterable[dict[str, Any]],
    start_timestamp: Union[str, datetime],
    end_timestamp: Union[str, datetime],
) -> list[dict[str, Any]]:
    """
    Filters structured log dicts by their "timestamp" field, inclusive.

    - Supports multiple timestamp formats (ISO-8601 variants, epoch seconds/millis, syslog "Mon DD HH:MM:SS").
    - Timezone-safe: comparisons are done on timezone-aware datetimes in UTC.
    - For timestamps without timezone info, UTC is assumed.
    - For syslog timestamps without a year, the year is inferred from start_timestamp (else current year).
    """

    start_dt = _to_utc_datetime(start_timestamp)
    end_dt = _to_utc_datetime(end_timestamp)
    if start_dt > end_dt:
        start_dt, end_dt = end_dt, start_dt

    inferred_year = start_dt.year
    out: list[dict[str, Any]] = []
    append = out.append

    for item in structured_logs:
        raw_ts = item.get("timestamp")
        ts = _to_utc_datetime(raw_ts, reference_year=inferred_year)
        if ts is None:
            continue
        if start_dt <= ts <= end_dt:
            append(item)

    return out


def parse_timestamp_to_utc(value: Any, *, reference_year: Optional[int] = None) -> Optional[datetime]:
    """
    Parse a timestamp value into a timezone-aware UTC datetime, or None if unparsable.
    """
    return _to_utc_datetime(value, reference_year=reference_year)


def _to_utc_datetime(
    value: Any,
    *,
    reference_year: Optional[int] = None,
) -> Optional[datetime]:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)

    if isinstance(value, (int, float)):
        return _epoch_to_datetime(value)

    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    return _parse_timestamp(text, reference_year=reference_year)


def _epoch_to_datetime(value: Union[int, float]) -> datetime:
    # Heuristic: treat 13-digit numbers as milliseconds.
    if value > 10_000_000_000:  # > year ~2286 in seconds, likely millis
        return datetime.fromtimestamp(value / 1000.0, tz=timezone.utc)
    return datetime.fromtimestamp(value, tz=timezone.utc)


@lru_cache(maxsize=65536)
def _parse_timestamp(text: str, reference_year: Optional[int]) -> Optional[datetime]:
    # Epoch seconds / millis
    if _EPOCH_RE.match(text):
        try:
            if len(text) == 13 and text.isdigit():
                return datetime.fromtimestamp(int(text) / 1000.0, tz=timezone.utc)
            return datetime.fromtimestamp(float(text), tz=timezone.utc)
        except ValueError:
            return None

    # ISO-like candidates (including minute precision, with/without timezone)
    if _ISO_DATE_PREFIX_RE.match(text) and ":" in text:
        normalized = text.replace("Z", "+00:00")
        if " " in normalized and "T" not in normalized:
            normalized = normalized.replace(" ", "T", 1)

        try:
            dt = datetime.fromisoformat(normalized)
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass

        # Fallback strptimes for a few common variants.
        for fmt in (
            "%Y-%m-%dT%H:%M",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
        ):
            try:
                dt = datetime.strptime(normalized, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

    # Syslog-ish (no year / tz)
    syslog_match = _SYSLOG_RE.match(text)
    if syslog_match:
        year = reference_year or datetime.now(tz=timezone.utc).year
        month = _MONTHS.get(syslog_match.group("mon"))
        if not month:
            return None
        day = int(syslog_match.group("day"))
        hms = syslog_match.group("hms")
        try:
            dt = datetime.strptime(f"{year:04d}-{month:02d}-{day:02d} {hms}", "%Y-%m-%d %H:%M:%S")
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    return None
