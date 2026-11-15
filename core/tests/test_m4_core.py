"""Reporter gates for M4-only sections."""

import unittest
from pathlib import Path

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

    def test_i6_table_flags_an_empty_prefix_and_shows_controls_only_runs(self):
        curve = run("curve", "o1.branch_cost", [])
        curve["controls"] = {"i6": {"i6a_gapless_prefix": True, "branch_prefix_seq": [], "main_seq": [1, 2],
                                    "i6b_isolation": True}}
        controls = run("controls", "o1.i6_controls", [{"valid": True, "i6a_gapless_prefix": True,
                       "i6a_prefix_length": 6, "i6a_main_length": 20, "i6b_isolation": True}])
        controls["run_id"] = "run-controls"
        text = memory_markdown([curve, controls], "m4", "M4: Omnigraph")
        self.assertIn("## I6a and I6b controls", text)
        self.assertIn("empty prefix, not exercised", text)
        self.assertIn("| 6 / 20 |", text)

    def test_failover_table_names_who_scanned_and_what_is_missing(self):
        matrix = run("matrix", "o4.failover_acceptance", [{
            "phase": "p1", "variant": "b", "successor_ready": True, "a_write": {"outcome": "ok"},
            "b_write": {"outcome": "ok"}, "writer_fenced_observed": False, "graph_open_and_scan": True,
            "status": "BOUNDARY", "integrity": {"scanned_via": "wm-omnigraph-b", "acknowledged_missing": ["a-p1-b"]}}])
        text = memory_markdown([matrix], "m4", "M4: Omnigraph")
        self.assertIn("wm-omnigraph-b", text)
        self.assertIn("a-p1-b", text)

    def test_falkor_table_reports_persistence_and_stalls(self):
        curve = run("curve", "o1.branch_cost", [])
        curve["controls"] = {"falkordb": {
            "persistence_during_curve": {"appendonly": "yes", "appendfsync": "always"},
            "persistence_found": {"appendonly": "no", "appendfsync": "everysec"},
            "rows": [{"size": 32000, "s28_reference_ms": 165, "inside_50_percent_band": True,
                      "copy_ms": {"median": 95.0, "q1": 90.0, "q3": 100.0},
                      "samples": [{"delete_ms": 1.0, "source_reader_stall_ms": 90.0, "unrelated_reader_stall_ms": 91.0,
                                   "unrelated_writer_stall_ms": 92.0, "rss_before_mb": 100.0, "rss_after_mb": 130.0,
                                   "aof_bytes": 5}]}]}}
        text = memory_markdown([curve], "m4", "M4: Omnigraph")
        self.assertIn("`appendfsync always`", text)
        self.assertIn("Unrelated writer stall", text)

    def test_a_run_that_never_finished_is_listed_with_its_error(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "ERROR.md").write_text("# Run error\n\n- Error: `RuntimeError: it broke`\n",
                                                   encoding="utf-8")
            planned = run("curve", "o1.branch_cost", [])
            planned.update({"status": "planned-before-execution", "_dir": directory})
            text = memory_markdown([planned], "m4", "M4: Omnigraph")
        self.assertIn("## Runs that did not complete", text)
        self.assertIn("RuntimeError: it broke", text)

    def test_the_first_versions_hard_coded_boundary_label_is_marked_superseded(self):
        matrix = run("matrix", "o4.failover_acceptance", [{
            "phase": "p1", "variant": "a", "successor_ready": False, "a_write": {"outcome": "ok"},
            "b_write": None, "writer_fenced_observed": False, "graph_open_and_scan": True,
            "status": "BOUNDARY", "boundary": "the pinned server exposes no branch writer-claim route"}])
        self.assertIn("BOUNDARY (first-version label, superseded)", memory_markdown([matrix], "m4", "M4"))

if __name__ == "__main__":
    unittest.main()
