"""Deterministic model stubs: the engine-neutral parts (master blueprint section 8).

Target adapters bind these to their own client interfaces. Nothing here calls a
network service.
"""

from __future__ import annotations

import contextvars
import hashlib
import json
import math
import re

from .timing import stamp

# The operation a stub call belongs to. The runner sets it around every
# operation; asyncio tasks inherit it, so calls made deep inside a library are
# attributed to the right client.
CURRENT_OP: contextvars.ContextVar = contextvars.ContextVar("witnessmark_current_op", default=None)

_TOKEN = re.compile(r"[a-z0-9]+")


def tokens(text: str) -> list[str]:
    return _TOKEN.findall((text or "").lower())


def embed(text: str, dim: int = 1024) -> list[float]:
    """Signed bag-of-words hashed into ``dim`` buckets, then L2-normalised.

    Equal word bags give equal vectors, and texts that share words get a
    positive cosine, so similarity search behaves plausibly and identically on
    every run.
    """
    vector = [0.0] * dim
    for token in tokens(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        vector[int.from_bytes(digest[:4], "big") % dim] += 1.0 if digest[4] & 1 else -1.0
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        vector[0] = 1.0
        return vector
    return [value / norm for value in vector]


def overlap(a: str, b: str) -> float:
    """Jaccard similarity of two texts' word sets."""
    left, right = set(tokens(a)), set(tokens(b))
    return len(left & right) / len(left | right) if left | right else 0.0


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class StubLedger:
    """Every stub answer, with what the 'model' was shown and what it decided."""

    def __init__(self) -> None:
        self._calls: list[dict] = []

    def record(self, prompt: str, request_text: str, response: dict, decision: dict, inv) -> None:
        current = CURRENT_OP.get() or {}
        self._calls.append({
            "prompt": prompt,
            "client": current.get("client"),
            "op_id": current.get("op_id"),
            "inv": inv,
            "ret": stamp(),
            "request_sha256": sha256_text(request_text),
            "response_sha256": sha256_text(json.dumps(response, sort_keys=True, default=str)),
            "decision": decision,
        })

    def drain(self) -> list[dict]:
        calls, self._calls = self._calls, []
        return calls
