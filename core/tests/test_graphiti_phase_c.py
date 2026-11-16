"""M5 Phase C: the Graphiti G6-G8 logic that runs without Graphiti, an engine or Docker (fakes only)."""

import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "targets" / "01-zep-graphiti"))
try:
    from witnessmark_graphiti import fixtures, measure, nemesis
    from witnessmark_graphiti.scenarios import G8RemoveVsAdd, g8_checks
except ImportError as exc:
    raise unittest.SkipTest(f"Graphiti harness helpers unavailable: {exc}") from exc

from witnessmark.history import OK, UNKNOWN, Op, validate_history
from witnessmark.stubs import tokens
from witnessmark.timing import Stamp


def falkor_row(label, types, status, entity="NODE"):
    return {"label": label, "types": types, "entitytype": entity, "status": status}


def sample(inv, ret, ready, states, graph="g", missing=0, rows=None, error=None):
    return {"graph": graph, "inv": Stamp(inv, "2026-11-16T00:00:00Z"), "ret": Stamp(ret, "2026-11-16T00:00:00Z"),
            "inv_ns": inv, "ret_ns": ret, "error": error, "probe_rows": rows, "probe_error": None,
            "summary": {"rows": 1, "states": states, "missing": missing, "relates_to_fulltext": "x", "ready": ready}}


class IndexStateTest(unittest.TestCase):
    def test_status_category_drops_falkordb_progress(self):
        self.assertEqual(measure.status_category("[Indexing] 0/1000: UNDER CONSTRUCTION"), "UNDER CONSTRUCTION")
        self.assertEqual(measure.status_category("OPERATIONAL"), "OPERATIONAL")
        self.assertEqual(measure.status_category("ONLINE"), "ONLINE")
        self.assertEqual(measure.status_category(None), "absent")

    def test_falkordb_summary_needs_every_expected_key_operational(self):
        rows = [falkor_row("Entity", {"uuid": ["RANGE"], "name": ["RANGE", "FULLTEXT"]}, "OPERATIONAL"),
                falkor_row("RELATES_TO", {"fact": ["FULLTEXT"]}, "[Indexing] 0/5: UNDER CONSTRUCTION",
                           "RELATIONSHIP")]
        expected = measure.index_keys("falkordb", rows)
        self.assertEqual(len(expected), 4)
        summary = measure.index_summary("falkordb", rows, expected)
        self.assertFalse(summary["ready"])
        self.assertEqual(summary["relates_to_fulltext"], "UNDER CONSTRUCTION")
        self.assertTrue(measure.under_construction(summary))
        rows[1]["status"] = "OPERATIONAL"
        self.assertTrue(measure.index_summary("falkordb", rows, expected)["ready"])
        self.assertFalse(measure.index_summary("falkordb", rows[:1], expected)["ready"])  # one index missing
        self.assertFalse(measure.index_summary("falkordb", [], set())["ready"])  # nothing listed is not ready

    def test_neo4j_summary_uses_names_and_online(self):
        rows = [{"name": "edge_name_and_fact", "state": "POPULATING"}, {"name": "entity_uuid", "state": "ONLINE"}]
        expected = measure.index_keys("neo4j", rows)
        summary = measure.index_summary("neo4j", rows, expected)
        self.assertFalse(summary["ready"])
        self.assertEqual(summary["relates_to_fulltext"], "POPULATING")
        self.assertTrue(measure.under_construction(summary))
        rows[0]["state"] = "ONLINE"
        self.assertTrue(measure.index_summary("neo4j", rows, expected)["ready"])


