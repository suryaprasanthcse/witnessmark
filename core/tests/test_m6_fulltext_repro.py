"""M6 Phase C: the FalkorDB fulltext repro's RESP parsing, sample classifier and trial loop, on a fake transport.

The repro is a single standalone file (baselines/repros/), so it is loaded by path. No network and no engine.
"""

import contextlib
import importlib.util
import io
import unittest
from pathlib import Path

REPRO = Path(__file__).resolve().parents[2] / "baselines" / "repros" / "repro_falkordb_fulltext_under_construction.py"
_spec = importlib.util.spec_from_file_location("repro_fulltext", REPRO)
repro = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(repro)

STATS = ["Query internal execution time: 0.1 milliseconds"]


def table(header, rows):
    return [header, rows, STATS]


class FakeClient:
    """Answers the repro's commands. `script` gives, per sample after CREATE INDEX, the index status (None for not
    listed) and the probe's answer (a row count or a RespError). The last step repeats."""

    def __init__(self, n, script, loaded=None, status_error=None):
        self.n, self.script, self.loaded = n, list(script), n if loaded is None else loaded
        self.status_error = status_error
        self.created = False
        self.step = None
        self.commands = []

    def command(self, *args):
        self.commands.append(args)
        if args[0] == "GRAPH.DELETE":
            existed, self.created = self.created, False
            if not existed:
                raise repro.RespError("ERR Invalid graph operation on empty key")
            return "OK"
        if args[0] == "INFO":
            return "# Server\r\nredis_version:7.4.2\r\n"
        if args[0] == "MODULE":
            return [["name", "graph", "ver", 60004, "path", "/x", "args", []]]
        cypher = args[2]
        if cypher.startswith("UNWIND"):
            return [STATS]
        if cypher == repro.COUNT_LOADED:
            return table(["count(r)"], [[self.loaded]])
        if cypher == repro.CREATE_INDEX:
            self.created = True
            return [STATS]
        if cypher == repro.INDEXES:
            if not self.created:
                return table(["label", "types", "entitytype", "status"], [])
            self.step = self.script.pop(0) if len(self.script) > 1 else self.script[0]
            if self.status_error:
                raise repro.RespError(self.status_error)
            status = self.step[0]
            rows = [["RELATES_TO", ["i", ["RANGE"]], "RELATIONSHIP", "OPERATIONAL"]]  # not the fulltext index
            if status is not None:
                rows.append(["RELATES_TO", ["fact", ["FULLTEXT"]], "RELATIONSHIP", status])
            return table(["label", "types", "entitytype", "status"], rows)
        if cypher == repro.PROBE:
            answer = self.step[1] if self.step else 0
            if isinstance(answer, repro.RespError):
                raise answer
            return table(["count(relationship)"], [[answer]])
        raise AssertionError(f"unexpected command {args}")

    def close(self):
        pass


class Ticker:
    def __init__(self, step=0.001):
        self.now, self.step = 0.0, step

    def __call__(self):
        self.now += self.step
        return self.now


UC = "[Indexing] 120/2000: UNDER CONSTRUCTION"


class ClassifierTest(unittest.TestCase):
    def test_every_class(self):
        n = 2000
        self.assertEqual(repro.classify(None, None, 0, None, n), "no_index_rows")
        self.assertEqual(repro.classify(None, None, None, "ERR no such index", n), "no_index_error")
        self.assertEqual(repro.classify(UC, None, 1999, None, n), "uc_fewer")
        self.assertEqual(repro.classify(UC, None, 0, None, n), "uc_fewer")
        self.assertEqual(repro.classify(UC, None, 2000, None, n), "uc_all")
        self.assertEqual(repro.classify(UC, None, None, "ERR boom", n), "uc_error")
        self.assertEqual(repro.classify("OPERATIONAL", None, 2000, None, n), "operational")
        self.assertEqual(repro.classify(UC, None, 2001, None, n), "other")
        self.assertEqual(repro.classify("FAILED", None, 0, None, n), "other")
        self.assertEqual(repro.classify(None, "ERR status", 0, None, n), "other")
        self.assertEqual(set(repro.CLASSES),
                         {"no_index_rows", "no_index_error", "uc_fewer", "uc_all", "uc_error", "operational", "other"})

    def test_status_category_drops_progress(self):
        self.assertEqual(repro.status_category(UC), "UNDER CONSTRUCTION")
        self.assertEqual(repro.status_category("[Indexing] 0/1000: UNDER CONSTRUCTION"), "UNDER CONSTRUCTION")
        self.assertEqual(repro.status_category("OPERATIONAL"), "OPERATIONAL")
        self.assertEqual(repro.status_category(" operational "), "OPERATIONAL")

    def test_finds_the_fulltext_index_only(self):
        rows = [["Entity", ["i", ["RANGE"]], "NODE", "OPERATIONAL"],
                ["RELATES_TO", ["i", ["RANGE"]], "RELATIONSHIP", "OPERATIONAL"],
                ["RELATES_TO", ["fact", ["FULLTEXT"]], "RELATIONSHIP", UC]]
        self.assertEqual(repro.relates_to_fulltext(rows), UC)
        self.assertIsNone(repro.relates_to_fulltext(rows[:2]))
        self.assertIsNone(repro.relates_to_fulltext([]))


