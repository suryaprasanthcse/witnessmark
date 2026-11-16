"""Instruments for G6-G8 (target blueprint section 5). They watch Graphiti and its engines; they change nothing
Graphiti does.

- BuildTracker wraps build_indices_and_constraints on both drivers: it awaits the original and records the
  database, start, end and outcome of every call, including the background builds the constructors start (K9, K23).
- LoopWatch is the event loop's exception handler (it catches "Task exception was never retrieved") and a logging
  handler for records at WARNING or above.
- FalkorProbe and Neo4jProbe read index state, the raw fulltext probe and the group's data on the harness's own
  connection, through the engines' own client packages.
- IndexMonitor samples a probe in a loop until it is stopped.
"""

from __future__ import annotations

import asyncio
import gc
import logging

from graphiti_core.driver.falkordb_driver import FalkorDriver
from graphiti_core.driver.neo4j_driver import Neo4jDriver

from witnessmark.evidence import digest, redact
from witnessmark.history import FAIL, OK, UNKNOWN, Op
from witnessmark.timing import stamp

from .measure import compress, index_summary

NEVER_RETRIEVED = "Task exception was never retrieved"


def _error(exc: BaseException, limit: int = 300) -> dict:
    return {"type": type(exc).__name__, "message": redact(str(exc))[:limit]}


# --- index builds ---------------------------------------------------------------------------------------------


class BuildTracker:
    def __init__(self) -> None:
        self.events: list[dict] = []
        self._originals: dict[type, object] = {}

    def install(self) -> None:
        for cls in (FalkorDriver, Neo4jDriver):
            if cls in self._originals:
                continue
            original = cls.__dict__["build_indices_and_constraints"]
            self._originals[cls] = original
            cls.build_indices_and_constraints = self._wrap(original, cls.__name__)

    def uninstall(self) -> None:
        for cls, original in self._originals.items():
            cls.build_indices_and_constraints = original
        self._originals.clear()

    def _wrap(self, original, driver_name: str):
        tracker = self

        async def build_indices_and_constraints(self, delete_existing=False):
            event = {"driver": driver_name, "database": getattr(self, "_database", None), "inv": stamp(),
                     "ret": None, "outcome": "running", "error": None}
            tracker.events.append(event)
            try:
                result = await original(self, delete_existing)
            except asyncio.CancelledError:
                event.update(ret=stamp(), outcome="cancelled")
                raise
            except BaseException as exc:
                event.update(ret=stamp(), outcome="error", error=_error(exc))
                raise
            event.update(ret=stamp(), outcome="ok")
            return result

        return build_indices_and_constraints

    def drain(self) -> list[dict]:
        events, self.events = self.events, []
        return events


def build_measures(events: list[dict]) -> list[dict]:
    """Build events as plain numbers for measure.uc_report."""
    return [{"database": e["database"], "outcome": e["outcome"], "inv_ns": e["inv"].mono_ns,
             "ret_ns": e["ret"].mono_ns if e["ret"] is not None else None} for e in events]


def build_ops(events: list[dict], run_id: str, k: int, phase: str = "race", start: int = 0, **extra) -> list[Op]:
    ops = []
    for n, event in enumerate(events, start):
        record = {"database": event["database"], "driver": event["driver"], **extra}
        if event["outcome"] == "ok":
            ops.append(Op(run_id, k, phase, f"{k}-build-{n:04d}", "init-task", "index_build", record, event["inv"],
                          event["ret"], OK, {"outcome": "ok"}))
        else:
            error = event["error"] or {"type": event["outcome"], "message": f"the build ended {event['outcome']}"}
            ended = event["ret"].wall if event["ret"] is not None else None
            ops.append(Op(run_id, k, phase, f"{k}-build-{n:04d}", "init-task", "index_build", record, event["inv"],
                          None, UNKNOWN, {"outcome": event["outcome"], "ended": ended},
                          {"type": f"target.{error['type']}", "message": error["message"]}))
    return ops


# --- the event loop and logs ----------------------------------------------------------------------------------


