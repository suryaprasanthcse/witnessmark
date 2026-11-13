"""The runner end to end, against in-memory engines.

One engine serialises claims, so it must keep I1. The other reads the guard,
waits, then writes, so concurrent clients must be able to break I1. Together
they show the runner can see a race and can see its absence, before any real
engine is involved.
"""

import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from witnessmark.adapters.base import Engine, Reply, Session
from witnessmark.evidence import RUN_ID
from witnessmark.history import read_history
from witnessmark.runner import RunConfig, run
from witnessmark.scenarios import ClaimState, Expectation

REPO_ROOT = Path(__file__).resolve().parents[2]


class Store:
    def __init__(self, racy: bool):
        self.racy = racy
        self.lock = threading.Lock()
        self.task = {"state": "open", "holder": ""}


class MemorySession(Session):
    def __init__(self, store: Store):
        self.store = store

    def run(self, query, params=None, *, write=True):
        store = self.store
        if query == "reset":
            with store.lock:
                store.task = {"state": "open", "holder": ""}
            return Reply([], [])
        if query == "observe":
            with store.lock:
                return Reply(["id", "state", "holder"], [[1, store.task["state"], store.task["holder"]]])
        if query == "claim":
            if store.racy:
                seen = store.task["state"]  # read the guard without a lock...
                time.sleep(0.005)  # ...and leave a window before the write
                if seen != "open":
                    return Reply(["won"], [[0]])
                with store.lock:
                    store.task = {"state": "claimed", "holder": params["agent"]}
                return Reply(["won"], [[1]])
            with store.lock:
                if store.task["state"] != "open":
                    return Reply(["won"], [[0]])
                store.task = {"state": "claimed", "holder": params["agent"]}
                return Reply(["won"], [[1]])
        raise AssertionError(f"unexpected query {query!r}")

    def ping(self):
        pass

    def close(self):
        pass


class MemoryEngine(Engine):
    repo = "witnessmark/test"

    def __init__(self, racy: bool):
        self.name = "memory-racy" if racy else "memory-serial"
        self.store = Store(racy)

    def session(self, timeout=60.0):
        return MemorySession(self.store)

    def reset(self, session):
        session.run("reset")

    def health(self):
        return {"ok": True}

    def describe(self):
        return {"role": "sut", "name": self.name, "version": "test", "digest": "sha256:" + "0" * 64}


class MemoryClaim(ClaimState):
    """claim.state, spoken in the memory engine's three-word query language."""

    shapes = {"naive": "claim"}

    def setup(self, session, n):
        pass

    def payload(self, shape, i, n):
        params = {"agent": f"c{i:02d}"}
        return "claim", params, dict(params)

    def observe(self, session, n):
        rows = session.run("observe").rows
        return {"tasks": [dict(zip(["id", "state", "holder"], row)) for row in rows]}


class RunnerTest(unittest.TestCase):
    def run_memory(self, racy: bool, role: str, evidence: Path):
        config = RunConfig(engine=MemoryEngine(racy), scenario=MemoryClaim(), shape="naive", clients=20, trials=5,
                           seed=7, evidence_root=evidence, repo_root=REPO_ROOT, batch="test",
                           expectation=Expectation(role, "inferred", "test"), capture_environment=False)
        return run(config)

    def test_serialised_engine_keeps_the_invariant(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.run_memory(False, "negative", Path(tmp))
            self.assertRegex(manifest["run_id"], RUN_ID)
            sequential, negative = manifest["controls"]
            self.assertTrue(sequential["met"], sequential)
            self.assertTrue(negative["met"], negative)
            self.assertEqual(manifest["verdicts"][0]["status"], "PASS")
            self.assertTrue(all(trial["valid"] for trial in manifest["trials"]))

    def test_racy_engine_is_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.run_memory(True, "positive", Path(tmp))
            sequential, positive = manifest["controls"]
            self.assertTrue(sequential["met"], "one client at a time cannot race")
            self.assertTrue(positive["met"], positive)
            record = manifest["verdicts"][0]
            self.assertEqual(record["status"], "FAIL")
            self.assertGreaterEqual(record["magnitude"]["max"], 2)
            self.assertTrue(record["witnesses"])

    def test_evidence_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self.run_memory(False, "negative", Path(tmp))
            run_dir = Path(manifest["path"])
            self.assertEqual(run_dir.parent.name, "claim.state.naive")
            on_disk = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
            for key in ("schema_version", "run_id", "harness", "target", "components", "host", "scenario", "seed",
                        "started_at", "finished_at", "controls", "trials", "verdicts"):
                self.assertIn(key, on_disk)
            ops = read_history(run_dir / "history.jsonl")
            self.assertEqual(len(ops), 20 + 20 * 5, "the sequential control plus every race operation")
            self.assertEqual({op["phase"] for op in ops}, {"control", "race"})
            self.assertTrue((run_dir / "state" / "0.json").exists())
            self.assertTrue((run_dir / "state" / "5.json").exists())
            self.assertIn("python wm.py run", (run_dir / "REPRO.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
