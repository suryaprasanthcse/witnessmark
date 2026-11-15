"""M3's core additions: the stub-error and spread gates, the release hook, and the new report tables."""

import asyncio
import tempfile
import unittest
from pathlib import Path

from witnessmark.checkers import Check
from witnessmark.history import OK, Op
from witnessmark.memory import (SPREAD_GATE_MS, MemoryRunConfig, MemoryTarget, RaceScenario, TargetSpec, run_race,
                                stub_errors)
from witnessmark.report import (extra_checks_table, invalid_table, invariants_table, ladder_table, memory_markdown,
                                support_boundaries_table)
from witnessmark.timing import Stamp

REPO_ROOT = Path(__file__).resolve().parents[2]


def _stub_op(decision):
    return Op("r", 1, "stub", "1-stub-0000", "setup", "llm", {}, Stamp(1, "w"), Stamp(2, "w"), OK,
              {"decision": decision, "response_sha256": "x"})


class StubErrorsTest(unittest.TestCase):
    def test_only_calls_with_an_error_count(self):
        ops = [_stub_op({"prompt": "graph"}), _stub_op({"error": "unknown prompt: x"})]
        self.assertEqual(stub_errors(ops), ["unknown prompt: x"])


class _Store(MemoryTarget):
    """Counts releases; ingests always succeed. Built fresh in every process."""

    name, repo = "fake", "none/fake"
    released = 0
    ERRORS: list = []

    def identity(self):
        return {"name": "fake", "repo": "none/fake", "ref": "test", "commit": "0" * 40}

    def components(self):
        return [{"role": "sut", "name": "fake", "version": "0", "config": {"backend": "memory"}}]

    async def reset(self, group):
        self.items = []

    async def ingest(self, item, group):
        await asyncio.sleep(0.02)
        return {"ok": True}

    async def search(self, query, group):
        return []

    async def dump(self, group):
        return {"n": 0}

    async def release(self):
        type(self).released += 1

    def drain_stub_calls(self):
        errors, type(self).ERRORS = type(self).ERRORS, []
        return errors


def make_store():
    return _Store()


class _Race(RaceScenario):
    id = "fake.race"
    invariants = ("I2",)
    support = "boundary"

    def clients(self):
        return [("g", {"tag": "a"}), ("g", {"tag": "b"})]

    def check(self, ops, states):
        return [Check("I2", True, 0, "lost", "fine"), Check("ERR", False, 1, "ops", "lock x1", ["x"])]

    def sequential_expected(self, ops, states):
        return True, "fine", "fine"