class LoopWatch(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.loop_events: list[dict] = []
        self.log_records: list[dict] = []
        self._loop = None

    def install(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        loop.set_exception_handler(self._on_loop)
        logging.getLogger().addHandler(self)

    def uninstall(self) -> None:
        if self._loop is not None:
            self._loop.set_exception_handler(None)
        logging.getLogger().removeHandler(self)

    def _on_loop(self, loop, context: dict) -> None:
        exc = context.get("exception")
        self.loop_events.append({"at": stamp(), "message": str(context.get("message"))[:200],
                                 "exception": _error(exc) if exc is not None else None})

    def emit(self, record: logging.LogRecord) -> None:
        if record.name.startswith("witnessmark"):
            return
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001 - a malformed record is still a record
            message = str(record.msg)
        self.log_records.append({"at": stamp(), "logger": record.name, "level": record.levelname,
                                 "message": redact(message)[:300]})

    async def settle(self) -> None:
        """Collect garbage so a finished task nobody awaited reports its exception now, not later."""
        for _ in range(3):
            gc.collect()
            await asyncio.sleep(0)

    def drain(self) -> tuple[list[dict], list[dict]]:
        loop_events, self.loop_events = self.loop_events, []
        logs, self.log_records = self.log_records, []
        return loop_events, logs


def watch_ops(loop_events: list[dict], logs: list[dict], run_id: str, k: int) -> list[Op]:
    ops = []
    for n, event in enumerate(loop_events):
        kind = "unretrieved_exception" if event["message"].startswith(NEVER_RETRIEVED) else "loop_error"
        ops.append(Op(run_id, k, "observe", f"{k}-loop-{n:04d}", "loop", kind, {"message": event["message"]},
                      event["at"], event["at"], OK, {"exception": event["exception"]}))
    for n, record in enumerate(logs):
        ops.append(Op(run_id, k, "observe", f"{k}-log-{n:04d}", "log", "log_record",
                      {"logger": record["logger"], "level": record["level"]}, record["at"], record["at"], OK,
                      {"message": record["message"]}))
    return ops


def watch_summary(loop_events: list[dict], logs: list[dict]) -> dict:
    unretrieved = [e for e in loop_events if e["message"].startswith(NEVER_RETRIEVED)]
    return {"unretrieved": len(unretrieved),
            "unretrieved_types": sorted({(e["exception"] or {}).get("type", "?") for e in unretrieved}),
            "loop_errors": len(loop_events) - len(unretrieved),
            "log_errors": sum(1 for r in logs if r["level"] in ("ERROR", "CRITICAL")),
            "log_warnings": sum(1 for r in logs if r["level"] == "WARNING")}


# --- engine probes --------------------------------------------------------------------------------------------


class FalkorProbe:
    backend = "falkordb"

    def __init__(self, host: str, port: int):
        from redis.asyncio import BlockingConnectionPool

        self.pool = BlockingConnectionPool(host=host, port=port, max_connections=4, timeout=30, decode_responses=True)
        self._db = None

    @property
    def db(self):
        # The client connects when it is constructed, so it is built on first use: a probe may exist before its
        # server does (G7 starts a new container in every trial).
        if self._db is None:
            from falkordb.asyncio import FalkorDB

            self._db = FalkorDB(connection_pool=self.pool)
        return self._db

    async def ping(self) -> bool:
        return bool(await self.db.connection.ping())

    async def _ro(self, graph: str, query: str, params: dict | None = None):
        return await self.db.select_graph(graph).ro_query(query, params)

    async def exists(self, graph: str) -> bool:
        return graph in await self.db.list_graphs()

    async def index_rows(self, graph: str) -> list[dict]:
        result = await self._ro(graph, "CALL db.indexes() YIELD label, types, entitytype, status "
                                       "RETURN label, types, entitytype, status")
        return [{"label": row[0], "types": {k: list(v) for k, v in dict(row[1]).items()}, "entitytype": row[2],
                 "status": row[3]} for row in result.result_set]

    async def probe(self, graph: str, group: str, term: str) -> int:
        result = await self._ro(graph, "CALL db.idx.fulltext.queryRelationships('RELATES_TO', $term) "
                                       "YIELD relationship WHERE relationship.group_id = $group "
                                       "RETURN count(relationship)", {"term": term, "group": group})
        return int(result.result_set[0][0])

    async def drop_indexes(self, graph: str) -> int:
        """Drop every index on the graph, one field at a time, as Graphiti's delete_all_indexes does."""
        dropped = 0
        for row in await self.index_rows(graph):
            pattern = f"(n:{row['label']})" if row["entitytype"] == "NODE" else f"()-[n:{row['label']}]-()"
            for field, kinds in row["types"].items():
                for kind in kinds:
                    keyword = "FULLTEXT INDEX" if kind == "FULLTEXT" else "INDEX"
                    await self.db.select_graph(graph).query(f"DROP {keyword} FOR {pattern} ON (n.{field})")
                    dropped += 1
        return dropped

    async def items(self, graph: str, group: str) -> dict:
        if not await self.exists(graph):
            return {"graph": False, "facts": [], "entities": [], "episodes": []}
        facts = await self._ro(graph, "MATCH ()-[e:RELATES_TO]->() RETURN e.fact ORDER BY e.fact")
        entities = await self._ro(graph, "MATCH (n:Entity) RETURN n.name ORDER BY n.name")
        episodes = await self._ro(graph, "MATCH (n:Episodic) RETURN n.name ORDER BY n.name")
        return {"graph": True, "facts": [r[0] for r in facts.result_set],
                "entities": [r[0] for r in entities.result_set], "episodes": [r[0] for r in episodes.result_set]}

    async def settings(self) -> dict:
        config = {}
        for name in ("appendonly", "appendfsync", "save", "dir"):
            reply = await self.db.connection.config_get(name)
            config[name] = reply.get(name)
        modules = await self.db.connection.execute_command("MODULE", "LIST")
        graph = next((m for m in modules if (m.get("name") if isinstance(m, dict) else None) == "graph"), None)
        config["graph_module"] = {"ver": graph.get("ver"), "args": list(graph.get("args") or [])} if graph else None
        return config

    async def save(self) -> bool:
        return bool(await self.db.connection.save())

    async def close(self) -> None:
        await self.pool.disconnect()


class Neo4jProbe:
    backend = "neo4j"

    def __init__(self, host: str, bolt_port: int):
        from neo4j import AsyncGraphDatabase

        self.driver = AsyncGraphDatabase.driver(f"bolt://{host}:{bolt_port}", auth=("neo4j", "witnessmark"))

    async def _run(self, query: str, **params) -> list[dict]:
        async with self.driver.session() as session:
            result = await session.run(query, params)
            return await result.data()

    async def ping(self) -> bool:
        return (await self._run("RETURN 1 AS ok"))[0]["ok"] == 1

    async def exists(self, graph) -> bool:
        return True

    async def index_rows(self, graph=None) -> list[dict]:
        return await self._run("SHOW INDEXES YIELD name, type, entityType, labelsOrTypes, properties, state "
                               "WHERE type <> 'LOOKUP' RETURN name, type, entityType, labelsOrTypes, properties, state")

    async def probe(self, graph, group: str, term: str) -> int:
        rows = await self._run("CALL db.index.fulltext.queryRelationships('edge_name_and_fact', $term) "
                               "YIELD relationship WHERE relationship.group_id = $group "
                               "RETURN count(relationship) AS n", term=term, group=group)
        return int(rows[0]["n"])

    async def drop_indexes(self, graph=None) -> int:
        rows = await self.index_rows()
        for row in rows:
            await self._run(f"DROP INDEX `{row['name']}` IF EXISTS")
        return len(rows)

    async def items(self, graph, group: str) -> dict:
        facts = await self._run("MATCH ()-[e:RELATES_TO {group_id: $g}]->() RETURN e.fact AS v ORDER BY v", g=group)
        entities = await self._run("MATCH (n:Entity {group_id: $g}) RETURN n.name AS v ORDER BY v", g=group)
        episodes = await self._run("MATCH (n:Episodic {group_id: $g}) RETURN n.name AS v ORDER BY v", g=group)
        return {"graph": True, "facts": [r["v"] for r in facts], "entities": [r["v"] for r in entities],
                "episodes": [r["v"] for r in episodes]}

    async def settings(self) -> dict:
        return {}

    async def save(self) -> bool:
        return True

    async def close(self) -> None:
        await self.driver.close()


def make_probe(target) -> FalkorProbe | Neo4jProbe:
    if target.backend == "falkordb":
        return FalkorProbe(target.host, target.falkordb_port)
    return Neo4jProbe(target.host, target.neo4j_bolt_port)


def items_digest(items: dict) -> str:
    return digest(items)


async def wait_answers(probe, run_id: str, k: int, timeout_s: float, op_id: str) -> Op:
    """Poll until the server answers (FalkorDB PING, Neo4j RETURN 1); one observe record from first try to answer."""
    inv = stamp()
    attempts, last = 0, None
    deadline = inv.mono_ns + int(timeout_s * 1e9)
    while True:
        attempts += 1
        try:
            if await probe.ping():
                return Op(run_id, k, "observe", op_id, "harness", "ping", {"attempts_until": "answer"}, inv, stamp(),
                          OK, {"attempts": attempts})
        except Exception as exc:  # noqa: BLE001 - not answering yet is what we wait through
            last = _error(exc)
        if stamp().mono_ns > deadline:
            return Op(run_id, k, "observe", op_id, "harness", "ping", {"attempts_until": "answer"}, inv, stamp(),
                      FAIL, {"attempts": attempts}, {"type": "unavailable.timeout",
                                                     "message": f"no answer in {timeout_s} s; last: {last}"})
        await asyncio.sleep(0.01)


# --- the index monitor ----------------------------------------------------------------------------------------


class IndexMonitor:
    """Samples index state (and, if given a term, the raw fulltext probe) for each watched graph."""

    def __init__(self, probe, watched: list[tuple], interval_s: float = 0.002):
        # watched: (graph, group, expected index keys, probe term or None)
        self.probe, self.watched, self.interval_s = probe, watched, interval_s
        self.read_timeout_s = 10.0
        self.samples: list[dict] = []
        self.first_sample = asyncio.Event()
        self.all_ready = asyncio.Event()
        self._stop = asyncio.Event()
        self._ready: set = set()

    def stop(self) -> None:
        self._stop.set()

    async def _sample(self, graph, group, expected, term) -> dict:
        inv = stamp()
        sample = {"graph": graph, "inv": inv, "inv_ns": inv.mono_ns, "summary": None, "error": None,
                  "probe_rows": None, "probe_error": None}
        try:
            rows = await asyncio.wait_for(self.probe.index_rows(graph), self.read_timeout_s)
            sample["summary"] = index_summary(self.probe.backend, rows, expected)
        except Exception as exc:  # noqa: BLE001 - an unanswered sample is an observation
            sample["error"] = f"{type(exc).__name__}: {redact(str(exc))[:120]}"
        if term is not None:
            try:
                sample["probe_rows"] = await asyncio.wait_for(self.probe.probe(graph, group, term),
                                                              self.read_timeout_s)
            except Exception as exc:  # noqa: BLE001
                sample["probe_error"] = f"{type(exc).__name__}: {redact(str(exc))[:120]}"
        ret = stamp()
        sample["ret"], sample["ret_ns"] = ret, ret.mono_ns
        return sample

    async def run(self) -> None:
        while not self._stop.is_set():
            for graph, group, expected, term in self.watched:
                sample = await self._sample(graph, group, expected, term)
                self.samples.append(sample)
                if (sample["summary"] or {}).get("ready"):
                    self._ready.add(graph)
            self.first_sample.set()
            if len(self._ready) == len(self.watched):
                self.all_ready.set()
            try:
                await asyncio.wait_for(self._stop.wait(), self.interval_s)
            except asyncio.TimeoutError:
                pass

    def ops(self, run_id: str, k: int) -> list[Op]:
        ops = []
        for n, run in enumerate(compress(self.samples)):
            result = {"summary": run["summary"], "error": run["error"], "probe_rows": run["probe_rows"],
                      "probe_error": run["probe_error"]}
            ops.append(Op(run_id, k, "observe", f"{k}-monitor-{n:04d}", "monitor", "index_status",
                          {"graph": run["graph"], "samples": run["samples"]}, run["inv"], run["ret"], OK, result))
        return ops
