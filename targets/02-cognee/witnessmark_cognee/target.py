"""Witnessmark's adapter for Cognee (target blueprint sections 3, 4 and 6).

Two modes, chosen by where the adapter is built:

- **coordinator** (the main process): it never imports cognee. Every call goes to a
  helper process (``helper.py``). ``reset`` starts a fresh store root, so no state
  survives from one trial to the next; ``release`` stops the helper before a
  process-mode race, which frees Ladybug's exclusive file lock for the workers.
- **worker** (a process the runner spawned): it reads the current root from the
  pointer file, sets the environment, imports cognee and runs the calls itself.

Telemetry is switched off before cognee is imported, and ``open`` refuses to run
if the switch did not take (``envsetup.assert_telemetry_off``).
"""

from __future__ import annotations

import multiprocessing
from pathlib import Path

from witnessmark import __version__ as harness_version
from witnessmark.memory import MemoryTarget
from witnessmark.stubs import CURRENT_OP

from . import envsetup, stub
from .helper import HelperClient

TAG_COMMITS = {"v1.6.8": "069f3cc119bdf5628be054bb915992b2fc78cfc5", "v1.6.1": "eb90d03740755f5252b8b12cce91fd09970f2d81"}
STORES = {
    "R1": [("graph", "ladybug", "subprocess worker on"), ("vector", "lancedb", ""), ("relational", "sqlite", "")],
    "R1i": [("graph", "ladybug", "in-process (GRAPH_DATABASE_SUBPROCESS_ENABLED=false)"), ("vector", "lancedb", ""),
            ("relational", "sqlite", "")],
    "R2": [("graph", "neo4j", "Neo4j 5.26.2 Community over Bolt"), ("vector", "lancedb", ""),
           ("relational", "sqlite", "")],
    "R3": [("graph", "falkordb", "FalkorDB 6.0.4 via cognee-community-hybrid-adapter-falkor"),
           ("vector", "falkordb", "same server"), ("relational", "sqlite", "")],
}


