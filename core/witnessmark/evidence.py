"""Evidence layout and writers (master blueprint section 9).

    evidence/<target>/<scenario>/<run_id>/
      run.json        manifest, pins, environment, controls, trials, verdicts
      history.jsonl   one JSON object per operation
      state/<k>.json  canonical final state of trial k (0 = sequential control)
      REPRO.md        the command that regenerates the run
"""

from __future__ import annotations

import datetime
import hashlib
import json
import re
from pathlib import Path
from typing import Iterable

from .history import Op, write_history

RUN_ID = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$")


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value) -> str:
    return "sha256:" + hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def make_run_id(started: datetime.datetime, header: dict) -> str:
    """<UTC yyyymmddThhmmssZ>-<first 8 hex of the SHA-256 of the run's header>."""
    short = hashlib.sha256(canonical(header).encode("utf-8")).hexdigest()[:8]
    return f"{started.astimezone(datetime.timezone.utc):%Y%m%dT%H%M%SZ}-{short}"


def redact(text: str) -> str:
    """Replace the home directory with ~ in every spelling a traceback may use (master blueprint 9.5)."""
    home = str(Path.home())
    for spelling in {home, home.replace("\\", "/"), home.replace("\\", "\\\\")}:
        text = text.replace(spelling, "~")
    return text


def crash_note(run_dir_path: Path, run_id: str, trace: str) -> None:
    """A crashed run leaves no run.json, so the reporter skips it; ERROR.md says why."""
    (Path(run_dir_path) / "ERROR.md").write_text(f"# Run {run_id} crashed\n\n```text\n{redact(trace)}```\n",
                                                 encoding="utf-8", newline="\n")


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


class RunDir:
    def __init__(self, evidence_root: Path, target: str, scenario_id: str, run_id: str):
        if not RUN_ID.match(run_id):
            raise ValueError(f"malformed run_id {run_id!r}")
        self.run_id = run_id
        self.path = Path(evidence_root) / target / scenario_id / run_id
        (self.path / "state").mkdir(parents=True, exist_ok=False)

    def write_state(self, k: int, state: dict) -> str:
        relative = f"state/{k}.json"
        write_json(self.path / relative, {"k": k, "digest": digest(state), "state": state})
        return relative

    def write_history(self, ops: Iterable[Op]) -> int:
        return write_history(self.path / "history.jsonl", ops)

    def write_manifest(self, manifest: dict) -> None:
        write_json(self.path / "run.json", manifest)

    def write_repro(self, text: str) -> None:
        (self.path / "REPRO.md").write_text(text, encoding="utf-8", newline="\n")
