"""The M5 report tables: thread races, refusal types, O2b, O6, O4 clean-stop and O1's unrelated graph."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from witnessmark import report

HOST = {"os": "test", "cpu": "cpu", "cores": 1, "memory_gb": 1}
HARNESS = {"commit": "a" * 40, "dirty": False}


def _thread_run(engine: str, run_id: str, directory: str = ".") -> dict:
    if engine == "omnigraph":
        components = [{"role": "sut", "name": "omnigraph-server", "version": "v0.15.0",
                       "config": {"storage": "local"}}]
        target = {"name": "omnigraph", "ref": "v0.15.0"}
        scenario_id = "o2a.conditional_one_task.thread"
    else:
        components = [{"role": "baseline", "name": "falkordb", "version": "6.0.4"}]
        target = {"name": "falkordb", "ref": "6.0.4"}
        scenario_id = "claim.state.naive"
    trials = [{"k": 1, "valid": True, "release_spread_ms": 10.0, "outcomes": {"ok": 1, "fail": 2, "unknown": 0},
               "checks": [{"invariant": "I1A", "held": True}]},
              {"k": 2, "valid": False, "invalid_reason": "spread", "release_spread_ms": 90.0,
               "outcomes": {"ok": 1, "fail": 2, "unknown": 0}, "checks": [{"invariant": "I1A", "held": True}]}]
    return {"run_id": run_id, "batch": "b", "started_at": run_id, "harness": HARNESS, "host": HOST,
            "target": target, "components": components, "_dir": directory,
            "scenario": {"id": scenario_id, "mode": "thread", "clients": 3, "invariants": ["I1A"],
                         "params": {"spread_gate_ms": 55.0}},
            "expectation": {"role": "negative"},
            "controls": [{"kind": "sequential", "met": True}, {"kind": "negative", "met": True}],
            "trials": trials,
            "verdicts": [{"invariant": "I1A", "status": "PASS", "trials_violating": 0, "trials_valid": 1}]}


class ReportM5Test(unittest.TestCase):
    def test_thread_races_split_controls_from_omnigraph_and_count_refusals_from_history(self):
        with tempfile.TemporaryDirectory() as root:
            ops = [{"run_id": "r", "k": 0, "phase": "control", "outcome": "fail", "error": {"type": "ignored"}},
                   {"run_id": "r", "k": 1, "phase": "race", "outcome": "ok", "error": None},
                   {"run_id": "r", "k": 1, "phase": "race", "outcome": "fail", "error": {"type": "too_many_requests"}},
                   {"run_id": "r", "k": 1, "phase": "race", "outcome": "fail", "error": {"type": "precondition_failure"}},
                   {"run_id": "r", "k": 2, "phase": "race", "outcome": "fail", "error": {"type": "too_many_requests"}}]
            (Path(root) / "history.jsonl").write_text("\n".join(json.dumps(op) for op in ops) + "\n", encoding="utf-8")
            runs = [_thread_run("falkordb", "1"), _thread_run("omnigraph", "2", root)]
            text = report.memory_markdown(runs, "b", "T")
        self.assertIn("## Baseline claim controls (thread mode)", text)
        self.assertIn("## Omnigraph races (thread mode)", text)
        self.assertIn("| omnigraph | v0.15.0 | local | o2a.conditional_one_task.thread | negative | 3 | 55 | met | met | "
                      "1 of 2 | 0 of 1 | 1 / 2 / 0 | 10 / 10 | PASS | `2` |", text)
        self.assertIn("| omnigraph | v0.15.0 | o2a.conditional_one_task.thread | 4 | 1 | `too_many_requests` 2; "
                      "`precondition_failure` 1 | 0 | `2` |", text)
        # Valid trials only: the 90 ms spread of the invalid trial is left out; 1.5 x 10 = 15.
        self.assertIn("| omnigraph | o2a.conditional_one_task.thread | 1 | 10 | 10 | 10 | 10 | 15 |", text)
        self.assertIn("## Invalid trials (M5 runs)", text)

    def test_o2b_o6_transfer_and_unrelated_graph_tables(self):
        omni = {"role": "sut", "name": "omnigraph-server", "version": "v0.15.0", "config": {"backend": "local"}}
        base = {"harness": HARNESS, "host": HOST, "target": {"name": "omnigraph", "ref": "v0.15.0"},
                "components": [omni], "batch": "b"}
        stats = {"median": 3, "q1": 2, "q3": 4}
        sweep = base | {"run_id": "s", "started_at": "1", "scenario": {"id": "o2b.disjoint_claims", "mode": "sweep"},
                        "spread_gate": {"gate_ms": 55.0},
                        "summary": [{"n": 2, "valid_repetitions": 5, "measured_repetitions": 5, "attempts_total": stats,
                                     "wasted_attempts": {"median": 1, "q1": 0, "q3": 1},
                                     "agent_attempts_median": {"median": 1.5}, "agent_attempts_max": {"median": 2},
                                     "time_to_all_claimed_ms": stats, "claim_latency_p50_ms": {"median": 20},
                                     "claim_latency_p99_ms": {"median": 30}}],
                        "trials": [{"k": 1, "n": 2, "warmup": True, "valid": True, "holders_ok": False},
                                   {"k": 2, "n": 2, "warmup": False, "valid": True, "holders_ok": True,
                                    "claimed": 2, "agent_status": {"claimed": 2}}]}
        parity = base | {"run_id": "p", "started_at": "2", "scenario": {"id": "o6.traversal_parity", "mode": "cases"},
                         "controls": {"sequential": {"met": True, "classifications": {"q_live": "identical"},
                                                     "errors": {}}},
                         "trials": [{"k": 1, "valid": True, "classifications": {"q_live": "silently different"},
                                     "errors": {"neo4j": {"q_live": "boom"}}}]}
        transfer = base | {"run_id": "t", "started_at": "3",
                           "scenario": {"id": "o4.clean_stop_transfer", "mode": "transfer"},
                           "trials": [{"k": 1, "valid": True, "a_write": {"outcome": "ok"},
                                       "shutdown": {"exit_code": 0, "killed": False, "oom_killed": False},
                                       "admission_released": True, "successor_ready": True,
                                       "b_write": {"outcome": "ok"}, "status": "OBSERVED", "reason": "released",
                                       "integrity": {"scan_ok": True, "acknowledged_missing": []}}]}
        curve = base | {"run_id": "c", "started_at": "4", "scenario": {"id": "o1.branch_cost", "mode": "curve"},
                        "trials": [{"size": 8, "siblings": 0, "samples": [
                            {"create_ms": 1.0, "unrelated_reader_stall_ms": 4.0, "unrelated_writer_stall_ms": 6.0}]}]}
        text = report.memory_markdown([sweep, parity, transfer, curve], "b", "T")
        self.assertIn("| omnigraph | v0.15.0 | local | 55 | 2 | 5 / 5 | 3 [2–4] | 1 [0–1] | 1.50 / 2 | 3 [2–4] | "
                      "20 / 30 | 0 of 1 | 0 | `s` |", text)
        self.assertIn("| v0.15.0 | local | sequential control | q_live | identical | none | `p` |", text)
        self.assertIn("| v0.15.0 | local | trial 1 | q_live | silently different | neo4j: q_live | `p` |", text)
        self.assertIn("| v0.15.0 | local | ok | 0 | no / no | yes | yes | ok | ok | none | not engaged | OBSERVED | "
                      "released | `t` |", text)
        self.assertIn("| v0.15.0 | local | 8 / 8 | 0 | 4 | 6 | `c` |", text)

    def test_o1_read_retries_are_shown_once_runs_record_them(self):
        curve = {"run_id": "c", "batch": "b", "started_at": "1", "harness": HARNESS, "host": HOST,
                 "target": {"name": "omnigraph", "ref": "v0.15.0"},
                 "components": [{"role": "sut", "config": {"backend": "local"}}],
                 "scenario": {"id": "o1.branch_cost", "mode": "curve"},
                 "trials": [{"size": 8, "siblings": 0, "samples": [
                     {"create_ms": 1.0, "unrelated_reader_stall_ms": 4.0, "unrelated_writer_stall_ms": 6.0,
                      "read_retries": {"main_reader_during_create": 1, "unrelated_reader_during_create": 0,
                                       "main_reader_total": 2, "unrelated_reader_total": 1}},
                     {"create_ms": 1.0, "unrelated_reader_stall_ms": 4.0, "unrelated_writer_stall_ms": 6.0,
                      "read_retries": {"main_reader_during_create": 0, "unrelated_reader_during_create": 1,
                                       "main_reader_total": 0, "unrelated_reader_total": 1}}]}]}
        text = report.memory_markdown([curve], "b", "T")
        self.assertIn("Read retries during create", text)
        self.assertIn("| v0.15.0 | local | 8 / 8 | 0 | 4 | 6 | 1 / 1 | 4 | `c` |", text)

    def test_an_m4_batch_gets_none_of_the_m5_sections(self):
        curve = {"run_id": "c", "batch": "b", "started_at": "1", "harness": HARNESS, "host": HOST,
                 "target": {"name": "omnigraph", "ref": "v0.15.0"},
                 "components": [{"role": "sut", "config": {"backend": "local"}}],
                 "scenario": {"id": "o1.branch_cost", "mode": "curve"},
                 "trials": [{"size": 8, "siblings": 0, "samples": [{"create_ms": 1.0}]}]}
        text = report.memory_markdown([curve], "b", "T")
        for heading in ("Runs added in M5", "thread mode", "O2b", "O6", "clean-stop", "Unrelated graph",
                        "Invalid trials (M5 runs)"):
            self.assertNotIn(heading, text)


if __name__ == "__main__":
    unittest.main()
