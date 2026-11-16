"""Omnigraph HTTP API 0.14 client, using only the Python standard library.

The wire contract comes from ``docs/user/operations/server.md`` and
``openapi.json`` at the two M4 pins. Calls are attempted once. A typed refusal
is definite and is never retried here; timeouts, lost connections and responses
whose disposition permits effects are unknown outcomes for the caller to
reconcile.
"""

from __future__ import annotations

import http.client
import errno
import json
import re
import socket
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any
from urllib.parse import quote, urlencode, urlsplit

from witnessmark.timing import stamp


class Outcome(str, Enum):
    """The three operation outcomes from master blueprint section 5.0."""

    OK = "ok"
    REFUSAL = "refusal"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class OperationResult:
    """One HTTP operation classified without throwing transport exceptions."""

    outcome: Outcome
    status: int | None = None
    kind: str | None = None
    data: Any = None
    message: str | None = None

    @property
    def ok(self) -> bool:
        return self.outcome is Outcome.OK

    @property
    def refused(self) -> bool:
        return self.outcome is Outcome.REFUSAL

    @property
    def unknown(self) -> bool:
        return self.outcome is Outcome.UNKNOWN


_TYPED_NAME = re.compile(
    r"\b(CardinalityViolation|DivergentInsert|DivergentUpdate|DeleteVsUpdate|"
    r"OrphanEdge|UniqueViolation|ValueConstraintViolation|WriterFenced)\b"
)
# server.md (v0.15.0 and b2dbaff), "Errors and retries": "Admission limits use 429 ... with Retry-After".
# A request refused at admission never ran, so the refusal is definite.
ADMISSION_LIMIT = "admission_limit"
_DEFINITE_REFUSALS = {
    ADMISSION_LIMIT, "precondition_failure", "CardinalityViolation", "DivergentInsert", "DivergentUpdate",
    "DeleteVsUpdate", "OrphanEdge", "UniqueViolation", "ValueConstraintViolation", "WriterFenced",
}
_CONFLICT_NAMES = {
    "cardinality_violation": "CardinalityViolation",
    "divergent_insert": "DivergentInsert",
    "divergent_update": "DivergentUpdate",
    "delete_vs_update": "DeleteVsUpdate",
    "orphan_edge": "OrphanEdge",
    "unique_violation": "UniqueViolation",
    "value_constraint_violation": "ValueConstraintViolation",
}


def _conflict_kinds(payload: Any) -> list[str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("merge_conflicts"), list):
        return []
    return [_CONFLICT_NAMES.get(str(conflict["kind"]), str(conflict["kind"]))
            for conflict in payload["merge_conflicts"]
            if isinstance(conflict, dict) and conflict.get("kind")]


def _error_kind(payload: Any, status: int) -> str:
    if status == 429:
        return ADMISSION_LIMIT
    if not isinstance(payload, dict):
        return f"http_{status}"
    if payload.get("precondition_failure") is not None:
        return "precondition_failure"
    if payload.get("writer_fenced") is not None:
        return "WriterFenced"
    error = str(payload.get("error", ""))
    if "@card violation" in error:
        return "CardinalityViolation"
    conflicts = _conflict_kinds(payload)
    if conflicts:
        return conflicts[0]
    match = _TYPED_NAME.search(str(payload.get("error", "")))
    if match:
        return match.group(1)
    return str(payload.get("code") or f"http_{status}")


KEPT_CONNECTION_DROPPED = "kept_connection_dropped"


class _KeptConnectionDropped(Exception):
    """A read on a reused kept connection that the server closed before replying (keep_alive only)."""


def _message(payload: Any, fallback: str) -> str:
    if isinstance(payload, dict):
        value = payload.get("error") or payload.get("message")
        if value:
            return str(value)
    return fallback


