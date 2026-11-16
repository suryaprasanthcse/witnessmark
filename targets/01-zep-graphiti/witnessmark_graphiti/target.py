"""Witnessmark's adapter for Graphiti (target blueprint sections 2 to 4).

Graphiti sends anonymous telemetry unless GRAPHITI_TELEMETRY_ENABLED is off, so
this module switches it off before graphiti_core is imported, and open() refuses
to run if the switch did not take.
"""

from __future__ import annotations

import os

os.environ["GRAPHITI_TELEMETRY_ENABLED"] = "false"  # must precede every graphiti_core import

import asyncio  # noqa: E402
import importlib.metadata  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

from graphiti_core import Graphiti  # noqa: E402
from graphiti_core.driver.falkordb_driver import FalkorDriver  # noqa: E402
from graphiti_core.driver.neo4j_driver import Neo4jDriver  # noqa: E402
from graphiti_core.edges import EntityEdge, EpisodicEdge  # noqa: E402
from graphiti_core.errors import GroupsEdgesNotFoundError, GroupsNodesNotFoundError  # noqa: E402
from graphiti_core.nodes import EntityNode, EpisodeType, EpisodicNode  # noqa: E402
from graphiti_core.search import search_config_recipes  # noqa: E402
from graphiti_core.telemetry import is_telemetry_enabled  # noqa: E402
from graphiti_core.utils.bulk_utils import RawEpisode  # noqa: E402
from graphiti_core.utils.maintenance.graph_data_operations import clear_data  # noqa: E402

from witnessmark import __version__ as harness_version  # noqa: E402
from witnessmark.memory import MemoryTarget  # noqa: E402
from witnessmark.stubs import StubLedger  # noqa: E402

from .fixtures import build  # noqa: E402
from .stubs import StubEmbedder, StubLLM, StubReranker  # noqa: E402