class CogneeTarget(MemoryTarget):
    name = "cognee"
    repo = "topoteretes/cognee"

    def __init__(self, row: str, root: str, stub_url: str, dim: int = 256, access_control: str = "default",
                 build_ref: str = "v1.6.8", commit: str = ""):
        if row not in envsetup.ROWS:
            raise ValueError(f"row must be one of {sorted(envsetup.ROWS)}")
        self.row, self.root, self.stub_url, self.dim = row, Path(root), stub_url, dim
        self.access_control, self.build_ref = access_control, build_ref
        self.commit = commit or TAG_COMMITS.get(build_ref, "")
        self.worker = multiprocessing.parent_process() is not None
        self.helper: HelperClient | None = None
        self.engine = None
        self.generation = 0
        self.dirty = True
        self.checked: dict = {}

    # --- roots and helpers -------------------------------------------------------------------------------------

    def _current(self) -> Path:
        return self.root / (self.root / "CURRENT").read_text(encoding="utf-8").strip()

    def _new_generation(self) -> Path:
        existing = [int(p.name[1:]) for p in self.root.glob("g[0-9][0-9][0-9][0-9]")]
        self.generation = max(existing, default=0) + 1
        name = f"g{self.generation:04d}"
        (self.root / name).mkdir(parents=True, exist_ok=False)
        (self.root / "CURRENT").write_text(name, encoding="utf-8")
        return self.root / name

    def env(self, root: Path) -> dict:
        return envsetup.build_env(self.row, root, self.stub_url, self.dim, self.access_control)

    async def _helper(self) -> HelperClient:
        if self.helper is None or not self.helper.process.is_alive():
            self.helper = HelperClient(self.env(self._current()), self.row)
            self.checked = await self.helper.call("check")
            if self.checked.get("telemetry") != "off":
                raise RuntimeError("Cognee telemetry is not off; refusing to run")
        return self.helper

    def _stop_helper(self) -> None:
        if self.helper is not None:
            self.helper.stop()
            self.helper = None

    # --- lifecycle ---------------------------------------------------------------------------------------------

    async def open(self) -> None:
        if self.worker:
            envsetup.enter(self.env(self._current()))
            from .engine import CogneeEngine

            self.engine = CogneeEngine(self.row)
            self.checked = await self.engine.check()  # imports cognee and asserts telemetry is off
            await self.engine._user()  # warm: the relational store is open before the barrier
            return
        self.root.mkdir(parents=True, exist_ok=True)
        if not (self.root / "CURRENT").exists():  # a second coordinator target (a reader) shares the store
            self._new_generation()
        await (await self._helper()).call("setup")
        self.dirty = False

    async def close(self) -> None:
        self._stop_helper()

    async def release(self) -> None:
        self._stop_helper()
        self.dirty = True

    def identity(self) -> dict:
        record = {"name": "cognee", "repo": self.repo, "ref": self.build_ref,
                  "package_version": self.checked.get("versions", {}).get("cognee", "?")}
        if self.commit:
            record["commit"] = self.commit
        return record

    def components(self) -> list[dict]:
        versions = self.checked.get("versions", {})
        config = {"build": self.build_ref, "row": self.row,
                  "backend": self.row + (" (access control off)" if self.access_control == "off" else ""),
                  "access_control": self.access_control,
                  "access_control_effective": self.checked.get("access_control"),
                  "telemetry": "off", "structured_output_framework": self.checked.get("structured_output_framework"),
                  "network": "loopback only (socket guard)",
                  "falkor_vector_port_shim": self.checked.get("falkor_vector_port_shim", False),
                  "env": {k: v for k, v in sorted(envsetup.ROWS[self.row].items()) if "PASSWORD" not in k}}
        components = [{"role": "sut", "name": "cognee", "version": versions.get("cognee", "?"), "config": config}]
        for role, name, note in STORES[self.row]:
            version = versions.get({"ladybug": "ladybug", "lancedb": "lancedb", "neo4j": "neo4j",
                                    "falkordb": "falkordb"}.get(name, ""), "")
            components.append({"role": "store", "name": name, "version": version or note or "bundled",
                               "config": {"store": role, "note": note}})
        if "cognee-community-hybrid-adapter-falkor" in versions:
            components.append({"role": "store", "name": "cognee-community-hybrid-adapter-falkor",
                               "version": versions["cognee-community-hybrid-adapter-falkor"]})
        components.append({"role": "stub", "name": "witnessmark-stub-endpoint", "version": harness_version,
                           "config": {"transport": "OpenAI-compatible HTTP on 127.0.0.1, shared by every process",
                                      "llm": "ideal-model fixture answers, schema-validated",
                                      "embedder": f"hashed bag of words, {self.dim} dimensions"}})
        return components

    # --- the contract ------------------------------------------------------------------------------------------

    async def reset(self, group: str) -> None:
        if self.worker:
            raise RuntimeError("workers do not reset")
        if not self.dirty:
            return
        self._stop_helper()
        self._new_generation()
        await (await self._helper()).call("setup")
        self.dirty = False

    async def ingest(self, item: dict, group: str) -> dict:
        if self.worker:
            return await self.engine.ingest(item, group)
        self.dirty = True
        return await (await self._helper()).call("ingest", item, group, context=CURRENT_OP.get())

    async def search(self, query: str, group: str) -> list[str]:
        if self.worker:
            return await self.engine.search(query, group)
        return await (await self._helper()).call("search", query, group)

    async def dump(self, group: str) -> dict:
        if self.worker:
            return await self.engine.dump(group)
        return await (await self._helper()).call("dump", group)

    async def call(self, method: str, *args):
        """Any engine method, for scenarios with their own runner (C4)."""
        return await (await self._helper()).call(method, *args)

    def drain_stub_calls(self) -> list[dict]:
        if self.worker or stub.SERVER is None:
            return []
        return stub.SERVER.ledger(drain=True)


def make_target(**options) -> CogneeTarget:
    return CogneeTarget(**options)
