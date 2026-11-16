"""M5 Phase E: the master §9.2 rule for measurement runs (ruling a).

No validator reads run manifests (``validate_history`` reads ``history.jsonl`` only), so the rule lives in the
Omnigraph manifest writer, ``capture.check_manifest_fields``, which every Part 2 manifest passes through.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "targets" / "03-omnigraph"))

from witnessmark_omnigraph.capture import (  # noqa: E402
    MEASUREMENT_SCENARIOS, RunCapture, check_manifest_fields,
)

RACES = ("o2a.conditional_one_task.thread", "o2c.cardinality_one_task.thread", "o3.merge_agents.thread",
         "claim.state.naive", "g8.remove_vs_add", "c2.improve")


def manifest(scenario: str, **fields) -> dict:
    return {"scenario": {"id": scenario}, **fields}


class MeasurementManifestRuleTest(unittest.TestCase):
    def test_measurement_runs_may_record_null_controls_and_verdicts(self):
        for scenario in sorted(MEASUREMENT_SCENARIOS):
            with self.subTest(scenario=scenario):
                check_manifest_fields(manifest(scenario))
                check_manifest_fields(manifest(scenario, controls=None, verdicts=None))

    def test_named_checks_under_controls_are_the_runs_own_fields(self):
        check_manifest_fields(manifest("o1.branch_cost", controls={"i6": {}, "falkordb": {}}))
        check_manifest_fields(manifest("o6.traversal_parity", controls={"sequential": {}}))

    def test_a_measurement_run_records_no_verdict_and_no_control_array(self):
        with self.assertRaisesRegex(ValueError, "verdicts must be null"):
            check_manifest_fields(manifest("o5.cross_process_ryw", verdicts=[]))
        with self.assertRaisesRegex(ValueError, "controls must be null"):
            check_manifest_fields(manifest("o4.clean_stop_transfer", controls=[]))

    def test_every_other_run_needs_both_arrays(self):
        for scenario in RACES:
            for fields in ({}, {"controls": [], "verdicts": None}, {"controls": None, "verdicts": []},
                           {"controls": {"sequential": {}}, "verdicts": []}):
                with self.subTest(scenario=scenario, fields=fields), self.assertRaisesRegex(ValueError, "arrays"):
                    check_manifest_fields(manifest(scenario, **fields))
            check_manifest_fields(manifest(scenario, controls=[], verdicts=[]))

    def test_the_writer_refuses_a_race_manifest_without_verdicts(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root)
            planned = {"run_id": "20261116T120000Z-12345678", "harness": {"commit": "0" * 40, "dirty": False},
                       "components": [{"name": "omnigraph-server", "version": "v0.15.0",
                                       "config": {"backend": "local"}}],
                       "scenario": {"id": "o1.i6_controls", "mode": "controls"}}
            capture = RunCapture(repo, repo / "evidence", planned, "python wm_omnigraph.py controls")
            try:
                with self.assertRaisesRegex(ValueError, "arrays"):
                    capture.write_manifest(planned | {"scenario": {"id": "o2a.conditional_one_task.thread"}})
            finally:
                capture.history.close()

    def test_every_committed_manifest_meets_the_rule(self):
        manifests = sorted((ROOT / "evidence").glob("**/run.json"))
        self.assertGreater(len(manifests), 100)
        measurement = 0
        for path in manifests:
            record = json.loads(path.read_text(encoding="utf-8"))
            with self.subTest(run=path.parent.name):
                check_manifest_fields(record)
            measurement += record["scenario"]["id"] in MEASUREMENT_SCENARIOS
        self.assertGreater(measurement, 0)


if __name__ == "__main__":
    unittest.main()
