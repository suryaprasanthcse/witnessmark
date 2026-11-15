"""Reporter gates for M4-only sections."""

import unittest

from witnessmark.report import memory_markdown


def run(mode, scenario, trials):
    return {
        "run_id": f"run-{mode}", "batch": "m4", "started_at": "2026-11-15T00:00:00Z",
        "harness": {"commit": "abc", "dirty": False},
        "host": {"os": "test", "cpu": "test", "cores": 1, "memory_gb": 1},
        "target": {"name": "omnigraph", "ref": "edge"},
        "components": [{"role": "sut", "name": "omnigraph-server", "version": "edge",
                        "config": {"backend": "local"}}],
        "scenario": {"id": scenario, "mode": mode, "invariants": []},
        "trials": trials,
    }


class M4ReportTest(unittest.TestCase):
    def test_cost_and_failover_sections_are_gated_by_mode(self):
        curve = run("curve", "o1.branch_cost", [{"size": 32000, "siblings": 0, "timing_kind": "timing",
                    "samples": [{"create_ms": 1.0, "stall_ms": 0.2, "reader_p99_before_ms": 0.1,
                                 "reader_p99_during_ms": 0.3, "merge_unchanged_ms": 0.5,
                                 "delete_ms": 0.4}]}])
        matrix = run("matrix", "o4.failover_acceptance", [{"phase": "p1", "variant": "a",
                     "successor_ready": True, "a_write": {"kind": "WriterFenced"}, "b_write": None,
                     "writer_fenced_observed": True, "graph_open_and_scan": True, "status": "BOUNDARY"}])
        text = memory_markdown([curve, matrix], "m4", "M4: Omnigraph")
        self.assertIn("## O1 branch-creation cost", text)
        self.assertIn("## O4 failover acceptance matrix", text)
        self.assertIn("BOUNDARY", text)

    def test_visibility_section(self):
        visibility = run("visibility", "o5.cross_process_ryw", [{"second_process": "b",
                         "write_acknowledged": True, "seen": True, "attempts": 1, "staleness_ms": 2.5}])
        self.assertIn("## O5 cross-process read your writes",
                      memory_markdown([visibility], "m4", "M4: Omnigraph"))


if __name__ == "__main__":
    unittest.main()