def _when(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def _iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        moment = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return str(value)


class GraphitiTarget(MemoryTarget):
    name = "graphiti"
    repo = "getzep/graphiti"

    def __init__(self, backend: str, fixture: str, anchor: str, build_ref: str = "v0.31.2", commit: str = "",
                 host: str = "127.0.0.1", falkordb_port: int = 16380, neo4j_bolt_port: int = 17687,
                 falkordb_pool: str = "blocking", bind_group: str | None = None):
        if backend not in ("falkordb", "neo4j"):
            raise ValueError("backend must be falkordb or neo4j")
        if falkordb_pool not in ("blocking", "default"):
            raise ValueError("falkordb_pool must be blocking or default")
        self.backend, self.build_ref, self.commit, self.falkordb_pool = backend, build_ref, commit, falkordb_pool
        self.host, self.falkordb_port, self.neo4j_bolt_port = host, falkordb_port, neo4j_bolt_port
        # bind_group: on FalkorDB, the driver's own database is this group's graph, so calls that read through
        # Graphiti.driver (remove_episode, graphiti.py L2174-2215 @ v0.31.2) reach the group (G8).
        self.bind_group = bind_group
        self.fixture = build(fixture, anchor)
        self.ledger = StubLedger()
        self.graphiti: Graphiti | None = None
        self.episode_uuids: dict[tuple[str, str], str] = {}

    # --- lifecycle ---------------------------------------------------------------------------------------------

    async def open(self) -> None:
        self.graphiti = self.make_graphiti()

    def make_graphiti(self) -> Graphiti:
        """A new Graphiti instance with a new driver. Inside a running event loop the driver's constructor
        schedules its own index build (falkordb_driver.py L178-184, neo4j_driver.py L92-97 @ v0.31.2)."""
        if is_telemetry_enabled():
            raise RuntimeError("Graphiti telemetry is enabled; refusing to run (set GRAPHITI_TELEMETRY_ENABLED=false)")
        database = {"database": self.bind_group} if self.backend == "falkordb" and self.bind_group else {}
        if self.backend == "falkordb" and self.falkordb_pool == "blocking":
            # Same 100 connections as the client's default pool, but a caller waits for a free
            # connection instead of failing with "Too many connections" (redis-py's ConnectionPool).
            from falkordb.asyncio import FalkorDB
            from redis.asyncio import BlockingConnectionPool

            pool = BlockingConnectionPool(host=self.host, port=self.falkordb_port, max_connections=100, timeout=120,
                                          decode_responses=True)
            driver = FalkorDriver(falkor_db=FalkorDB(connection_pool=pool), **database)
        elif self.backend == "falkordb":
            driver = FalkorDriver(host=self.host, port=self.falkordb_port, **database)
        else:
            driver = Neo4jDriver(uri=f"bolt://{self.host}:{self.neo4j_bolt_port}", user="neo4j", password="witnessmark")
        return Graphiti(graph_driver=driver, llm_client=StubLLM(self.fixture, self.ledger),
                        embedder=StubEmbedder(), cross_encoder=StubReranker())

    async def renew(self) -> None:
        """Close the current instance (after its background work) and build a new one (G6a, G6b)."""
        await self.close()
        self.graphiti = self.make_graphiti()

    async def close(self) -> None:
        if self.graphiti is not None:
            await self.quiesce()
            await self.graphiti.close()
            self.graphiti = None

    def identity(self) -> dict:
        record = {"name": "graphiti", "repo": self.repo, "ref": self.build_ref,
                  "package_version": importlib.metadata.version("graphiti-core")}
        if self.commit:
            record["commit"] = self.commit
        return record

    def components(self) -> list[dict]:
        backend = {"falkordb": "FalkorDB 6.0.4 (graph module 60004)", "neo4j": "Neo4j 5.26.2 Community"}[self.backend]
        return [
            {"role": "sut", "name": "graphiti-core", "version": importlib.metadata.version("graphiti-core"),
             "config": {"build": self.build_ref, "backend": self.backend, "telemetry": "off",
                        "falkordb_pool": self.falkordb_pool if self.backend == "falkordb" else None,
                        **({"bound_graph": self.bind_group} if self.bind_group and self.backend == "falkordb" else {}),
                        "driver": importlib.metadata.version("falkordb" if self.backend == "falkordb" else "neo4j")}},
            {"role": "store", "name": self.backend, "version": backend},
            {"role": "stub", "name": "witnessmark-graphiti-stubs", "version": harness_version,
             "config": {"fixture": self.fixture.name, "llm": "ideal-model fixture answers",
                        "embedder": "hashed bag of words, 1024 dimensions", "reranker": "word overlap"}},
        ]

    # --- groups ------------------------------------------------------------------------------------------------

    def _driver(self, group: str):
        # FalkorDB keeps each group in its own graph; Neo4j keeps every group in one database.
        return self.graphiti.driver.clone(database=group) if self.backend == "falkordb" else self.graphiti.driver

    async def reset(self, group: str) -> None:
        driver = self._driver(group)
        await clear_data(driver, [group])
        if self.backend == "falkordb":
            await clear_data(self.graphiti.driver, [group])  # strays written to the default graph
        await driver.build_indices_and_constraints()
        await self._await_indexes(driver)

    async def drop_group(self, group: str) -> None:
        """FalkorDB: delete the group's graph with its indexes (a fresh group, G6c). Neo4j: empty the group;
        its indexes are database-wide."""
        if self.backend == "neo4j":
            await clear_data(self.graphiti.driver, [group])
            return
        try:
            await self.graphiti.driver.client.select_graph(group).delete()
        except Exception as exc:  # noqa: BLE001 - a graph that does not exist is already fresh
            if "empty key" not in str(exc).lower() and "no such" not in str(exc).lower():
                raise

    async def _await_indexes(self, driver) -> None:
        if self.backend == "neo4j":
            await driver.execute_query("CALL db.awaitIndexes(120)")
            return
        for _ in range(400):  # FalkorDB builds indexes in the background (GNOMON hazard S6)
            records, _, _ = await driver.execute_query("CALL db.indexes() YIELD status RETURN status")
            if all(str(record["status"]).upper() == "OPERATIONAL" for record in records):
                return
            await asyncio.sleep(0.05)
        raise RuntimeError("FalkorDB indexes did not become OPERATIONAL within 20 s")

    async def quiesce(self) -> None:
        # FalkorDriver clones start index builds as background tasks; let them finish.
        current = asyncio.current_task()
        pending = [task for task in asyncio.all_tasks() if task is not current and not task.done()]
        if pending:
            await asyncio.wait(pending, timeout=30)

    # --- operations --------------------------------------------------------------------------------------------

    async def ingest(self, item: dict, group: str) -> dict:
        entry = item.get("entry", "add_episode")
        if entry == "search":
            facts = await self.search(item["query"], group, item.get("num_results"))
            return {"facts": len(facts),
                    "edge_search_limit_after": search_config_recipes.EDGE_HYBRID_SEARCH_RRF.limit}
        episode = self.fixture.episode(item["tag"])
        if entry == "add_episode":
            result = await self.graphiti.add_episode(
                name=episode.name, episode_body=episode.body, source_description="witnessmark fixture",
                reference_time=_when(episode.reference_time), source=EpisodeType.message, group_id=group)
            self.episode_uuids[(group, episode.tag)] = result.episode.uuid
            return {"episode": episode.tag, "nodes": len(result.nodes), "edges": len(result.edges)}
        if entry == "remove_episode":
            await self.graphiti.remove_episode(self.episode_uuids[(group, item["tag"])])
            return {"removed": item["tag"]}
        if entry == "add_episode_bulk":
            raw = RawEpisode(name=episode.name, content=episode.body, source_description="witnessmark fixture",
                             source=EpisodeType.message, reference_time=_when(episode.reference_time))
            result = await self.graphiti.add_episode_bulk([raw], group_id=group)
            return {"episode": episode.tag, "nodes": len(result.nodes), "edges": len(result.edges)}
        if entry == "add_triplet":
            edges = 0
            for fact in episode.facts:
                now = datetime.now(timezone.utc)
                source = EntityNode(name=fact.source, group_id=group, labels=["Entity"], summary="", created_at=now)
                target = EntityNode(name=fact.target, group_id=group, labels=["Entity"], summary="", created_at=now)
                edge = EntityEdge(group_id=group, source_node_uuid=source.uuid, target_node_uuid=target.uuid,
                                  created_at=now, name=fact.relation, fact=fact.fact, episodes=[],
                                  valid_at=_when(fact.valid_at), invalid_at=_when(fact.invalid_at))
                result = await self.graphiti.add_triplet(source, edge, target)
                edges += len(result.edges)
            return {"episode": episode.tag, "edges": edges}
        raise ValueError(f"unknown entry point {entry!r}")

    async def search(self, query: str, group: str, num_results: int | None = None) -> list[str]:
        kwargs = {} if num_results is None else {"num_results": num_results}
        edges = await self.graphiti.search(query, group_ids=[group], **kwargs)
        return [edge.fact for edge in edges]

    @staticmethod
    async def _all(kind, driver, group: str) -> list:
        # get_by_group_ids raises instead of returning [] when a group holds nothing of that kind.
        try:
            return await kind.get_by_group_ids(driver, [group])
        except (GroupsEdgesNotFoundError, GroupsNodesNotFoundError):
            return []

    async def dump(self, group: str) -> dict:
        driver = self._driver(group)
        nodes = await self._all(EntityNode, driver, group)
        edges = await self._all(EntityEdge, driver, group)
        episodes = await self._all(EpisodicNode, driver, group)
        mentions = await self._all(EpisodicEdge, driver, group)
        names = {node.uuid: node.name for node in nodes}
        episode_names = {episode.uuid: episode.name for episode in episodes}
        mentioned_by: dict[str, list[str]] = {}
        for mention in mentions:
            mentioned_by.setdefault(mention.target_node_uuid, []).append(
                episode_names.get(mention.source_node_uuid, "?"))
        state = {
            "entities": sorted(
                ({"name": node.name, "key": self.fixture.entity_key(node.name),
                  "mentioned_by": sorted(mentioned_by.get(node.uuid, []))} for node in nodes),
                key=lambda entity: (entity["key"] or "", entity["name"], entity["mentioned_by"])),
            "facts": sorted(
                ({"fact": edge.fact, "source": names.get(edge.source_node_uuid, "?"),
                  "target": names.get(edge.target_node_uuid, "?"), "relation": edge.name,
                  "valid_at": _iso(edge.valid_at), "invalid_at": _iso(edge.invalid_at),
                  "expired": edge.expired_at is not None, "episodes": len(edge.episodes or [])} for edge in edges),
                key=lambda fact: (fact["fact"], fact["valid_at"] or "", fact["invalid_at"] or "", fact["expired"])),
            "episodes": sorted(episode.name for episode in episodes),
        }
        if self.backend == "falkordb" and self.bind_group is None:
            # Writes that bypass the group's graph land in the default graph; report them, do not hide them.
            strays = await self._all(EntityEdge, self.graphiti.driver, group)
            state["facts_in_default_graph"] = sorted(
                ({"fact": edge.fact, "valid_at": _iso(edge.valid_at), "invalid_at": _iso(edge.invalid_at),
                  "expired": edge.expired_at is not None} for edge in strays),
                key=lambda fact: (fact["fact"], fact["valid_at"] or ""))
        return state

    def drain_stub_calls(self) -> list[dict]:
        return self.ledger.drain()


def make_target(**options) -> GraphitiTarget:
    return GraphitiTarget(**options)
