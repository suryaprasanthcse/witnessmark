"""Omnigraph M4 scenario declarations and their pure checks."""

from pathlib import Path
import sys
import unittest

TARGET = Path(__file__).resolve().parents[2] / "targets" / "03-omnigraph"
sys.path.insert(0, str(TARGET))

try:
    from witnessmark_omnigraph.scenarios import (O2AConditionalClaims, O2BDisjointConditionalClaims,
                                                 O3BranchMerge, O6TraversalParity, SCENARIOS)
except ImportError as exc:  # Keep discovery usable if the target package is unavailable.
    O2AConditionalClaims = None
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


@unittest.skipIf(IMPORT_ERROR is not None, f"Omnigraph scenario import unavailable: {IMPORT_ERROR}")
class OmnigraphScenarioTest(unittest.TestCase):
    def test_declares_all_no_run_scenarios(self):
        self.assertEqual(len(SCENARIOS), 6)
        self.assertEqual(len(O2AConditionalClaims().clients()), 50)
        self.assertEqual(len(O2BDisjointConditionalClaims().groups()), 1)
        self.assertEqual(O3BranchMerge(True).clients()[0][1]["branch"], "agent/c00")

    def test_parity_classifies_identical_rejected_and_different(self):
        scenario = O6TraversalParity()
        same = {
            engine: {
                "q_eligible": {"outcome": "ok", "rows": [{"agent": "a", "task": "t"}]},
                "q_live": {"outcome": "ok", "rows": [{"live": 1.0}]},
            }
            for engine in scenario.ENGINES
        }
        self.assertTrue(all(check.held for check in scenario.check([], same)))

        rejected = {engine: dict(queries) for engine, queries in same.items()}
        rejected["falkordb"] = dict(rejected["falkordb"])
        rejected["falkordb"]["q_live"] = {"outcome": "refusal", "rows": []}
        self.assertIn("rejected", scenario.check([], rejected)[1].detail)

        different = {engine: dict(queries) for engine, queries in same.items()}
        different["neo4j"] = dict(different["neo4j"])
        different["neo4j"]["q_eligible"] = {"outcome": "ok", "rows": []}
        self.assertIn("silently different", scenario.check([], different)[0].detail)


if __name__ == "__main__":
    unittest.main()
