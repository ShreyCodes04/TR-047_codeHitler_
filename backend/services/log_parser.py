from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Optional, Tuple

from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig


_TS_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d{3,6})?(?:Z|[+-]\d{2}:?\d{2})?)\s+"
)
_LVL_RE = re.compile(r"^(?:\[(?P<lvl1>[A-Z]+)\]|(?P<lvl2>[A-Z]+))\b[:\-]?\s*")


@dataclass(frozen=True)
class ParsedLog:
    timestamp: Optional[str]
    level: Optional[str]
    template: str
    variables: list[str]


class LogParser:
    """
    Drain3-backed log parser.

    Input: raw log lines
    Output: structured dicts with timestamp, level, template, and extracted variables
    """

    def __init__(
        self,
        *,
        drain_depth: int = 4,
        similarity_threshold: float = 0.4,
        max_children: int = 100,
        max_clusters: int = 20000,
    ) -> None:
        config = TemplateMinerConfig()
        # Keep config in-memory and tuned for streaming large logs.
        config.drain_depth = drain_depth
        config.drain_similarity_threshold = similarity_threshold
        config.drain_max_children = max_children
        config.max_clusters = max_clusters
        config.snapshot_interval_minutes = 0  # no periodic snapshots by default

        self._miner = TemplateMiner(config=config)

    def parse_logs(self, log_lines: List[str]) -> List[dict]:
        results: list[dict] = []
        append = results.append

        for line in log_lines:
            if not line:
                continue
            append(self.parse_line(line))

        return results

    def parse_line(self, line: str) -> dict:
        parsed = self._parse_line(line.rstrip("\n"))
        return {
            "timestamp": parsed.timestamp,
            "log_level": parsed.level,
            "template": parsed.template,
            "variables": parsed.variables,
            "message": self._strip_prefixes(line),
        }

    def _parse_line(self, line: str) -> ParsedLog:
        timestamp, remainder = self._extract_timestamp(line)
        level, message = self._extract_level(remainder)

        # Feed only the message portion into Drain3 so templates are stable across timestamps/levels.
        message_for_mining = message if message else remainder
        template = self._mine_template(message_for_mining)
        variables = self._extract_variables(template, message_for_mining)

        return ParsedLog(
            timestamp=timestamp,
            level=level,
            template=template,
            variables=variables,
        )

    def _strip_prefixes(self, line: str) -> str:
        # Best-effort: remove leading timestamp + level so "message" stays stable.
        _, remainder = self._extract_timestamp(line)
        _, message = self._extract_level(remainder)
        return message

    def _extract_timestamp(self, line: str) -> Tuple[Optional[str], str]:
        match = _TS_RE.match(line)
        if not match:
            return None, line.lstrip()
        return match.group("ts"), line[match.end() :].lstrip()

    def _extract_level(self, text: str) -> Tuple[Optional[str], str]:
        match = _LVL_RE.match(text)
        if not match:
            return None, text.lstrip()
        level = match.group("lvl1") or match.group("lvl2")
        return level, text[match.end() :].lstrip()

    def _mine_template(self, message: str) -> str:
        result = self._miner.add_log_message(message)

        cluster = None
        if isinstance(result, dict):
            cluster = result.get("cluster")

        if cluster is not None and hasattr(cluster, "get_template"):
            return cluster.get_template()

        # Fallback: keep message as template if Drain3 doesn't return a cluster (should be rare).
        return message

    def _extract_variables(self, template: str, message: str) -> list[str]:
        if "<*>" not in template:
            return []

        regex = self._template_to_regex(template)
        match = regex.match(message)
        if not match:
            return []

        # Return vars in order: v0, v1, ...
        groups: list[str] = []
        for key in sorted(match.groupdict().keys(), key=lambda k: int(k[1:])):
            groups.append(match.group(key))
        return groups

    @staticmethod
    @lru_cache(maxsize=4096)
    def _template_to_regex(template: str) -> re.Pattern[str]:
        # Convert Drain3 template into a regex that extracts parameters where "<*>" appears.
        escaped = re.escape(template)
        placeholder = re.escape("<*>")

        i = 0
        var_index = 0
        parts: list[str] = ["^"]
        while True:
            j = escaped.find(placeholder, i)
            if j == -1:
                parts.append(escaped[i:])
                break
            parts.append(escaped[i:j])
            parts.append(f"(?P<v{var_index}>.+?)")
            var_index += 1
            i = j + len(placeholder)
        parts.append("$")

        return re.compile("".join(parts))