class OmnigraphClient:
    """A single-request client for one graph on an ``omnigraph-server``."""

    def __init__(
        self,
        endpoint: str = "http://127.0.0.1:8080",
        graph: str = "witnessmark",
        *,
        bearer_token: str | None = None,
        timeout: float = 60.0,
        observed=None,
        keep_alive: bool = False,
    ):
        parsed = urlsplit(endpoint)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ValueError("endpoint must be an http(s) service-root URL")
        if parsed.query or parsed.fragment or parsed.username or parsed.password:
            raise ValueError("endpoint must not contain credentials, a query or a fragment")
        self._scheme = parsed.scheme
        self._host = parsed.hostname
        self._port = parsed.port or (443 if parsed.scheme == "https" else 80)
        self._prefix = parsed.path.rstrip("/")
        self.graph = graph
        self.bearer_token = bearer_token
        self.timeout = timeout
        self._observed = observed
        # keep_alive reuses one HTTP/1.1 connection for this client's requests. A closed-loop load that opens a
        # connection per request leaves a socket in TIME_WAIT per request and can exhaust the Windows host's
        # ephemeral ports (WinError 10048, batch m5b-20261115T230235Z, O1 on v0.15.0 local). One client per
        # thread: the connection is not shared.
        self.keep_alive = keep_alive
        self._kept: http.client.HTTPConnection | None = None
        self.dropped_reads: list[int] = []  # perf_counter_ns of each read retried after a dropped kept connection
        # (inv, ret, message) of each dropped read attempt, for callers that write their own history (O2b).
        self.dropped_attempts: list[tuple] = []

    def _connection(self) -> http.client.HTTPConnection:
        cls = http.client.HTTPSConnection if self._scheme == "https" else http.client.HTTPConnection
        return cls(self._host, self._port, timeout=self.timeout)

    def _graph_path(self, suffix: str) -> str:
        return f"{self._prefix}/graphs/{quote(self.graph, safe='')}{suffix}"

    def _request(self, method: str, path: str, body: dict | bytes | None = None, *, protected: bool = True,
                 extra_headers: dict[str, str] | None = None,
                 content_type: str = "application/json") -> OperationResult:
        inv = stamp()
        options = {"protected": protected, "extra_headers": extra_headers, "content_type": content_type}
        try:
            result = self._send(method, path, body, **options)
        except _KeptConnectionDropped as exc:
            # A read whose kept connection the server closed before any reply. The dropped attempt is its own
            # record (outcome unknown: no reply arrived), its time is kept for the O1 stall metrics, and the
            # read is sent once more on a fresh connection as a separate record. Nothing is hidden.
            self.dropped_reads.append(time.perf_counter_ns())
            dropped_message = (f"the server closed the kept connection before replying ({exc}); "
                               "the read is sent again on a fresh connection")
            self.dropped_attempts.append((inv, stamp(), dropped_message))
            if self._observed is not None:
                self._observed(method, path, body, inv, stamp(), OperationResult(
                    Outcome.UNKNOWN, kind=KEPT_CONNECTION_DROPPED,
                    message=f"the server closed the kept connection before replying ({exc}); "
                            "the read is sent again on a fresh connection"))
                inv = stamp()
            result = self._send(method, path, body, **options)
        if self._observed is not None:
            self._observed(method, path, body, inv, stamp(), result)
        return result

    def _send(self, method: str, path: str, body: dict | bytes | None, *, protected: bool,
              extra_headers: dict[str, str] | None, content_type: str) -> OperationResult:
        headers = {"Accept": "application/json", **(extra_headers or {})}
        if protected:
            headers["Omnigraph-Http-Api"] = "0.14"
            if self.bearer_token is not None:
                headers["Authorization"] = f"Bearer {self.bearer_token}"
        encoded = None
        if body is not None:
            encoded = body if isinstance(body, bytes) else json.dumps(body, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = content_type

        reused = self.keep_alive and self._kept is not None
        connection = self._kept if reused else self._connection()
        try:
            try:
                connection.request(method, path, body=encoded, headers=headers)
                response = connection.getresponse()
            except (http.client.RemoteDisconnected, ConnectionResetError, BrokenPipeError) as exc:
                # The server closed a kept connection before answering. A read is sent again by _request, on a
                # fresh connection and as a separate record; a write's outcome stays unknown, as without
                # keep-alive.
                if reused and ((method == "POST" and path.endswith("/query")) or method == "GET"):
                    raise _KeptConnectionDropped(str(exc) or type(exc).__name__) from exc
                raise
            raw = response.read()
            status = response.status
            if self.keep_alive and not response.will_close:
                self._kept, connection = connection, None
        except (TimeoutError, socket.timeout) as exc:
            return OperationResult(Outcome.UNKNOWN, kind="timeout", message=str(exc) or "timed out")
        except OSError as exc:
            # Windows reports WSAECONNREFUSED as a plain OSError. In either
            # form the TCP handshake failed before an HTTP request was sent.
            if isinstance(exc, ConnectionRefusedError) or exc.errno in (errno.ECONNREFUSED, 10061) \
                    or getattr(exc, "winerror", None) == 10061:
                return OperationResult(Outcome.REFUSAL, kind="unavailable",
                                       message=str(exc) or "connection refused")
            return OperationResult(Outcome.UNKNOWN, kind="connection", message=str(exc) or type(exc).__name__)
        except http.client.HTTPException as exc:
            return OperationResult(
                Outcome.UNKNOWN,
                kind="connection",
                message=str(exc) or type(exc).__name__,
            )
        finally:
            if connection is not None:
                connection.close()
                if connection is self._kept:
                    self._kept = None

        payload: Any = None
        if raw:
            try:
                payload = json.loads(raw)
            except (UnicodeDecodeError, ValueError):
                text = raw.decode("utf-8", errors="replace")[:300]
                if status < 300:
                    return OperationResult(
                        Outcome.UNKNOWN,
                        status,
                        "protocol",
                        message="successful response was not JSON",
                    )
                payload = {"error": text}

        if 200 <= status < 300:
            return OperationResult(Outcome.OK, status=status, data=payload)

        fallback = f"HTTP {status}"
        disposition = payload.get("disposition") if isinstance(payload, dict) else None
        effects = disposition.get("effects") if isinstance(disposition, dict) else None
        kinds = _conflict_kinds(payload)
        if kinds:
            payload = dict(payload)
            payload["conflict_kinds"] = kinds
        kind = _error_kind(payload, status)
        message = _message(payload, fallback)
        if kind in _DEFINITE_REFUSALS:
            return OperationResult(Outcome.REFUSAL, status, kind, payload, message)
        if status >= 500 or effects in ("partial", "unknown") or kind == "outcome_unknown":
            return OperationResult(Outcome.UNKNOWN, status, kind, payload, message)
        return OperationResult(Outcome.REFUSAL, status, kind, payload, message)

    def query(
        self,
        query: str,
        params: dict | None = None,
        *,
        name: str | None = None,
        branch: str | None = None,
        snapshot: str | None = None,
        settings: dict | None = None,
    ) -> OperationResult:
        body: dict[str, Any] = {"query": query}
        for key, value in (("params", params), ("name", name), ("branch", branch),
                           ("snapshot", snapshot), ("settings", settings)):
            if value is not None:
                body[key] = value
        return self._request("POST", self._graph_path("/query"), body)

    def mutate(
        self,
        query: str,
        params: dict | None = None,
        *,
        name: str | None = None,
        branch: str | None = None,
        settings: dict | None = None,
        commit_id: str | None = None,
    ) -> OperationResult:
        body: dict[str, Any] = {"query": query}
        for key, value in (("params", params), ("name", name), ("branch", branch), ("settings", settings)):
            if value is not None:
                body[key] = value
        suffix = "/mutate/if-graph-commit" if commit_id is not None else "/mutate"
        if commit_id is None:
            return self._request("POST", self._graph_path(suffix), body)
        return self._request_with_commit("POST", self._graph_path(suffix), body, commit_id)

    def load_ndjson(self, payload: bytes, *, branch: str = "main", mode: str = "append") -> OperationResult:
        """Send one strict graph-batch payload to the bounded raw load route."""
        query = urlencode({"branch": branch, "mode": mode})
        return self._request("POST", self._graph_path(f"/load/ndjson?{query}"), payload,
                             content_type="application/x-ndjson")

    def _request_with_commit(self, method: str, path: str, body: dict, commit_id: str) -> OperationResult:
        """Send the dedicated conditional route with its required raw header."""
        return self._request(method, path, body,
                             extra_headers={"Omnigraph-If-Graph-Commit": commit_id})

    def branch_create(
        self,
        name: str,
        *,
        from_branch: str | None = None,
        from_commit: str | None = None,
    ) -> OperationResult:
        if from_branch is not None and from_commit is not None:
            raise ValueError("from_branch and from_commit are mutually exclusive")
        body = {"name": name}
        if from_branch is not None:
            body["from"] = from_branch
        if from_commit is not None:
            body["from_commit"] = from_commit
        return self._request("POST", self._graph_path("/branches"), body)

    def branch_delete(self, name: str) -> OperationResult:
        return self._request("DELETE", self._graph_path(f"/branches/{quote(name, safe='')}"))

    def branch_list(self, *, detailed: bool = False) -> OperationResult:
        suffix = "/branches"
        if detailed:
            suffix += "?" + urlencode({"detailed": "true"})
        return self._request("GET", self._graph_path(suffix))

    def merge(
        self,
        source: str,
        *,
        target: str | None = None,
        delete_branch: bool = False,
        dry_run: bool = False,
        as_commit: bool = False,
        settings: dict | None = None,
    ) -> OperationResult:
        body: dict[str, Any] = {"source": source}
        for key, value in (("target", target), ("settings", settings)):
            if value is not None:
                body[key] = value
        if delete_branch:
            body["delete_branch"] = True
        if dry_run:
            body["dry_run"] = True
        if as_commit:
            body["as_commit"] = True
        return self._request("POST", self._graph_path("/branches/merge"), body)

    def health(self) -> OperationResult:
        return self._request("GET", f"{self._prefix}/healthz", protected=False)