class MonitorTest(unittest.TestCase):
    def test_compress_keeps_runs_per_graph_with_counts_and_last_return(self):
        samples = [sample(0, 1, False, {"UNDER CONSTRUCTION": 1}, rows=0),
                   sample(2, 3, False, {"UNDER CONSTRUCTION": 1}, rows=0),
                   sample(4, 5, False, {"UNDER CONSTRUCTION": 1}, rows=7),
                   sample(6, 7, True, {"OPERATIONAL": 1}, rows=10)]
        runs = measure.compress(samples)
        self.assertEqual([r["samples"] for r in runs], [2, 1, 1])
        self.assertEqual(runs[0]["ret_ns"], 3)

    def test_uc_report_bounds_after_creation(self):
        ms = 1_000_000
        samples = [sample(0, 1 * ms, False, {}, missing=3),
                   sample(10 * ms, 11 * ms, False, {"UNDER CONSTRUCTION": 1}, rows=4),
                   sample(20 * ms, 21 * ms, False, {"UNDER CONSTRUCTION": 1}, rows=9),
                   sample(30 * ms, 31 * ms, True, {"OPERATIONAL": 1}, rows=12)]
        builds = [{"database": "g", "outcome": "ok", "ret_ns": 5 * ms},
                  {"database": "other", "outcome": "ok", "ret_ns": 1 * ms}]
        report = measure.uc_report(samples, builds, "g", "g")
        self.assertEqual(report["not_ready_after_creation_ms"], {"at_least_ms": 15.0, "at_most_ms": 26.0})
        self.assertEqual(report["not_ready_after_creation_kinds"], ["under construction"])
        self.assertTrue(report["under_construction_seen"])
        self.assertEqual(report["probe_rows_while_under_construction"], {"min": 4, "max": 9})
        self.assertEqual(report["under_construction_span_ms"], 20.0)

    def test_uc_report_is_zero_when_ready_before_creation_returned(self):
        ms = 1_000_000
        samples = [sample(0, 1 * ms, True, {"OPERATIONAL": 1})]
        report = measure.uc_report(samples, [{"database": "g", "outcome": "ok", "ret_ns": 5 * ms}], "g", "g")
        self.assertEqual(report["not_ready_after_creation_ms"], {"at_least_ms": 0.0, "at_most_ms": 0.0})
        self.assertFalse(report["under_construction_seen"])

    def test_state_before_picks_last_finished_sample(self):
        samples = [sample(0, 2, False, {}), sample(3, 5, True, {"OPERATIONAL": 1})]
        self.assertFalse(measure.state_before(samples, 4, "g")["summary"]["ready"])
        self.assertTrue(measure.state_before(samples, 6, "g")["summary"]["ready"])
        self.assertIsNone(measure.state_before(samples, 1, "g"))


class AnswersTest(unittest.TestCase):
    def test_classify_compares_multisets(self):
        self.assertEqual(measure.classify({"facts": ["b", "a"], "error": None}, ["a", "b"]), "identical")
        self.assertEqual(measure.classify({"facts": ["a"], "error": None}, ["a", "b"]), "different")
        self.assertEqual(measure.classify({"facts": None, "error": {"type": "x"}}, ["a"]), "error")

    def test_suite_summary_counts(self):
        control = {"q1": ["a"], "q2": ["b", "c"], "q3": ["d"]}
        answers = [{"query": "q1", "facts": ["a"], "error": None},
                   {"query": "q2", "facts": ["c", "b"], "error": None},
                   {"query": "q3", "facts": None, "error": {"type": "target.ClientError"}}]
        summary = measure.suite_summary(answers, control)
        self.assertEqual((summary["identical"], summary["different"], summary["errors"], summary["order_only"]),
                         (2, 0, 1, 1))
        self.assertEqual(summary["error_types"], {"target.ClientError": 1})

    def test_lost_items(self):
        before = {"episodes": ["E1", "E2"], "entities": [{"name": "A"}], "facts": [{"fact": "f1"}, {"fact": "f2"}]}
        after = {"episodes": ["E1"], "entities": [{"name": "A"}], "facts": []}
        lost = measure.lost_items(before, after)
        self.assertEqual(lost["lost"], {"episodes": 1, "entities": 0, "facts": 2})
        self.assertEqual(lost["lost_total"], 3)
        self.assertEqual(measure.lost_items(before, before)["lost_total"], 0)


