"""M6 Phase B: master §9.7 in the verdict code.

A verdict on fewer than half of its declared count (`trials_valid` × 2 < declared) reads as insufficient valid trials.
The writers keep `status` as computed and add `sufficiency`; the reporter adds a "Valid of declared" column and puts
"insufficient valid trials" in place of the verdict word, only when a run carries the field. Old manifests render as
before.
"""

import asyncio
import copy
import json
import tempfile
import unittest
from pathlib import Path

from tests.test_memory import SameGroup, make_target
from tests.test_runner import MemoryClaim, MemoryEngine
from witnessmark.memory import MemoryRunConfig, TargetSpec, run_race
from witnessmark.report import (INSUFFICIENT, g7_table, in_batch, load_runs, memory_markdown, race_table, runs_table,
                                thread_race_table)
from witnessmark.runner import RunConfig, run
from witnessmark.scenarios import Expectation
from witnessmark.verdicts import CHECKING_CASES, DECLARED_TRIALS, add_sufficiency, sufficiency

REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = REPO_ROOT / "evidence"


def verdict(invariant, status, valid, violating=0):
    return {"invariant": invariant, "status": status, "trials_violating": violating, "trials_valid": valid,
            "magnitude": {"unit": ""}, "basis": "inferred", "basis_ref": "test", "witnesses": []}


def trial(k, valid=True, invariants=("I1B",), case=None):
    record = {"k": k, "valid": valid, "release_spread_ms": 1.0, "outcomes": {"ok": 2, "fail": 0, "unknown": 0},
              "checks": [{"invariant": i, "held": True, "magnitude": 0, "unit": "", "witnesses": [], "detail": ""}
                         for i in invariants]}
    if case:
        record["case"] = case
    return record


def race_run(declared, valid, status="PASS", mode="asyncio"):
    """A race manifest with `declared` trials, of which `valid` are valid."""
    return {
        "run_id": "20261119T000000Z-00000000", "batch": "test",
        "target": {"name": "memory", "ref": "test"},
        "components": [{"role": "sut", "name": "memory", "version": "test", "config": {"backend": "falkordb"}}],
        "scenario": {"id": "test.race", "invariants": ["I1B"], "mode": mode, "clients": 2, "trials": declared,
                     "params": {}},
        "expectation": {"role": "negative"},
        "controls": [{"kind": "sequential", "met": True}, {"kind": "overlap", "met": True, "observed": "ok"},
                     {"kind": "negative", "met": True}],
        "trials": [trial(k, valid=k <= valid) for k in range(1, declared + 1)],
        "verdicts": [verdict("I1B", status, valid)],
    }


def g3_run(case_valid=True):
    """M2's G3 shape: six cases, each invariant checked in one of them, MR1 in a suite trial after the cases."""
    trials = [trial(1, invariants=("I7B",), case="b1"), trial(2, invariants=("I7B",), case="b2"),
              trial(3, valid=case_valid, invariants=("I7C",), case="c1"), trial(4, invariants=("I7B",), case="b3"),
              trial(5, invariants=("I2",), case="lost"), trial(6, invariants=("I7B",), case="b4"),
              trial(7, invariants=("MR1",), case="suite")]
    return {
        "run_id": "20261119T000000Z-11111111", "batch": "test", "target": {"name": "memory", "ref": "test"},
        "components": [{"role": "sut", "name": "memory", "version": "test", "config": {"backend": "falkordb"}}],
        "scenario": {"id": "g3.bitemporal", "invariants": ["I7B", "I7C", "I2", "MR1"], "mode": "sequential",
                     "clients": 1, "trials": 6, "params": {"cases": ["b1", "b2", "c1", "b3", "lost", "b4"]}},
        "controls": [], "trials": trials,
        "verdicts": [verdict("I7B", "PASS", 4), verdict("I7C", "PASS", 1 if case_valid else 0),
                     verdict("I2", "PASS", 1), verdict("MR1", "PASS", 1)],
    }


def row(table: str) -> str:
    return table.splitlines()[2]


