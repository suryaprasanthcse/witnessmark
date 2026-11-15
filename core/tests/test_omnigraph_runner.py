"""Focused tests for the Omnigraph workload loader and network adapter."""

from pathlib import Path
import sys
import unittest

from witnessmark.adapters.base import Reply

TARGET = Path(__file__).resolve().parents[2] / "targets" / "03-omnigraph"
sys.path.insert(0, str(TARGET))

from witnessmark_omnigraph.engine import OmnigraphSession  # noqa: E402
from witnessmark_omnigraph.workload import load_queries  # noqa: E402


class OmnigraphRunnerTest(unittest.TestCase):
    def test_workload_loader_finds_every_checked_in_declaration(self):
        self.assertEqual(set(load_queries()), {
            "m_reset", "m_fixture_base", "m_fixture_agent", "m_fixture_task",
            "q_task", "q_task_holder", "q_live", "q_eligible", "m_claim_cond",
            "m_claim_card", "m_ledger",
        })

    def test_dump_uses_one_snapshot_and_derives_live_lease_record(self):
        session = object.__new__(OmnigraphSession)
        calls = []

        def run(query, params, *, write):
            calls.append((query, params, write))
            if query == "q_task":
                return Reply(["task", "state"], [["task-0", "claimed"]], "commit-7", {})
            return Reply(["holder", "from_seq", "rw"], [["c00", 4, "lease-4"]], "commit-7", {})

        session.run = run
        state = session.dump_task("task-0")

        self.assertEqual(calls[1], ("q_task_holder", {"task_id": "task-0", "_snapshot": "commit-7"}, False))
        self.assertEqual(state["lease_records"], [{
            "id": "lease-4", "task": "task-0", "agent": "c00", "from_seq": 4,
            "until_seq": None, "observed_graph_commit_id": "commit-7", "observed_order": 1,
        }])


if __name__ == "__main__":
    unittest.main()