class RespTest(unittest.TestCase):
    def test_encode(self):
        self.assertEqual(repro.encode("GRAPH.QUERY", "g", "RETURN 1"),
                         b"*3\r\n$11\r\nGRAPH.QUERY\r\n$1\r\ng\r\n$8\r\nRETURN 1\r\n")

    def test_read_reply(self):
        data = (b"*3\r\n*1\r\n$8\r\ncount(r)\r\n*1\r\n*2\r\n:2000\r\n$-1\r\n*1\r\n+done\r\n"
                b"-ERR boom\r\n")
        stream = io.BytesIO(data)
        self.assertEqual(repro.read_reply(stream), [["count(r)"], [[2000, None]], ["done"]])
        error = repro.read_reply(stream)
        self.assertIsInstance(error, repro.RespError)
        self.assertEqual(str(error), "ERR boom")
        with self.assertRaises(ConnectionError):
            repro.read_reply(stream)

    def test_rows_of(self):
        self.assertEqual(repro.rows_of(table(["a"], [[1]])), [[1]])
        self.assertEqual(repro.rows_of([STATS]), [])


class TrialTest(unittest.TestCase):
    def test_trial_classifies_each_sample(self):
        n = 2000
        script = [(None, 0), (UC, 37), (UC, n), (UC, repro.RespError("ERR busy")), ("OPERATIONAL", n)]
        client = FakeClient(n, script)
        trial = repro.run_trial(client, n, clock=Ticker())
        self.assertTrue(trial["valid"], trial["reason"])
        self.assertEqual([s["class"] for s in trial["samples"]],
                         ["no_index_rows", "uc_fewer", "uc_all", "uc_error", "operational"])
        self.assertEqual(trial["control_rows"], n)
        self.assertEqual(repro.counts(trial["samples"])["uc_fewer"], 1)
        loads = [c for c in client.commands if c[0] == "GRAPH.QUERY" and c[2].startswith("UNWIND")]
        self.assertEqual(len(loads), 2)
        self.assertIn("range(1000, 1999)", loads[1][2])
        probes = [c for c in client.commands if c[-1] == repro.PROBE]
        self.assertEqual(len(probes), 6)  # five samples and the control
        self.assertTrue(all(c[0] == "GRAPH.RO_QUERY" for c in probes))

    def test_control_not_met_is_invalid(self):
        trial = repro.run_trial(FakeClient(2000, [("OPERATIONAL", 1999)]), 2000, clock=Ticker())
        self.assertFalse(trial["valid"])
        self.assertIn("control", trial["reason"])

    def test_timeout_is_invalid(self):
        trial = repro.run_trial(FakeClient(10, [(UC, 3)]), 10, timeout_s=0.05, clock=Ticker(0.01))
        self.assertFalse(trial["valid"])
        self.assertIn("not OPERATIONAL", trial["reason"])
        self.assertTrue(all(s["class"] == "uc_fewer" for s in trial["samples"]))

    def test_short_load_is_invalid(self):
        trial = repro.run_trial(FakeClient(10, [("OPERATIONAL", 10)], loaded=9), 10, clock=Ticker())
        self.assertFalse(trial["valid"])
        self.assertEqual(trial["samples"], [])

    def test_status_read_error_is_other(self):
        trial = repro.run_trial(FakeClient(10, [(UC, 3)], status_error="ERR x"), 10, timeout_s=0.02,
                                clock=Ticker(0.01))
        self.assertTrue(trial["samples"])
        self.assertTrue(all(s["class"] == "other" for s in trial["samples"]))

    def test_runs_merge_consecutive_classes(self):
        samples = [{"class": c, "t_ms": t, "status_raw": UC, "rows": r, "status_error": None, "query_error": None}
                   for c, t, r in [("uc_fewer", 1.0, 5), ("uc_fewer", 2.0, 9), ("uc_all", 3.0, 10)]]
        merged = repro.runs(samples)
        self.assertEqual([(m["class"], m["count"], m["rows"]) for m in merged],
                         [("uc_fewer", 2, [5, 9]), ("uc_all", 1, [10])])
        self.assertIn("rows 5-9", repro.describe_run(merged[0]))


class OutputTest(unittest.TestCase):
    def test_plain_steps(self):
        steps = repro.plain_steps(2500)
        loads = [s for s in steps if "UNWIND" in s]
        self.assertEqual(len(loads), 3)
        self.assertIn("range(2000, 2499)", loads[-1])
        self.assertIn(repro.CREATE_INDEX, steps[-4])
        self.assertTrue(steps[0].startswith("GRAPH.DELETE"))

    def _main(self, script):
        original = repro.Client
        repro.Client = lambda host, port: FakeClient(20, script)
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                code = repro.main(["repro", "127.0.0.1", "16380", "20", "2"])
        finally:
            repro.Client = original
        return code, out.getvalue()

    def test_main_exit_codes(self):
        code, text = self._main([(UC, 4), ("OPERATIONAL", 20)])
        self.assertEqual(code, 1)
        self.assertIn("Totals over 2 valid of 2 trials", text)
        self.assertIn("module graph ver 60004", text)
        self.assertIn("CREATE FULLTEXT INDEX FOR ()-[r:RELATES_TO]-() ON (r.fact)", text)
        self.assertEqual(self._main([(UC, 20), ("OPERATIONAL", 20)])[0], 0)
        self.assertEqual(self._main([("OPERATIONAL", 19)])[0], 2)


if __name__ == "__main__":
    unittest.main()
