"""Omnigraph HTTP API 0.14 client, using only the Python standard library.

The wire contract comes from ``docs/user/operations/server.md`` and
``openapi.json`` at the two M4 pins. Calls are attempted once. A typed refusal
is definite and is never retried here; timeouts, lost connections and responses
whose disposition permits effects are unknown outcomes for the caller to
reconcile.
"""

from __future__ import annotations

import http.client
import json
import re
import socket
from dataclasses import dataclass
from enum import Enum
from typing import Any
from urllib.parse import quote, urlencode, urlsplit


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


def _error_kind(payload: Any, status: int) -> str:
    if not isinstance(payload, dict):
        return f"http_{status}"
    if payload.get("precondition_failure") is not None:
        return "precondition_failure"
    if payload.get("writer_fenced") is not None:
        return "WriterFenced"
    conflicts = payload.get("merge_conflicts")
    if isinstance(conflicts, list):
        for conflict in conflicts:
            if isinstance(conflict, dict) and conflict.get("kind"):
                return str(conflict["kind"])
    match = _TYPED_NAME.search(str(payload.get("error", "")))
    if match:
        return match.group(1)
    return str(payload.get("code") or f"http_{status}")


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

    def _connection(self) -> http.client.HTTPConnection:
        cls = http.client.HTTPSConnection if self._scheme == "https" else http.client.HTTPConnection
        return cls(self._host, self._port, timeout=self.timeout)

    def _graph_path(self, suffix: str) -> str:
        return f"{self._prefix}/graphs/{quote(self.graph, safe='')}{suffix}"

    def _request(self, method: str, path: str, body: dict | None = None, *, protected: bool = True) -> OperationResult:
        headers = {"Accept": "application/json"}
        if protected:
            headers["Omnigraph-Http-Api"] = "0.14"
            if self.bearer_token is not None:
                headers["Authorization"] = f"Bearer {self.bearer_token}"
        encoded = None
        if body is not None:
            encoded = json.dumps(body, separators=(",", ":")).encode("utf-8")
            headers["Content-Type"] = "application/json"

        connection = self._connection()
        try:
            connection.request(method, path, body=encoded, headers=headers)
            response = connection.getresponse()
            raw = response.read()
            status = response.status
        except (TimeoutError, socket.timeout) as exc:
            return OperationResult(Outcome.UNKNOWN, kind="timeout", message=str(exc) or "timed out")
        except (http.client.HTTPException, OSError) as exc:
            return OperationResult(
                Outcome.UNKNOWN,
                kind="connection",
                message=str(exc) or type(exc).__name__,
            )
        finally:
            connection.close()

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
        kind = _error_kind(payload, status)
        message = _message(payload, fallback)
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

    def _request_with_commit(self, method: str, path: str, body: dict, commit_id: str) -> OperationResult:
        """Send the dedicated conditional route with its required raw header."""
        headers = {"Accept": "application/json", "Content-Type": "application/json",
                   "Omnigraph-Http-Api": "0.14", "Omnigraph-If-Graph-Commit": commit_id}
        if self.bearer_token is not None:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        encoded = json.dumps(body, separators=(",", ":")).encode("utf-8")
        return self._request_encoded(method, path, encoded, headers)

    def _request_encoded(self, method: str, path: str, encoded: bytes, headers: dict[str, str]) -> OperationResult:
        """The request classifier shared by the conditional-header path."""
        connection = self._connection()
        try:
            connection.request(method, path, body=encoded, headers=headers)
            response = connection.getresponse()
            raw = response.read()
            status = response.status
        except (TimeoutError, socket.timeout) as exc:
            return OperationResult(Outcome.UNKNOWN, kind="timeout", message=str(exc) or "timed out")
        except (http.client.HTTPException, OSError) as exc:
            return OperationResult(Outcome.UNKNOWN, kind="connection", message=str(exc) or type(exc).__name__)
        finally:
            connection.close()
        try:
            payload = json.loads(raw) if raw else None
        except (UnicodeDecodeError, ValueError):
            payload = {"error": raw.decode("utf-8", errors="replace")[:300]}
            if status < 300:
                return OperationResult(Outcome.UNKNOWN, status, "protocol", message="successful response was not JSON")
        if 200 <= status < 300:
            return OperationResult(Outcome.OK, status=status, data=payload)
        disposition = payload.get("disposition") if isinstance(payload, dict) else None
        effects = disposition.get("effects") if isinstance(disposition, dict) else None
        kind = _error_kind(payload, status)
        message = _message(payload, f"HTTP {status}")
        if status >= 500 or effects in ("partial", "unknown") or kind == "outcome_unknown":
            return OperationResult(Outcome.UNKNOWN, status, kind, payload, message)
        return OperationResult(Outcome.REFUSAL, status, kind, payload, message)

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
