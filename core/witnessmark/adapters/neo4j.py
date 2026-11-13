"""Neo4j over its HTTP transaction API, standard library only (master blueprint section 7.3).

Every statement runs in its own transaction through POST /db/<name>/tx/commit,
at Neo4j's default isolation (read committed). An error in the response body
means the transaction rolled back, so it is a definite refusal.
"""

from __future__ import annotations

import base64
import http.client
import json

from .. import env
from .base import Engine, EngineError, EngineUnavailable, Reply, Session


def _bookmark(data: dict) -> str | None:
    bookmarks = data.get("lastBookmarks") or []
    return bookmarks[0] if bookmarks else None


class Neo4jSession(Session):
    def __init__(self, host: str, port: int, database: str, authorization: str | None, timeout: float):
        self._host, self._port, self._timeout = host, port, timeout
        self._authorization = authorization
        self._path = f"/db/{database}/tx/commit"
        self._conn: http.client.HTTPConnection | None = None

    def _connection(self) -> http.client.HTTPConnection:
        if self._conn is None:
            self._conn = http.client.HTTPConnection(self._host, self._port, timeout=self._timeout)
        return self._conn

    def _drop(self) -> None:
        if self._conn is not None:
            self._conn.close()
        self._conn = None

    def run(self, query: str, params: dict | None = None, *, write: bool = True) -> Reply:
        body = json.dumps({"statements": [{"statement": query, "parameters": params or {}}]}).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json;charset=UTF-8"}
        if self._authorization:
            headers["Authorization"] = self._authorization
        try:
            conn = self._connection()
            conn.request("POST", self._path, body=body, headers=headers)
            response = conn.getresponse()
            payload = response.read()
        except TimeoutError as exc:
            self._drop()
            raise EngineUnavailable("timeout", str(exc) or "timed out") from exc
        except (http.client.HTTPException, OSError) as exc:
            self._drop()
            raise EngineUnavailable("connection", str(exc) or type(exc).__name__) from exc
        if response.status >= 500:
            raise EngineUnavailable("http", f"HTTP {response.status}")
        if response.status >= 400:
            raise EngineError("neo4j.http", f"HTTP {response.status}: {payload[:300]!r}")
        try:
            data = json.loads(payload)
        except ValueError as exc:
            raise EngineUnavailable("protocol", "the response is not JSON") from exc
        errors = data.get("errors") or []
        if errors:
            first = errors[0]
            code = first.get("code") or "neo4j.error"
            raise EngineError(code, first.get("message", ""), code)
        results = data.get("results") or []
        if not results:
            return Reply([], [], _bookmark(data))
        result = results[0]
        rows = [entry.get("row", []) for entry in result.get("data", [])]
        return Reply(list(result.get("columns", [])), rows, _bookmark(data))

    def ping(self) -> None:
        # A kept-alive connection may have been closed by the server between
        # trials. A ping is a read, so one retry on a fresh connection is safe.
        try:
            self.run("RETURN 1 AS one", {}, write=False)
        except EngineUnavailable:
            self.run("RETURN 1 AS one", {}, write=False)

    def close(self) -> None:
        self._drop()


class Neo4j(Engine):
    name = "neo4j"
    repo = "neo4j/neo4j"

    def __init__(self, host: str = "127.0.0.1", port: int = 17474, database: str = "neo4j",
                 container: str = "wm-neo4j", user: str | None = None, password: str | None = None):
        self.host, self.port, self.database, self.container = host, port, database, container
        self._authorization = None
        if user is not None:
            token = base64.b64encode(f"{user}:{password or ''}".encode("utf-8")).decode("ascii")
            self._authorization = "Basic " + token

    def session(self, timeout: float = 60.0) -> Neo4jSession:
        return Neo4jSession(self.host, self.port, self.database, self._authorization, timeout)

    def reset(self, session: Session) -> None:
        session.run("MATCH (n) DETACH DELETE n", {})

    def discovery(self, timeout: float = 5.0) -> dict:
        conn = http.client.HTTPConnection(self.host, self.port, timeout=timeout)
        try:
            conn.request("GET", "/", headers={"Accept": "application/json"})
            response = conn.getresponse()
            payload = response.read()
        finally:
            conn.close()
        if response.status != 200:
            raise EngineUnavailable("http", f"HTTP {response.status}")
        return json.loads(payload)

    def health(self) -> dict:
        try:
            found = self.discovery()
        except (OSError, http.client.HTTPException, ValueError, EngineUnavailable) as exc:
            return {"ok": False, "error": str(exc) or type(exc).__name__}
        return {"ok": True, "version": found.get("neo4j_version")}

    def describe(self) -> dict:
        found = self.discovery()
        record = {
            "role": "baseline",
            "name": "neo4j",
            "version": f"{found.get('neo4j_version', 'unknown')} {found.get('neo4j_edition', '')}".strip(),
            "config": {"api": "HTTP tx/commit", "isolation": "read committed (default)"},
        }
        image, image_digest = env.docker_image(self.container)
        if image:
            record["image"] = image
        if image_digest:
            record["digest"] = image_digest
        return record
