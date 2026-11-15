"""Load the checked-in Omnigraph schema/query workload."""

from __future__ import annotations

import re
from pathlib import Path

WORKLOAD = Path(__file__).resolve().parents[1] / "workload"
QUERY_START = re.compile(r"(?m)^query\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")


def load_queries(path: Path | None = None) -> dict[str, str]:
    """Split a GQ source file into its top-level named declarations."""
    text = (path or (WORKLOAD / "queries.gq")).read_text(encoding="utf-8")
    queries: dict[str, str] = {}
    for match in QUERY_START.finditer(text):
        opening = text.find("{", match.end())
        if opening < 0:
            raise ValueError(f"query {match.group(1)} has no body")
        depth = 0
        quote = None
        escaped = False
        for index in range(opening, len(text)):
            character = text[index]
            if quote:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == quote:
                    quote = None
                continue
            if character in ('"', "'"):
                quote = character
            elif character == "{":
                depth += 1
            elif character == "}":
                depth -= 1
                if depth == 0:
                    queries[match.group(1)] = text[match.start():index + 1]
                    break
        else:
            raise ValueError(f"query {match.group(1)} has an unterminated body")
    return queries
