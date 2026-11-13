"""Time stamps for operation records (master blueprint sections 6.1 and 9.3).

Monotonic readings order events inside one clock domain. Wall-clock readings
order events across domains, using offsets recorded with the run.
"""

from __future__ import annotations

import datetime
import time
from dataclasses import dataclass

HOST_DOMAIN = "host"


@dataclass(frozen=True)
class Stamp:
    mono_ns: int
    wall: str
    domain: str = HOST_DOMAIN

    def to_json(self) -> dict:
        return {"mono_ns": self.mono_ns, "wall": self.wall, "domain": self.domain}


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def iso(moment: datetime.datetime) -> str:
    return moment.isoformat(timespec="microseconds").replace("+00:00", "Z")


def stamp(domain: str = HOST_DOMAIN) -> Stamp:
    # The monotonic reading comes first: it is the one that orders a race.
    mono = time.perf_counter_ns()
    return Stamp(mono, iso(utc_now()), domain)
