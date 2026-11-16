"""O2b agents on kept connections (M5 batch m5f): dropped reads are recorded and retried, dropped claims are not."""

from __future__ import annotations

import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

TARGET = Path(__file__).resolve().parents[2] / "targets" / "03-omnigraph"
sys.path.insert(0, str(TARGET))

from witnessmark.history import OK, UNKNOWN  # noqa: E402

from witnessmark import report  # noqa: E402
from witnessmark_omnigraph import costcurve  # noqa: E402
from witnessmark_omnigraph.client import OmnigraphClient  # noqa: E402
from witnessmark_omnigraph.workload import load_queries  # noqa: E402


class _Graph(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, _format, *_args):
        pass

    def do_POST(self):  # noqa: N802 - http.server naming
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        kind = "claim" if "/mutate" in self.path else "read"
        self.server.seen.append(kind)
        if self.server.drop.get(kind):
            self.server.drop[kind] -= 1
            self.close_connection = True  # close the kept connection without a reply
            return
        if kind == "read":
            payload = {"columns": ["state"], "rows": [{"state": "open"}], "graph_commit_id": "c1"}
        else:
            payload = {"commit": {"graph_commit_id": "c2"}}
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class O2bKeptConnectionTest(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _Graph)
        self.server.daemon_threads = True
        self.server.seen, self.server.drop = [], {}
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.client = OmnigraphClient(f"http://127.0.0.1:{self.server.server_address[1]}", keep_alive=True)
        self.client.query("warm", {})  # opens the kept connection, as the agent's warm-up does
        self.server.seen.clear()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_a_dropped_read_is_its_own_record_then_retried_and_counted(self):
        self.server.drop = {"read": 1}
        run = costcurve.omnigraph_agent(self.client, load_queries(), 0)
        self.assertEqual(run.status, "claimed")
        self.assertEqual([(s.kind, s.outcome, s.error_type) for s in run.steps],
                         [("read", UNKNOWN, "kept_connection_dropped"), ("read", OK, None), ("claim", OK, None)])
        self.assertIsNone(run.steps[0].ret)
        self.assertTrue(run.steps[0].inputs["dropped_kept_connection"])
        self.assertEqual(self.server.seen, ["read", "read", "claim"])
        metrics = costcurve.trial_metrics([run])
        self.assertEqual((metrics["read_retries"], metrics["unknown_operations"], metrics["operations"]), (1, 0, 3))

    def test_a_dropped_claim_is_unknown_and_never_resent(self):
        self.server.drop = {"claim": 1}
        run = costcurve.omnigraph_agent(self.client, load_queries(), 0)
        self.assertEqual(run.status, "unknown")
        self.assertEqual([(s.kind, s.outcome) for s in run.steps], [("read", OK), ("claim", UNKNOWN)])
        self.assertEqual(self.server.seen, ["read", "claim"])
        metrics = costcurve.trial_metrics([run])
        self.assertEqual((metrics["read_retries"], metrics["unknown_operations"]), (0, 1))

    def test_both_engines_record_their_agent_connection_model(self):
        self.assertEqual(costcurve.OMNIGRAPH_AGENT_CONNECTIONS["model"], "kept")
        self.assertEqual(costcurve.FALKORDB_AGENT_CONNECTIONS["model"], "kept")

    def test_the_sweep_table_shows_read_retries_only_for_runs_that_record_them(self):
        base = {"run_id": "s", "batch": "b", "started_at": "1", "harness": {"commit": "a" * 40, "dirty": False},
                "host": {}, "target": {"name": "omnigraph", "ref": "v0.15.0"},
                "components": [{"role": "sut", "config": {"backend": "local"}}],
                "scenario": {"id": "o2b.disjoint_claims", "mode": "sweep"}, "spread_gate": {"gate_ms": 55.0},
                "summary": [{"n": 1, "valid_repetitions": 1, "measured_repetitions": 1}]}
        old = base | {"trials": [{"k": 1, "n": 1, "warmup": False, "valid": True, "claimed": 1}]}
        new = base | {"trials": [{"k": 1, "n": 1, "warmup": False, "valid": True, "claimed": 1, "read_retries": 2}]}
        self.assertNotIn("Read retries", report.sweep_table([old]))
        table = report.sweep_table([new])
        self.assertIn("Read retries after a dropped kept connection", table)
        self.assertTrue(table.splitlines()[2].endswith("| 0 | 2 | `s` |"))


if __name__ == "__main__":
    unittest.main()
