"""The Omnigraph client against a loopback-only in-process HTTP server."""

from __future__ import annotations

import json
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

TARGET = Path(__file__).resolve().parents[2] / "targets" / "03-omnigraph"
sys.path.insert(0, str(TARGET))
try:
    from witnessmark_omnigraph.client import OmnigraphClient, Outcome
except ImportError as exc:  # A target checkout may intentionally be absent.
    IMPORT_ERROR = exc
else:
    IMPORT_ERROR = None


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address):
        super().__init__(address, _Handler)
        self.requests = []


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass

    def _read_body(self):
        size = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(size) if size else b""
        if self.headers.get("Content-Type") == "application/x-ndjson":
            return raw
        return json.loads(raw) if raw else None

    def _send(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    def _handle(self):
        parsed = urlsplit(self.path)
        body = self._read_body()
        self.server.requests.append((self.command, self.path, dict(self.headers), body))

        if parsed.path == "/healthz":
            return self._send(200, {"status": "ok"})
        if parsed.path.endswith("/load/ndjson"):
            return self._send(200, {"graph_commit_id": "load-commit", "entities_loaded": 1})
        if parsed.path.endswith("/query"):
            return self._send(200, {"rows": [{"task": "t1", "state": "open"}], "graph_commit_id": "c1"})
        if parsed.path.endswith("/mutate/if-graph-commit"):
            return self._send(412, {
                "error": "the graph head moved",
                "code": "precondition_failed",
                "precondition_failure": {"expected": "c1", "actual": "c2"},
                "disposition": {"effects": "none", "action": "refresh"},
            })
        if parsed.path.endswith("/mutate") and body["query"] == "cardinality":
            return self._send(409, {
                "error": "CardinalityViolation: HeldBy exceeds 1",
                "code": "conflict",
                "disposition": {"effects": "none", "action": "fix"},
            })
        if parsed.path.endswith("/mutate") and body["query"] == "cardinality_envelope":
            return self._send(400, {
                "error": "@card violation on edge HeldBy: source 'task-0' has 2 edges (max 1)",
                "code": "bad_request",
                "disposition": {"effects": "unknown", "action": "reconcile"},
            })
        if parsed.path.endswith("/mutate") and body["query"] == "server_error":
            return self._send(500, {
                "error": "internal error",
                "code": "internal",
                "disposition": {"effects": "unknown", "action": "reconcile"},
            })
        if parsed.path.endswith("/mutate") and body["query"] == "slow":
            time.sleep(0.15)
            return self._send(200, {"commit": {"graph_commit_id": "late"}})
        if parsed.path.endswith("/branches/merge") and body["source"] == "conflict":
            return self._send(409, {
                "error": "merge conflict",
                "merge_conflicts": [
                    {"kind": "CardinalityViolation", "item": "HeldBy"},
                    {"kind": "divergent_update", "item": "Task"},
                ],
                "disposition": {"effects": "none", "action": "fix"},
            })
        if "/branches" in parsed.path:
            return self._send(200, {"ok": True})
        return self._send(404, {
            "error": "not found",
            "code": "not_found",
            "disposition": {"effects": "none", "action": "fix"},
        })

    do_GET = _handle
    do_POST = _handle
    do_DELETE = _handle


@unittest.skipIf(IMPORT_ERROR is not None, f"Omnigraph client unavailable: {IMPORT_ERROR}")
class OmnigraphClientTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = _Server(("127.0.0.1", 0))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address
        cls.endpoint = f"http://{host}:{port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        self.client = OmnigraphClient(self.endpoint, "knowledge", bearer_token="secret", timeout=1)

    def test_successful_query(self):
        result = self.client.query("query q() { match { $t: Task } return { $t.id } }")
        self.assertIs(result.outcome, Outcome.OK)
        self.assertEqual(result.data["graph_commit_id"], "c1")

    def test_conditional_precondition_failure_is_a_typed_refusal(self):
        result = self.client.mutate("claim", commit_id="c1")
        self.assertIs(result.outcome, Outcome.REFUSAL)
        self.assertEqual(result.kind, "precondition_failure")
        method, path, headers, _body = self.server.requests[-1]
        self.assertEqual((method, path), ("POST", "/graphs/knowledge/mutate/if-graph-commit"))
        self.assertEqual(headers["Omnigraph-If-Graph-Commit"], "c1")

    def test_raw_ndjson_load_uses_one_classifier_path(self):
        result = self.client.load_ndjson(b'{"type":"Entry","id":"e0","data":{}}\n')
        self.assertIs(result.outcome, Outcome.OK)
        method, path, headers, body = self.server.requests[-1]
        self.assertEqual(method, "POST")
        self.assertIn("/load/ndjson?", path)
        self.assertEqual(headers["Content-Type"], "application/x-ndjson")
        self.assertIn(b'"Entry"', body)

    def test_cardinality_violation_is_a_typed_refusal(self):
        result = self.client.mutate("cardinality")
        self.assertIs(result.outcome, Outcome.REFUSAL)
        self.assertEqual(result.kind, "CardinalityViolation")

    def test_documented_cardinality_message_overrides_generic_unknown_disposition(self):
        result = self.client.mutate("cardinality_envelope")
        self.assertIs(result.outcome, Outcome.REFUSAL)
        self.assertEqual(result.kind, "CardinalityViolation")

    def test_server_error_is_unknown(self):
        result = self.client.mutate("server_error")
        self.assertIs(result.outcome, Outcome.UNKNOWN)
        self.assertEqual(result.kind, "internal")

    def test_timeout_is_unknown(self):
        client = OmnigraphClient(self.endpoint, "knowledge", timeout=0.02)
        result = client.mutate("slow")
        self.assertIs(result.outcome, Outcome.UNKNOWN)
        self.assertEqual(result.kind, "timeout")

    def test_connection_refused_before_send_is_a_definite_unavailable_refusal(self):
        class RefusedConnection:
            def request(self, *_args, **_kwargs):
                raise ConnectionRefusedError("refused before send")

            def close(self):
                pass

        with patch.object(self.client, "_connection", return_value=RefusedConnection()):
            result = self.client.health()
        self.assertIs(result.outcome, Outcome.REFUSAL)
        self.assertEqual(result.kind, "unavailable")

    def test_merge_refusal_keeps_every_conflict_kind(self):
        result = self.client.merge("conflict")
        self.assertIs(result.outcome, Outcome.REFUSAL)
        self.assertEqual(result.kind, "CardinalityViolation")
        self.assertEqual(result.data["conflict_kinds"], ["CardinalityViolation", "DivergentUpdate"])

    def test_branch_routes_and_health(self):
        self.assertTrue(self.client.branch_create("review/a", from_branch="main").ok)
        self.assertTrue(self.client.branch_delete("review/a").ok)
        self.assertTrue(self.client.branch_list(detailed=True).ok)
        self.assertTrue(self.client.merge("review/a", target="main").ok)
        self.assertTrue(self.client.health().ok)
        requests = self.server.requests[-5:]
        self.assertEqual(requests[0][1], "/graphs/knowledge/branches")
        self.assertEqual(requests[0][3], {"name": "review/a", "from": "main"})
        self.assertEqual(requests[1][1], "/graphs/knowledge/branches/review%2Fa")
        self.assertEqual(requests[2][1], "/graphs/knowledge/branches?detailed=true")
        self.assertEqual(requests[3][1], "/graphs/knowledge/branches/merge")
        self.assertNotIn("Omnigraph-Http-Api", requests[4][2])

    def test_branch_create_rejects_two_bases_without_network(self):
        before = len(self.server.requests)
        with self.assertRaises(ValueError):
            self.client.branch_create("x", from_branch="main", from_commit="c1")
        self.assertEqual(len(self.server.requests), before)


if __name__ == "__main__":
    unittest.main()