class RuleTest(unittest.TestCase):
    def test_exactly_half_is_sufficient(self):
        manifest = add_sufficiency(race_run(20, 10))
        self.assertEqual(manifest["verdicts"][0]["sufficiency"],
                         {"declared": 20, "valid": 10, "sufficient": True, "counted": DECLARED_TRIALS})
        self.assertEqual(manifest["verdicts"][0]["status"], "PASS")
        line = row(race_table([manifest]))
        self.assertIn("| 10 of 20 | I1B PASS 0/10 |", line)
        self.assertNotIn(INSUFFICIENT, line)

    def test_below_half_is_insufficient_and_replaces_the_verdict_word(self):
        manifest = add_sufficiency(race_run(20, 9, status="FAIL"))
        self.assertEqual(manifest["verdicts"][0]["sufficiency"]["sufficient"], False)
        self.assertEqual(manifest["verdicts"][0]["status"], "FAIL", "the computed status is kept in the manifest")
        self.assertIn(f"| 9 of 20 | I1B {INSUFFICIENT} 0/9 |", row(race_table([manifest])))
        self.assertTrue(row(runs_table([manifest])).endswith(f"| 9 of 20 | {INSUFFICIENT} | `{manifest['run_id']}` |"))
        thread = add_sufficiency(race_run(20, 1, status="BOUNDARY", mode="thread"))
        self.assertTrue(row(thread_race_table([thread])).endswith(f"| 1 of 20 | {INSUFFICIENT} | `{thread['run_id']}` |"))

    def test_invalid_stays_invalid(self):
        manifest = add_sufficiency(race_run(20, 0, status="INVALID"))
        self.assertFalse(manifest["verdicts"][0]["sufficiency"]["sufficient"])
        self.assertIn("| 0 of 20 | I1B INVALID 0/0 |", row(race_table([manifest])))

    def test_rule_boundaries(self):
        self.assertTrue(sufficiency(20, 10, DECLARED_TRIALS)["sufficient"])
        self.assertFalse(sufficiency(20, 9, DECLARED_TRIALS)["sufficient"])
        self.assertTrue(sufficiency(5, 3, DECLARED_TRIALS)["sufficient"])
        self.assertFalse(sufficiency(5, 2, DECLARED_TRIALS)["sufficient"])
        self.assertTrue(sufficiency(1, 1, CHECKING_CASES)["sufficient"])

    def test_g3_case_suite_counts_the_cases_that_check_each_invariant(self):
        manifest = add_sufficiency(g3_run())
        records = {v["invariant"]: v["sufficiency"] for v in manifest["verdicts"]}
        self.assertEqual(records["I7C"], {"declared": 1, "valid": 1, "sufficient": True, "counted": CHECKING_CASES})
        self.assertEqual(records["I2"]["declared"], 1)
        self.assertEqual(records["MR1"]["declared"], 1)
        self.assertEqual(records["I7B"]["declared"], 4)
        self.assertTrue(all(record["sufficient"] for record in records.values()))
        cell = row(race_table([manifest]))
        self.assertIn("I7B 4 of 4; I7C 1 of 1; I2 1 of 1; MR1 1 of 1", cell)
        self.assertNotIn(INSUFFICIENT, cell)

    def test_g3_case_suite_with_its_one_case_invalid(self):
        records = {v["invariant"]: v["sufficiency"] for v in add_sufficiency(g3_run(case_valid=False))["verdicts"]}
        self.assertEqual(records["I7C"], {"declared": 1, "valid": 0, "sufficient": False, "counted": CHECKING_CASES})

    def test_measurement_manifest_is_left_alone(self):
        manifest = {"scenario": {"trials": 3}, "trials": [], "controls": None, "verdicts": None}
        self.assertEqual(add_sufficiency(copy.deepcopy(manifest)), manifest)
        without = {"scenario": {"trials": 3}, "trials": []}
        self.assertEqual(add_sufficiency(copy.deepcopy(without)), without)


