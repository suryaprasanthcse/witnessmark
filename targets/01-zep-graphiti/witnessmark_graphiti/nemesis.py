"""Container actions on the harness's own test containers, recorded as fault-injector operations (client
``nemesis``; master blueprint sections 3.4 and 9.3). Standard library only, so the unit tests can drive it with a
fake runner.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable

from witnessmark.history import OK, UNKNOWN, Op
from witnessmark.timing import stamp

Runner = Callable[[list[str], float], tuple[int, str]]

REPO = Path(__file__).resolve().parents[3]
G7_COMPOSE = "targets/01-zep-graphiti/docker/compose-g7.yml"
#: Layered over G7_COMPOSE for the explanatory control: appendonly yes, appendfsync everysec.
G7_APPENDONLY = "targets/01-zep-graphiti/docker/compose-g7-appendonly.yml"
G7_PROJECT = "witnessmark-g7"
G7_VARIANTS = {
    "root": {"service": "falkordb-root", "container": "wm-g7-root", "port": 16391, "volume": "g7_root_data",
             "mount": "/data"},
    "mcp": {"service": "falkordb-mcp", "container": "wm-g7-mcp", "port": 16392, "volume": "g7_mcp_data",
            "mount": "/var/lib/falkordb/data"},
}


def run_command(args: list[str], timeout: float) -> tuple[int, str]:
    try:
        done = subprocess.run(args, cwd=REPO, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout} s"
    except OSError as exc:
        return 127, f"{type(exc).__name__}: {exc}"
    return done.returncode, (done.stdout + done.stderr).strip()


def compose(*args: str, files: tuple[str, ...] = (G7_COMPOSE,)) -> list[str]:
    return ["docker", "compose", "-p", G7_PROJECT, *[part for f in files for part in ("-f", f)], *args]


class Nemesis:
    """Runs container commands and keeps one operation record per action."""

    def __init__(self, run_id: str, runner: Runner = run_command, timeout_s: float = 180.0):
        self.run_id, self.runner, self.timeout_s = run_id, runner, timeout_s
        self.ops: list[Op] = []
        self._seq = 0

    def act(self, k: int, kind: str, args: list[str], phase: str = "nemesis", client: str = "nemesis",
            **inputs) -> Op:
        """One action: ``kind`` is pause, resume, stop, kill, start or restart (master blueprint section 3.4)."""
        inv = stamp()
        code, output = self.runner(args, self.timeout_s)
        ret = stamp()
        op_id = f"{k}-{client}-{self._seq:03d}"
        self._seq += 1
        record = {"command": " ".join(args), **inputs}
        if code == 0:
            op = Op(self.run_id, k, phase, op_id, client, kind, record, inv, ret, OK, {"exit": 0, "output": output[-300:]})
        else:
            op = Op(self.run_id, k, phase, op_id, client, kind, record, inv, None, UNKNOWN, None,
                    {"type": "docker.exit", "code": code, "message": output[-500:] or f"exit {code}"})
        self.ops.append(op)
        return op

    def drain(self) -> list[Op]:
        ops, self.ops = self.ops, []
        return ops


def g7_action_steps(action: str, variant: str, files: tuple[str, ...] = (G7_COMPOSE,)) -> list[tuple[str, list[str], dict]]:
    """The cell's action as (kind, command, inputs) steps (target blueprint section 5, G7)."""
    v = G7_VARIANTS[variant]
    if action == "compose_restart":
        return [("restart", compose("restart", v["service"], files=files), {"service": v["service"]})]
    if action == "down_up":
        return [("stop", compose("down", files=files),
                 {"service": v["service"], "removes_container": True, "keeps_volume": True}),
                ("start", compose("up", "-d", v["service"], files=files),
                 {"service": v["service"], "creates_container": True})]
    if action == "kill_start":
        return [("kill", ["docker", "kill", v["container"]], {"container": v["container"]}),
                ("start", ["docker", "start", v["container"]], {"container": v["container"]})]
    raise ValueError(f"unknown G7 action {action!r}")


def g7_fresh_steps(variant: str, files: tuple[str, ...] = (G7_COMPOSE,)) -> list[tuple[str, list[str], dict]]:
    """Remove the variant's container and its volume, then start it: every trial starts from an empty volume."""
    v = G7_VARIANTS[variant]
    return [("stop", compose("rm", "--stop", "--force", v["service"], files=files),
             {"service": v["service"], "removes_container": True}),
            ("delete_volume", ["docker", "volume", "rm", "--force", f"{G7_PROJECT}_{v['volume']}"],
             {"volume": f"{G7_PROJECT}_{v['volume']}"}),
            ("start", compose("up", "-d", v["service"], files=files),
             {"service": v["service"], "creates_container": True})]
