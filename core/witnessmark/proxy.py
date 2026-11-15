"""Fixed-delay counting HTTP proxy for matched object-store repetitions.

The proxy is deliberately small and standard-library only. It preserves
end-to-end request headers (including ``Host`` for S3 signatures), removes
hop-by-hop headers, waits once per forwarded request, and counts request and
response body bytes by HTTP method. Its own control endpoints are not counted.
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import threading
import time
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

CONTROL_PREFIX = "/__witnessmark__"
HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "proxy-connection", "te", "trailer", "transfer-encoding", "upgrade",
}


class Counters:
    """Thread-safe request and byte counters grouped by uppercase method."""

    def __init__(self, delay_ms: float):
        self.delay_ms = delay_ms
        self._lock = threading.Lock()
        self._methods: dict[str, dict[str, int]] = defaultdict(
            lambda: {"requests": 0, "request_bytes": 0, "response_bytes": 0}
        )

    def add(self, method: str, request_bytes: int, response_bytes: int) -> None:
        with self._lock:
            row = self._methods[method.upper()]
            row["requests"] += 1
            row["request_bytes"] += request_bytes
            row["response_bytes"] += response_bytes

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "delay_ms": self.delay_ms,
                "methods": {method: dict(values) for method, values in sorted(self._methods.items())},
            }

    def reset(self) -> None:
        with self._lock:
            self._methods.clear()


class CountingProxy(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], upstream: str, delay_ms: float):
        parsed = urlsplit(upstream)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("upstream must be an http(s) origin")
        if parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ValueError("upstream must not contain credentials, a query or a fragment")
        self.upstream_scheme = parsed.scheme
        self.upstream_host = parsed.hostname
        self.upstream_port = parsed.port or (443 if parsed.scheme == "https" else 80)
        self.upstream_prefix = parsed.path.rstrip("/")
        self.delay_seconds = delay_ms / 1000.0
        self.counters = Counters(delay_ms)
        super().__init__(address, ProxyHandler)

    def connection(self) -> http.client.HTTPConnection:
        cls = http.client.HTTPSConnection if self.upstream_scheme == "https" else http.client.HTTPConnection
        return cls(self.upstream_host, self.upstream_port, timeout=120)


class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: CountingProxy

    def log_message(self, _format: str, *_args) -> None:
        pass

    def _read_chunked(self) -> bytes:
        chunks = []
        while True:
            line = self.rfile.readline(65537)
            if not line or len(line) > 65536:
                raise ValueError("invalid chunk header")
            size = int(line.split(b";", 1)[0].strip(), 16)
            if size == 0:
                while self.rfile.readline(65537) not in (b"\r\n", b"\n", b""):
                    pass
                return b"".join(chunks)
            chunk = self.rfile.read(size)
            if len(chunk) != size or self.rfile.read(2) != b"\r\n":
                raise ValueError("truncated chunked body")
            chunks.append(chunk)

    def _read_body(self) -> bytes:
        transfer = self.headers.get("Transfer-Encoding", "").lower()
        if "chunked" in transfer:
            return self._read_chunked()
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b""
        if len(body) != length:
            raise ValueError("truncated request body")
        return body

    @staticmethod
    def _filtered_headers(headers) -> dict[str, str]:
        blocked = set(HOP_BY_HOP)
        connection_tokens = headers.get("Connection", "")
        blocked.update(token.strip().lower() for token in connection_tokens.split(",") if token.strip())
        return {key: value for key, value in headers.items() if key.lower() not in blocked}

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _control(self) -> bool:
        path = urlsplit(self.path).path
        if path == f"{CONTROL_PREFIX}/counts" and self.command == "GET":
            self._json(200, self.server.counters.snapshot())
            return True
        if path == f"{CONTROL_PREFIX}/reset" and self.command == "POST":
            self.server.counters.reset()
            self._json(200, {"reset": True})
            return True
        return False

    def _forward(self) -> None:
        if self._control():
            return
        try:
            body = self._read_body()
        except (ValueError, OSError) as exc:
            self._json(400, {"error": "invalid_request_body", "message": str(exc)})
            return

        parsed = urlsplit(self.path)
        path = parsed.path if parsed.scheme else self.path
        if parsed.scheme and parsed.query:
            path += "?" + parsed.query
        path = self.server.upstream_prefix + (path if path.startswith("/") else "/" + path)
        headers = self._filtered_headers(self.headers)
        headers["Content-Length"] = str(len(body))
        connection = self.server.connection()
        response_body = b""
        try:
            time.sleep(self.server.delay_seconds)
            connection.request(self.command, path, body=body, headers=headers)
            response = connection.getresponse()
            response_body = response.read()
            response_headers = self._filtered_headers(response.headers)
            # A HEAD reply carries the object's length but no body, so its own
            # Content-Length must pass through; overwriting it with the empty
            # body's length makes a client see a zero-byte object.
            if self.command != "HEAD" and response.status not in (204, 304):
                response_headers["Content-Length"] = str(len(response_body))
            self.send_response(response.status, response.reason)
            for key, value in response_headers.items():
                self.send_header(key, value)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(response_body)
        except (OSError, http.client.HTTPException) as exc:
            response_body = json.dumps({"error": "upstream_unavailable", "message": str(exc)},
                                       sort_keys=True, separators=(",", ":")).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_body)))
            self.end_headers()
            self.wfile.write(response_body)
        finally:
            connection.close()
            self.server.counters.add(self.command, len(body), len(response_body))

    do_DELETE = _forward
    do_GET = _forward
    do_HEAD = _forward
    do_OPTIONS = _forward
    do_PATCH = _forward
    do_POST = _forward
    do_PUT = _forward


def _bind(value: str) -> tuple[str, int]:
    host, separator, port = value.rpartition(":")
    if not separator or not host or not port.isdecimal():
        raise argparse.ArgumentTypeError("bind must be HOST:PORT")
    return host, int(port)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="fixed-delay counting HTTP proxy")
    parser.add_argument("--bind", type=_bind, default=_bind(os.environ.get("WM_PROXY_BIND", "127.0.0.1:19010")))
    parser.add_argument("--upstream", default=os.environ.get("WM_PROXY_UPSTREAM", "http://127.0.0.1:19000"))
    parser.add_argument("--delay-ms", type=float, default=float(os.environ.get("WM_PROXY_DELAY_MS", "17")))
    args = parser.parse_args(argv)
    if args.delay_ms < 0:
        parser.error("delay must be non-negative")
    server = CountingProxy(args.bind, args.upstream, args.delay_ms)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