class NemesisTest(unittest.TestCase):
    def test_actions_become_nemesis_records(self):
        calls = []

        def runner(args, timeout):
            calls.append(args)
            return (0, "done") if args[1] != "kill" else (1, "no such container")

        n = nemesis.Nemesis("20261116T000000Z-00000000", runner)
        ok = n.act(1, "restart", ["docker", "restart", "wm-falkordb"], container="wm-falkordb")
        bad = n.act(1, "kill", ["docker", "kill", "wm-x"])
        self.assertEqual((ok.client, ok.phase, ok.outcome), ("nemesis", "nemesis", OK))
        self.assertEqual(bad.outcome, UNKNOWN)
        self.assertIsNone(bad.ret)
        self.assertEqual(bad.error["code"], 1)
        self.assertNotEqual(ok.op_id, bad.op_id)
        self.assertEqual(len(n.drain()), 2)
        self.assertEqual(n.drain(), [])

    def test_g7_steps(self):
        kinds = [k for k, _, _ in nemesis.g7_action_steps("down_up", "root")]
        self.assertEqual(kinds, ["stop", "start"])
        self.assertIn("down", nemesis.g7_action_steps("down_up", "root")[0][1])
        self.assertEqual([k for k, _, _ in nemesis.g7_action_steps("kill_start", "mcp")], ["kill", "start"])
        self.assertEqual(nemesis.g7_action_steps("kill_start", "mcp")[0][1], ["docker", "kill", "wm-g7-mcp"])
        self.assertEqual([k for k, _, _ in nemesis.g7_action_steps("compose_restart", "mcp")], ["restart"])
        fresh = nemesis.g7_fresh_steps("root")
        self.assertEqual([k for k, _, _ in fresh], ["stop", "delete_volume", "start"])
        self.assertIn("witnessmark-g7_g7_root_data", fresh[1][1])
        with self.assertRaises(ValueError):
            nemesis.g7_action_steps("pause", "root")

    def test_records_validate(self):
        import tempfile

        from witnessmark.history import write_history

        n = nemesis.Nemesis("20261116T000000Z-00000000", lambda args, timeout: (0, ""))
        n.act(0, "start", ["docker", "start", "x"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "history.jsonl"
            write_history(path, n.drain())
            self.assertEqual(validate_history(path), 1)


class FixturesTest(unittest.TestCase):
    def test_g6_declared_size(self):
        fixture = fixtures.g6()
        self.assertEqual(len(fixture.episodes), 400)
        self.assertEqual(sum(len(e.facts) for e in fixture.episodes), 2000)
        self.assertTrue(all(fixtures.G6_PROBE_TERM in f.fact for e in fixture.episodes for f in e.facts))
        self.assertEqual(fixtures.build("g6@3", "2026-11-16T00:00:00Z").episodes[-1].tag, "G6E0002")

    def test_g6_queries_have_one_right_answer(self):
        fixture = fixtures.g6()
        slots = Counter(fixtures._slot(w) for e in fixture.episodes for f in e.facts for w in set(tokens(f.fact)))
        queries = fixtures.g6_queries()
        self.assertEqual(len(queries), 10)
        self.assertEqual(len({q for q, _ in queries}), 10)
        for query, fact in queries:
            self.assertIn(query, fact)
            self.assertEqual(slots[fixtures._slot(query.lower())], 1, query)
        self.assertEqual(queries, fixtures.g6_queries())  # deterministic

    def test_g6c_and_g7_and_g8(self):
        self.assertEqual(len(fixtures.g6c().episodes), 8)
        for g in range(8):
            query, fact = fixtures.g6c_query(g)
            self.assertIn(query, fact)
        self.assertEqual(len(fixtures.g7().episodes), 10)
        g8 = fixtures.g8()
        self.assertEqual([e.tag for e in g8.episodes], ["G8S", "G8E", "G8N"])
        named = {e.tag: {x.name for x in e.entities} for e in g8.episodes}
        self.assertNotIn("Payments", named["G8S"])
        self.assertIn("Payments", named["G8E"] & named["G8N"])


def g8_state(episodes, facts, entities, shared_episodes=1):
    return {"episodes": episodes,
            "facts": [{"fact": f, "episodes": shared_episodes if f == fixtures.G8_SHARED_FACT else 1} for f in facts],
            "entities": [{"name": e.title(), "key": e, "mentioned_by": []} for e in entities]}


def g8_ops(remove=OK, add=OK):
    stamp = Stamp(1, "2026-11-16T00:00:00Z")
    run = "20261116T000000Z-00000000"
    return [Op(run, 1, "race", "1-c00-0", "c00", "delete", {"group": "wm_g8", "tag": "G8E", "entry": "remove_episode"},
               stamp, stamp if remove == OK else None, remove),
            Op(run, 1, "race", "1-c01-0", "c01", "ingest", {"group": "wm_g8", "tag": "G8N", "entry": "add_episode"},
               stamp, stamp if add == OK else None, add)]


class G8ChecksTest(unittest.TestCase):
    good = (["G8N", "G8S"], [fixtures.G8_SHARED_FACT, fixtures.G8_ADDED_FACT], ["alice", "acme", "payments"])

    def test_clean_state_passes(self):
        checks = {c.invariant: c for c in g8_checks(g8_ops(), g8_state(*self.good), "wm_g8")}
        self.assertTrue(all(c.held for c in checks.values()), [c.detail for c in checks.values()])

    def test_overreach_is_i2_with_cause_delete(self):
        state = g8_state(["G8N", "G8S"], [fixtures.G8_SHARED_FACT], ["alice", "acme"])
        checks = {c.invariant: c for c in g8_checks(g8_ops(), state, "wm_g8")}
        self.assertFalse(checks["I2"].held)
        self.assertEqual(checks["I2"].magnitude, 2)
        self.assertIn("cause = delete", checks["I2"].detail)
        self.assertTrue(checks["I5"].held)

    def test_resurrection_and_stale_provenance_are_i5(self):
        state = g8_state(["G8N", "G8S"], [*self.good[1], fixtures.G8_REMOVED_FACT], self.good[2], shared_episodes=2)
        check = next(c for c in g8_checks(g8_ops(), state, "wm_g8") if c.invariant == "I5")
        self.assertFalse(check.held)
        self.assertEqual(check.magnitude, 2)

    def test_unacknowledged_operations_relax_the_checks(self):
        state = g8_state(["G8S", "G8E"], [fixtures.G8_SHARED_FACT, fixtures.G8_REMOVED_FACT], ["alice", "acme",
                                                                                               "payments"], 2)
        checks = {c.invariant: c for c in g8_checks(g8_ops(remove=UNKNOWN, add=UNKNOWN), state, "wm_g8")}
        self.assertTrue(checks["I5"].held)
        self.assertTrue(checks["I2"].held)

    def test_duplicate_entity_is_i1b(self):
        state = g8_state(*self.good)
        state["entities"].append({"name": "Payments", "key": "payments", "mentioned_by": ["G8N"]})
        check = next(c for c in g8_checks(g8_ops(), state, "wm_g8") if c.invariant == "I1B")
        self.assertFalse(check.held)

    def test_sequential_expected(self):
        scenario = G8RemoveVsAdd("2026-11-16T00:00:00Z")
        met, _, _ = scenario.sequential_expected(g8_ops(), {"wm_g8": g8_state(*self.good)})
        self.assertTrue(met)
        met, _, _ = scenario.sequential_expected(g8_ops(), {"wm_g8": g8_state(*self.good, shared_episodes=2)})
        self.assertFalse(met)
        self.assertEqual([item.get("entry", "add_episode") for _, item in scenario.clients()],
                         ["remove_episode", "add_episode"])


if __name__ == "__main__":
    unittest.main()