class OldManifestTest(unittest.TestCase):
    def test_old_manifest_renders_exactly_as_before(self):
        old = race_run(20, 9, status="FAIL")
        self.assertEqual(race_table([old]).splitlines(), [
            "| Build | Backend | Scenario | Sequential control | Overlap control | Verdicts | Run |",
            "|---|---|---|---|---|---|---|",
            "| test | falkordb | test.race | met | ok | I1B FAIL 0/9 | `20261119T000000Z-00000000` |",
        ])
        self.assertNotIn("Valid of declared", runs_table([old]))
        self.assertNotIn("Valid of declared", thread_race_table([race_run(20, 9, mode="thread")]))

    def test_a_committed_m5_report_is_unchanged(self):
        """Cognee M5 R1 (1 of 20 valid, the §9.7 case) keeps its stored PASS and the report regenerates exactly."""
        runs = in_batch(load_runs(EVIDENCE), "m5k-20261116T123513Z")
        self.assertFalse(any("sufficiency" in v for run in runs for v in run["verdicts"] or []))
        text = memory_markdown(runs, "m5k-20261116T123513Z", "M5: Cognee")
        committed = (EVIDENCE / "M5_COGNEE.md").read_bytes().decode("utf-8").replace("\r\n", "\n")
        self.assertEqual(text, committed)
        self.assertNotIn("Valid of declared", text)

    def test_the_same_r1_run_under_the_rule(self):
        runs = in_batch(load_runs(EVIDENCE), "m5k-20261116T123513Z")
        r1 = next(run for run in runs if run["run_id"] == "20261116T123522Z-49f0100f")
        line = row(race_table([add_sufficiency(copy.deepcopy(r1))]))
        self.assertIn(f"| 1 of 20 | I1B {INSUFFICIENT} 0/1; I2 {INSUFFICIENT} 0/1; I4 {INSUFFICIENT} 0/1; "
                      f"I5 {INSUFFICIENT} 0/1 |", line)

    def test_g7_table_column(self):
        run = {"scenario": {"params": {"variant": "root", "action": "restart", "volume_mount": "/data"}, "trials": 10},
               "controls": [{"kind": "sequential", "met": True}], "run_id": "r",
               "trials": [{"valid": k < 4, "g7": {"lost": {"lost": {"episodes": 0, "entities": 0, "facts": 0},
                                                           "lost_total": 0}}} for k in range(10)],
               "verdicts": [verdict("I2", "PASS", 4)]}
        self.assertNotIn("Valid of declared", g7_table([run]))
        self.assertIn(f"| 4 of 10 | I2 {INSUFFICIENT} 0/4 |", row(g7_table([add_sufficiency(run)])))


class WriterTest(unittest.TestCase):
    def test_core_runner_writes_the_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = RunConfig(engine=MemoryEngine(False), scenario=MemoryClaim(), shape="naive", clients=4, trials=3,
                               seed=7, spread_gate_ms=None, evidence_root=Path(tmp), repo_root=REPO_ROOT,
                               batch="test", expectation=Expectation("negative", "inferred", "test"),
                               capture_environment=False)
            manifest = run(config)
            on_disk = json.loads((Path(manifest["path"]) / "run.json").read_text(encoding="utf-8"))
        expected = {"declared": 3, "valid": 3, "sufficient": True, "counted": DECLARED_TRIALS}
        self.assertEqual(manifest["verdicts"][0]["sufficiency"], expected)
        self.assertEqual(on_disk["verdicts"][0]["sufficiency"], expected)
        self.assertEqual(on_disk["verdicts"][0]["status"], "PASS")

    def test_memory_runner_writes_the_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = MemoryRunConfig(spec=TargetSpec(make_target.__module__, "make_target",
                                                     {"racy": False, "store": "m6-sufficiency"}),
                                     mode="asyncio", trials=4, evidence_root=Path(tmp), repo_root=REPO_ROOT,
                                     evidence_dir="memory/test")
            manifest = asyncio.run(run_race(config, SameGroup()))
            on_disk = json.loads((Path(manifest["path"]) / "run.json").read_text(encoding="utf-8"))
        expected = {"declared": 4, "valid": 4, "sufficient": True, "counted": DECLARED_TRIALS}
        self.assertEqual(on_disk["verdicts"][0]["sufficiency"], expected)


if __name__ == "__main__":
    unittest.main()
