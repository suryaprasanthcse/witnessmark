"""FalkorDB over RESP, standard library only (master blueprint section 7.2).

Queries go through GRAPH.QUERY (writes) or GRAPH.RO_QUERY (reads) in the
verbose reply format. Parameters travel in FalkorDB's ``CYPHER name=value``
prefix, encoded as Cypher literals.
"""

from __future__ import annotations

import math
import re

from .. import env
from .base import Engine, EngineError, EngineUnavailable, Reply, Session
from .resp import RespConnection, RespError, RespErrorReply

_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def cypher_literal(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError("NaN and infinity have no Cypher literal")
        return repr(value)
    if isinstance(value, str):
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(cypher_literal(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{_map_key(key)}: {cypher_literal(item)}" for key, item in value.items()) + "}"
    raise TypeError(f"no Cypher literal for {type(value).__name__}")


def _map_key(key) -> str:
    key = str(key)
    if _IDENTIFIER.match(key):
        return key
    return "`" + key.replace("`", "``") + "`"


def with_params(query: str, params: dict | None) -> str:
    if not params:
        return query
    assignments = []
    for name, value in params.items():
        if not _IDENTIFIER.match(name):
            raise ValueError(f"parameter name {name!r} is not an identifier")
        assignments.append(f"{name}={cypher_literal(value)}")
    return "CYPHER " + " ".join(assignments) + " " + query


def _first_error(value):
    if isinstance(value, RespErrorReply):
        return value
    if isinstance(value, list):
        for item in value:
            found = _first_error(item)
            if found is not None:
                return found
    return None


def parse_query_reply(reply) -> Reply:
    """Verbose replies are [header, rows, statistics], or [statistics] when nothing is returned."""
    nested = _first_error(reply)
    if nested is not None:
        raise EngineError("falkordb.error", nested.message)
    if not isinstance(reply, list) or len(reply) not in (1, 3):
        raise EngineError("falkordb.protocol", f"unexpected reply shape: {reply!r}"[:300])
    if len(reply) == 1:
        header, rows, statistics = [], [], reply[0]
    else:
        header, rows, statistics = reply
    columns = [entry[1] if isinstance(entry, list) else entry for entry in header or []]
    stats = {}
    for line in statistics or []:
        if isinstance(line, str) and ":" in line:
            key, value = line.split(":", 1)
            stats[key.strip()] = value.strip()
    return Reply(columns, [list(row) for row in rows or []], None, stats)


def module_version(modules) -> int | None:
    for entry in modules or []:
        if isinstance(entry, list):
            fields = dict(zip(entry[0::2], entry[1::2]))
            if str(fields.get("name", "")).lower() in ("graph", "falkordb"):
                try:
                    return int(fields.get("ver"))
                except (TypeError, ValueError):
                    return None
    return None


def version_string(ver: int) -> str:
    return f"{ver // 10000}.{(ver // 100) % 100}.{ver % 100}"


class FalkorSession(Session):
    def __init__(self, host: str, port: int, graph: str, timeout: float):
        self._host, self._port, self._graph, self._timeout = host, port, graph, timeout
        self._conn: RespConnection | None = None
        self._connect()

    def _connect(self) -> None:
        try:
            self._conn = RespConnection(self._host, self._port, self._timeout)
        except OSError as exc:
            raise EngineUnavailable("connection", f"cannot reach FalkorDB at {self._host}:{self._port}: {exc}") from exc

    def _drop(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except OSError:
                pass
        self._conn = None

    def call(self, *args):
        if self._conn is None:
            self._connect()
        try:
            return self._conn.call(*args)
        except RespError as exc:
            raise EngineError("falkordb.error", str(exc)) from exc
        except TimeoutError as exc:
            self._drop()
            raise EngineUnavailable("timeout", str(exc) or "timed out") from exc
        except OSError as exc:
            self._drop()
            raise EngineUnavailable("connection", str(exc) or type(exc).__name__) from exc

    def run(self, query: str, params: dict | None = None, *, write: bool = True) -> Reply:
        command = "GRAPH.QUERY" if write else "GRAPH.RO_QUERY"
        return parse_query_reply(self.call(command, self._graph, with_params(query, params)))

    def ping(self) -> None:
        if self.call("PING") != "PONG":
            raise EngineUnavailable("protocol", "PING did not answer PONG")

    def close(self) -> None:
        self._drop()


class FalkorDB(Engine):
    name = "falkordb"
    repo = "FalkorDB/FalkorDB"

    def __init__(self, host: str = "127.0.0.1", port: int = 16380, graph: str = "witnessmark",
                 container: str = "wm-falkordb"):
        self.host, self.port, self.graph, self.container = host, port, graph, container

    def session(self, timeout: float = 60.0) -> FalkorSession:
        return FalkorSession(self.host, self.port, self.graph, timeout)

    def reset(self, session: Session) -> None:
        try:
            session.call("GRAPH.DELETE", self.graph)
        except EngineError as exc:
            if "empty key" not in exc.message.lower():
                raise

    def health(self) -> dict:
        try:
            session = self.session(timeout=5.0)
            try:
                session.ping()
            finally:
                session.close()
        except (EngineError, EngineUnavailable) as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True}

    def describe(self) -> dict:
        session = self.session(timeout=10.0)
        try:
            ver = module_version(session.call("MODULE", "LIST"))
            config = {}
            for key in ("appendonly", "appendfsync", "save"):
                try:
                    pair = session.call("CONFIG", "GET", key)
                    config[key] = pair[1] if isinstance(pair, list) and len(pair) > 1 else None
                except EngineError:
                    config[key] = None
        finally:
            session.close()
        record = {
            "role": "baseline",
            "name": "falkordb",
            "version": f"{version_string(ver)} (graph module {ver})" if ver else "unknown",
            "config": config,
        }
        image, image_digest = env.docker_image(self.container)
        if image:
            record["image"] = image
        if image_digest:
            record["digest"] = image_digest
        return record
