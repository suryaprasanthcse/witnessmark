"""O1's closed-loop loads keep one connection per client (batch m5b-20261115T230235Z, WinError 10048)."""

from __future__ import annotations

import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

TARGET = Path(__file__).resolve().parents[2] / "targets" / "03-omnigraph"
sys.path.insert(0, str(TARGET))

from witnessmark_omnigraph.client import OmnigraphClient, Outcome  # noqa: E402


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, _format, *_args):
        pass

    def do_POST(self):  # noqa: N802 - http.server naming
        size = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(size)
        self.server.ports.append(self.client_address[1])
        self.server.paths.append(self.path)
        body = json.dumps({"columns": [], "rows": []}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        if self.server.close_after_each:
            self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)


class KeepAliveTest(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.server.daemon_threads = True
        self.server.ports, self.server.paths, self.server.close_after_each = [], [], False
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.endpoint = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def test_a_kept_client_sends_every_request_on_one_connection(self):
        client = OmnigraphClient(self.endpoint, keep_alive=True)
        for _ in range(20):
            self.assertIs(client.query("q", {}).outcome, Outcome.OK)
            self.assertIs(client.mutate("m", {}).outcome, Outcome.OK)
        self.assertEqual(len(set(self.server.ports)), 1)

    def test_the_default_client_still_opens_one_connection_per_request(self):
        client = OmnigraphClient(self.endpoint)
        for _ in range(5):
            client.query("q", {})
        self.assertEqual(len(set(self.server.ports)), 5)

    def test_a_server_that_closes_each_connection_is_followed(self):
        self.server.close_after_each = True
        client = OmnigraphClient(self.endpoint, keep_alive=True)
        for _ in range(3):
            self.assertIs(client.query("q", {}).outcome, Outcome.OK)
        self.assertIsNone(client._kept)
        self.assertEqual(len(set(self.server.ports)), 3)


if __name__ == "__main__":
    unittest.main()