class RunnerGatesTest(unittest.TestCase):
    def _run(self, mode: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            config = MemoryRunConfig(spec=TargetSpec(__name__, "make_store"), mode=mode, trials=2, processes=2,
                                     evidence_root=Path(tmp), repo_root=REPO_ROOT, evidence_dir="fake/x")
            return asyncio.run(run_race(config, _Race()))

    def test_asyncio_records_the_gate_and_a_stub_error_invalidates_the_trial(self):
        _Store.ERRORS = []
        manifest = self._run("asyncio")
        self.assertEqual(manifest["scenario"]["params"]["spread_gate_ms"], SPREAD_GATE_MS["asyncio"])
        self.assertTrue(all(t["valid"] for t in manifest["trials"]))
        self.assertEqual(_Store.released, 0)

    def test_process_mode_releases_the_store_before_each_trial(self):
        _Store.released = 0
        manifest = self._run("process")
        self.assertEqual(_Store.released, 2)
        self.assertEqual(manifest["scenario"]["params"]["spread_gate_ms"], SPREAD_GATE_MS["process"])


def _run_record(trials, ladder=None, invariants=("I1B", "I2")):
    run = {"run_id": "20261114T000000Z-abcdef01", "target": {"name": "cognee", "ref": "v1.6.8"},
           "components": [{"role": "sut", "name": "cognee", "config": {"backend": "R1"}}],
           "scenario": {"id": "c1.k2.process", "mode": "process", "invariants": list(invariants)},
           "controls": [{"kind": "sequential", "met": True}, {"kind": "overlap", "met": True, "observed": "2 of 2"}],
           "verdicts": [{"invariant": "I2", "status": "PASS", "trials_violating": 0, "trials_valid": 2}],
           "trials": trials}
    if ladder:
        run["ladder"] = ladder
    return run


def _trial(valid, checks, reason=None):
    trial = {"k": 1, "valid": valid, "release_spread_ms": 0.1, "checks": checks}
    if reason:
        trial["invalid_reason"] = reason
    return trial


class ReportTablesTest(unittest.TestCase):
    def test_support_boundaries_exclude_failed_sequential_controls(self):
        err = {"invariant": "ERR", "held": False, "detail": "lock x1"}
        run = _run_record([_trial(False, [err])])
        run["expectation"] = {"support": "boundary"}
        self.assertIn("`20261114T000000Z-abcdef01`", support_boundaries_table([run]))
        run["controls"][0]["met"] = False
        self.assertIsNone(support_boundaries_table([run]))

    def test_support_boundaries_require_a_boundary_and_no_valid_trials(self):
        err = {"invariant": "ERR", "held": False, "detail": "busy x1; lock x3"}
        other = {"invariant": "ERR", "held": False, "detail": "busy x3"}
        run = _run_record([_trial(False, [err]), _trial(False, [other])])
        run["expectation"] = {"support": "boundary"}
        report = memory_markdown([run], "b", "T")
        self.assertLess(report.index("## Support boundaries reached"), report.index("## Races"))
        self.assertIn("| 0 of 2 | busy | `20261114T000000Z-abcdef01` |", report)
        run["trials"][0]["valid"] = True
        self.assertNotIn("## Support boundaries reached", memory_markdown([run], "b", "T"))
        run["trials"][0]["valid"] = False
        run["expectation"]["support"] = "supported"
        self.assertNotIn("## Support boundaries reached", memory_markdown([run], "b", "T"))
        run["expectation"]["support"] = "boundary"
        run["trials"] = [_trial(False, [])]
        self.assertNotIn("## Support boundaries reached", memory_markdown([run], "b", "T"))

    def test_invariants_table_counts_valid_trials_by_unit(self):
        entity = {"invariant": "I1B", "held": True, "unit": "records per key", "detail": "", "magnitude": 1}
        vector = {"invariant": "I1B", "held": False, "unit": "rows per vector id", "detail": "", "magnitude": 2}
        lost = {"invariant": "I2", "held": True, "unit": "missing facts", "detail": "", "magnitude": 0}
        run = _run_record([_trial(True, [entity, vector, lost]), _trial(False, [vector], "lock")])
        row = invariants_table([run]).splitlines()[2]
        self.assertIn("| 1/2 | 0/1 | 1/1 | – | 0/1 | – |", row)
        self.assertIn("`20261114T000000Z-abcdef01`", row)

    def test_extra_checks_and_invalid_trials(self):
        err = {"invariant": "ERR", "held": False, "unit": "ops", "detail": "ladybug file lock x1", "magnitude": 1}
        run = _run_record([_trial(False, [err], "1 of 2 operations had an unknown outcome")])
        self.assertIn("| ERR | 1 of 1 | ladybug file lock x1 |", extra_checks_table([run]))
        self.assertIn("| 1 of 1 | 1 of 2 operations had an unknown outcome |", invalid_table([run]))
        self.assertIsNone(invalid_table([_run_record([_trial(True, [])])]))

    def test_ladder_table_and_section(self):
        trials = [{"k": 1, "rung": 448, "valid": True, "documents": 448, "elapsed_s": 60.0,
                   "batch_seconds": {"median": 2.0, "max": 3.5}, "resident_mb_peak": {"helper": 400.0, "children": 90},
                   "store": {"graph_bytes": 3 * 2**20}, "graph": {"nodes": 2700, "entities": 1300},
                   "stub_calls": {"llm": 448, "embed": 120}, "crash": None, "checks": []}]
        ladder = {"documents": 448, "crash": None,
                  "reopen": {"store": "x.lbug", "read_only": {"opened": True, "nodes": 2700},
                             "read_write": {"opened": True, "nodes": 2700}}}
        run = _run_record(trials, ladder, invariants=("I2", "CRASH"))
        run["scenario"]["mode"] = "sequential"
        table = ladder_table(run)
        self.assertIn("| 448 | 448 | 60 | 2 / 3.50 | 400 / 90 | 3 | 2700 | 1300 | 448 / 120 | no |", table)
        self.assertIn("read_only: opened, 2700 nodes", table)
        text = memory_markdown([run], "b", "T")
        self.assertIn("## Scale ladder", text)
        self.assertNotIn("## Read your writes", text)
        self.assertIn("none up to 448 | read-only yes; read-write yes", text)


if __name__ == "__main__":
    unittest.main()
