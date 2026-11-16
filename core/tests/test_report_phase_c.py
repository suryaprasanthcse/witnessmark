"""M5 Phase C report tables: G6 (startup and KD-F4) and G7 (persistence), built from manifests alone."""

import unittest

from witnessmark.report import g6_startup_table, g6_uc_table, g7_table, memory_markdown


def component(backend):
    return [{"role": "sut", "name": "graphiti-core", "version": "0.31.2", "config": {"backend": backend}}]


def startup_run():
    uc = {"not_ready_after_creation_ms": {"at_least_ms": 5.0, "at_most_ms": 9.5},
          "not_ready_after_creation_kinds": ["under construction"], "under_construction_seen": True,
          "probe_rows_while_under_construction": {"min": 3, "max": 80}, "ready_seen": True}
    suite = {"queries": 10, "identical": 9, "different": 1, "errors": 0}
    trial = {"k": 1, "valid": True, "checks": [], "g6": {"first_query_met_unready_index": True, "at_once": suite,
                                                         "ready": {**suite, "identical": 10, "different": 0},
                                                         "uc": uc, "watch": {"unretrieved": 1, "log_errors": 2}}}
    stalled = {"k": 2, "valid": False, "invalid_reason": "a search did not return within 60 s", "checks": [],
               "g6": {"stalled": {"op_id": "2-c00-at_once-00"}, "watch": {"unretrieved": 0, "log_errors": 0}}}
    return {"run_id": "20261116T000000Z-aaaaaaaa", "started_at": "2026-11-16T00:00:00Z", "batch": "b",
            "target": {"ref": "v0.31.2", "name": "graphiti"}, "components": component("falkordb"),
            "scenario": {"id": "g6a.fresh.startup", "mode": "startup", "params": {"facts": 2000}, "invariants": []},
            "controls": [{"kind": "sequential", "met": True}], "trials": [trial, stalled], "verdicts": []}


def persistence_run():
    lost = {"lost": {"episodes": 10, "entities": 2, "facts": 10}, "lost_total": 22}
    settings = {"appendonly": "no", "appendfsync": "everysec", "save": "3600 1",
                "graph_module": {"args": ["MAX_QUEUED_QUERIES", "25"]}}
    return {"run_id": "20261116T000001Z-bbbbbbbb", "started_at": "2026-11-16T00:00:01Z", "batch": "b",
            "target": {"ref": "v0.31.2", "name": "graphiti"}, "components": component("falkordb"),
            "scenario": {"id": "g7.mcp.kill_start.persistence", "mode": "persistence", "invariants": ["I2"],
                         "params": {"variant": "mcp", "action": "kill_start", "volume_mount": "/var/lib/falkordb/data"}},
            "controls": [{"kind": "sequential", "met": True}],
            "trials": [{"k": 1, "valid": True, "checks": [], "g7": {"lost": lost, "settings_before": settings}}],
            "verdicts": [{"invariant": "I2", "status": "OBSERVED", "trials_violating": 1, "trials_valid": 1,
                          "magnitude": {"max": 22, "unit": "items lost"}}]}


class PhaseCReportTest(unittest.TestCase):
    def test_startup_table_sums_valid_trials(self):
        row = g6_startup_table([startup_run()]).splitlines()[2]
        self.assertIn("1 of 2", row)
        self.assertIn("9 / 1 / 0", row)
        self.assertIn("10 / 0 / 0", row)
        self.assertIn("`20261116T000000Z-aaaaaaaa`", row)

    def test_uc_table(self):
        row = g6_uc_table([startup_run()]).splitlines()[2]
        self.assertIn("5 / 9.50", row)
        self.assertIn("under construction", row)
        self.assertIn("3 / 80; 2000", row)

    def test_g7_table(self):
        row = g7_table([persistence_run()]).splitlines()[2]
        self.assertIn("| mcp | kill_start | met | 1 of 1 | 1 of 1 | 10 / 2 / 10 |", row)
        self.assertIn("MAX_QUEUED_QUERIES 25", row)

    def test_sections_appear_only_with_phase_c_runs(self):
        text = memory_markdown([startup_run(), persistence_run()], "b", "M5: Graphiti")
        for heading in ("## G6 index readiness at startup", "### Index state after creation returned (KD-F4)",
                        "## G7 persistence across container actions", "## Invalid trials (M5 Phase C runs)"):
            self.assertIn(heading, text)
        self.assertNotIn("Phase C", memory_markdown([], "b", "x"))


if __name__ == "__main__":
    unittest.main()
