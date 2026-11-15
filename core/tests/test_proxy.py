"""The fixed-delay proxy against a loopback fake object store."""

from __future__ import annotations

import http.client
import json
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from witnessmark.proxy import CONTROL_PREFIX, CountingProxy


class Upstream(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self):
        super().__init__(("127.0.0.1", 0), UpstreamHandler)
        self.seen = []


class UpstreamHandler(BaseHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass

    def handle_request(self):
        size = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(size)
        self.server.seen.append((self.command, self.path, self.headers.get("Host"), body))
        response = self.command.encode("ascii") + b":" + body
        self.send_response(201)
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(response)

    do_GET = handle_request
    do_POST = handle_request
    do_PUT = handle_request


class ProxyTest(unittest.TestCase):
    def setUp(self):
        self.upstream = Upstream()
        upstream_host, upstream_port = self.upstream.server_address
        self.proxy = CountingProxy(("127.0.0.1", 0), f"http://{upstream_host}:{upstream_port}", 17)
        self.threads = [threading.Thread(target=self.upstream.serve_forever, daemon=True),
                        threading.Thread(target=self.proxy.serve_forever, daemon=True)]
        for thread in self.threads:
            thread.start()

    def tearDown(self):
        self.proxy.shutdown()
        self.upstream.shutdown()
        self.proxy.server_close()
        self.upstream.server_close()
        for thread in self.threads:
            thread.join(timeout=2)

    def request(self, method, path, body=None, headers=None):
        host, port = self.proxy.server_address
        connection = http.client.HTTPConnection(host, port, timeout=2)
        started = time.perf_counter()
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        payload = response.read()
        elapsed = time.perf_counter() - started
        connection.close()
        return response.status, payload, elapsed

    def test_forwards_with_delay_and_counts_bytes_by_method(self):
        status, body, elapsed = self.request("PUT", "/bucket/key?partNumber=1", b"hello",
                                             {"Host": "signed.example:19010"})
        self.assertEqual((status, body), (201, b"PUT:hello"))
        self.assertGreaterEqual(elapsed, 0.014)
        self.assertEqual(self.upstream.seen, [
            ("PUT", "/bucket/key?partNumber=1", "signed.example:19010", b"hello")
        ])

        status, body, _ = self.request("GET", f"{CONTROL_PREFIX}/counts")
        self.assertEqual(status, 200)
        counts = json.loads(body)
        self.assertEqual(counts["delay_ms"], 17)
        self.assertEqual(counts["methods"], {
            "PUT": {"requests": 1, "request_bytes": 5, "response_bytes": 9}
        })

    def test_reset_endpoint_is_not_forwarded_or_counted(self):
        self.request("GET", "/bucket")
        status, body, _ = self.request("POST", f"{CONTROL_PREFIX}/reset")
        self.assertEqual((status, json.loads(body)), (200, {"reset": True}))
        _, body, _ = self.request("GET", f"{CONTROL_PREFIX}/counts")
        self.assertEqual(json.loads(body)["methods"], {})
        self.assertEqual(len(self.upstream.seen), 1)


if __name__ == "__main__":
    unittest.main()
