"""Operation records and history.jsonl (master blueprint sections 5.0 and 9.3)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .timing import Stamp

OK = "ok"
FAIL = "fail"
UNKNOWN = "unknown"
OUTCOMES = (OK, FAIL, UNKNOWN)
PHASES = ("setup", "control", "race", "quiesce", "observe", "nemesis", "stub")
RAW_CAP = 65536


@dataclass
class Op:
    """One operation, as the client saw it.

    ``ok``: the SUT acknowledged success. ``fail``: the SUT definitely did not
    apply it (a typed refusal, or a guard that evaluated false). ``unknown``:
    no definite answer, so the operation may or may not have taken effect.
    """

    run_id: str
    k: int
    phase: str
    op_id: str
    client: str
    kind: str
    input: dict
    inv: Stamp
    ret: Stamp | None
    outcome: str
    result: Any = None
    error: dict | None = None
    token: str | None = None
    process: str | None = None
    raw: str | None = None

    def __post_init__(self) -> None:
        if self.outcome not in OUTCOMES:
            raise ValueError(f"outcome must be one of {OUTCOMES}, not {self.outcome!r}")
        if self.phase not in PHASES:
            raise ValueError(f"phase must be one of {PHASES}, not {self.phase!r}")
        if self.outcome == UNKNOWN and self.ret is not None:
            raise ValueError("an operation with an unknown outcome has no return time")
        if self.outcome != UNKNOWN and self.ret is None:
            raise ValueError("a definite outcome needs a return time")

    @classmethod
    def from_json(cls, record: dict) -> "Op":
        """Rebuild an operation sent from another process."""

        def stamp_of(value):
            return Stamp(value["mono_ns"], value["wall"], value.get("domain", "host")) if value else None

        return cls(record["run_id"], record["k"], record["phase"], record["op_id"], record["client"], record["kind"],
                   record["input"], stamp_of(record["inv"]), stamp_of(record["ret"]), record["outcome"],
                   record.get("result"), record.get("error"), record.get("token"), record.get("process"),
                   record.get("raw"))

    def to_json(self) -> dict:
        record = {
            "run_id": self.run_id,
            "k": self.k,
            "phase": self.phase,
            "op_id": self.op_id,
            "client": self.client,
            "kind": self.kind,
            "input": self.input,
            "inv": self.inv.to_json(),
            "ret": self.ret.to_json() if self.ret else None,
            "outcome": self.outcome,
            "result": self.result,
            "error": self.error,
            "token": self.token,
        }
        if self.process is not None:
            record["process"] = self.process
        if self.raw is not None:
            record["raw_sha256"] = hashlib.sha256(self.raw.encode("utf-8")).hexdigest()
            record["raw"] = self.raw[:RAW_CAP]
        return record


def write_history(path: Path, ops: Iterable[Op]) -> int:
    count = 0
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for op in ops:
            handle.write(json.dumps(op.to_json(), sort_keys=True, separators=(",", ":"), ensure_ascii=False))
            handle.write("\n")
            count += 1
    return count


def read_history(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def validate_history(path: Path) -> int:
    """Check the required operation fields in §9.3 and return the record count."""
    required = {"run_id", "k", "phase", "op_id", "client", "kind", "input", "inv", "ret", "outcome"}
    seen = set()

    def check_stamp(value: object) -> None:
        if not isinstance(value, dict) or type(value.get("mono_ns")) is not int:
            raise ValueError("a timestamp needs an integer mono_ns")
        wall, domain = value.get("wall"), value.get("domain")
        if not isinstance(wall, str) or not isinstance(domain, str) or not domain:
            raise ValueError("a timestamp needs wall and domain strings")
        moment = datetime.fromisoformat(wall.replace("Z", "+00:00"))
        if "T" not in wall or moment.utcoffset() is None:
            raise ValueError("wall must be a date-time with a time zone")

    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            try:
                record = json.loads(line)
                if not isinstance(record, dict) or not required <= record.keys():
                    raise ValueError("missing required operation fields")
                if type(record["k"]) is not int or record["k"] < 0 or not isinstance(record["input"], dict):
                    raise ValueError("invalid trial number or input")
                if any(not isinstance(record[key], str) for key in ("run_id", "op_id", "client", "kind")):
                    raise ValueError("operation identifiers must be strings")
                if record["phase"] not in PHASES or record["outcome"] not in OUTCOMES:
                    raise ValueError("invalid phase or outcome")
                check_stamp(record["inv"])
                if record["outcome"] == UNKNOWN:
                    if record["ret"] is not None:
                        raise ValueError("an unknown outcome requires a null ret")
                else:
                    check_stamp(record["ret"])
                error = record.get("error")
                if error is not None and (not isinstance(error, dict) or
                                          any(not isinstance(error.get(key), str) for key in ("type", "message")) or
                                          ("code" in error and type(error["code"]) not in (str, int))):
                    raise ValueError("invalid error object")
                token = record.get("token")
                if token is not None and not isinstance(token, str):
                    raise ValueError("invalid token")
                key = record["run_id"], record["op_id"]
                if key in seen:
                    raise ValueError("duplicate operation id")
                seen.add(key)
            except ValueError as exc:
                raise ValueError(f"history line {number}: {exc}") from exc
    return len(seen)
