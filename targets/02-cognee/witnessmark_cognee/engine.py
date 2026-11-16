"""Cognee calls, run inside a process whose environment ``envsetup.enter`` has set.

This module imports cognee, so it is imported only in a helper or a worker
process, never in the coordinator.

Entry points an item can name (``item["entry"]``):

- ``add``, ``add_cognify``, ``cognify``: the public ``cognee.add`` and ``cognee.cognify``;
- ``delete``: ``cognee.datasets.delete_data`` for each tagged document of the dataset;
- ``search``: ``cognee.search`` with ``SearchType.CHUNKS`` (no model call);
- ``c3_paused``: #6559's method, credited to its reporter: ``add`` into B is paused after
  its stored file is written and before its row is committed, while A's copy is deleted;
- ``c3_gather``: the same add and delete started together in one process, no pause;
- ``delete_during_cognify``: a delete in one dataset while another dataset is cognified;
- ``improve``: the public ``cognee.improve`` on the dataset, with no session ids, so only the
  graph-fed stages run (``review_conflicts`` and ``global_context_index``; target blueprint C29).
  It fails open: an errored stage is reported in the result, not raised.

``offset_ms`` (or ``offsets``, indexed by the trial) delays the item before it starts.
"""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from uuid import UUID

import cognee  # noqa: F401 - the environment is set before this module is imported

FALKOR_PORT_SHIM = False
if os.environ.get("GRAPH_DATABASE_PROVIDER") == "falkor":  # row R3: the community hybrid adapter registers itself
    import cognee_community_hybrid_adapter_falkor.register  # noqa: F401
    from cognee.infrastructure.databases.vector import use_vector_adapter
    from cognee_community_hybrid_adapter_falkor.falkor_adapter import FalkorDBAdapter

    def _falkor_vector(**kwargs):
        # Cognee forwards vector_db_port, but the adapter's constructor reads only graph_database_port, so its
        # vector instance always dials 6379 (target blueprint C24). Pass the port through; nothing else changes.
        port = kwargs.pop("vector_db_port", None)
        if port:
            kwargs["graph_database_port"] = int(port)
        return FalkorDBAdapter(**kwargs)

    use_vector_adapter("falkor", _falkor_vector)
    FALKOR_PORT_SHIM = True
from sqlalchemy import select

from witnessmark.stubs import CURRENT_OP

from . import envsetup
from .fixtures import all_docs, key, tags_in
from .graph_pages import _graph_data

INDEXED_TYPES = {"Entity": "Entity_name", "EntityType": "EntityType_name", "DocumentChunk": "DocumentChunk_text",
                 "TextDocument": "TextDocument_name", "TextSummary": "TextSummary_text",
                 "GlobalContextSummary": "GlobalContextSummary_text"}  # improve's index nodes (C30)


def _path(location: str) -> str:
    """A stored location as a local path: Cognee writes file:///C:/... on Windows."""
    if location.startswith("file:"):
        from urllib.parse import urlparse
        from urllib.request import url2pathname

        return url2pathname(urlparse(location).path)
    return location


def _exists(location: str | None) -> bool | None:
    if not location:
        return None
    return os.path.exists(_path(location))


def _error_text(exc: BaseException) -> str:
    """The exception and its causes, so a wrapped 'Too many concurrent writers' is still visible."""
    parts, seen = [], set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        parts.append(f"{type(exc).__name__}: {exc}")
        exc = exc.__cause__ or exc.__context__
    return " <- ".join(parts)[:2000]


class CogneeEngine:
    def __init__(self, row: str):
        self.row = row
        self.docs = all_docs()

    # --- identity ----------------------------------------------------------------------------------------------

    async def check(self) -> dict:
        envsetup.assert_telemetry_off()
        import importlib.metadata as md

        versions = {}
        for package in ("cognee", "ladybug", "lancedb", "pylance", "litellm", "neo4j", "falkordb",
                        "cognee-community-hybrid-adapter-falkor"):
            try:
                versions[package] = md.version(package)
            except md.PackageNotFoundError:
                pass
        from cognee.context_global_variables import backend_access_control_enabled
        from cognee.infrastructure.llm.config import get_llm_config

        return {"versions": versions, "telemetry": "off", "blocked": list(envsetup.BLOCKED),
                "falkor_vector_port_shim": FALKOR_PORT_SHIM,
                "access_control": bool(backend_access_control_enabled()),
                "structured_output_framework": get_llm_config().structured_output_framework,
                "pid": os.getpid()}

    async def setup(self) -> dict:
        from cognee.modules.engine.operations.setup import setup
        from cognee.modules.users.methods import get_default_user

        await setup()
        user = await get_default_user()
        if self.row in ("R2", "R3"):  # a server store outlives the fresh root: empty it
            await cognee.prune.prune_system(graph=True, vector=True, metadata=False, cache=False)
        return {"user": str(user.id)}

    # --- helpers -----------------------------------------------------------------------------------------------

    async def _user(self):
        from cognee.modules.users.methods import get_default_user

        return await get_default_user()

    async def _dataset(self, name: str):
        from cognee.infrastructure.databases.relational import get_relational_engine
        from cognee.modules.data.models import Dataset

        user = await self._user()
        async with get_relational_engine().get_async_session() as session:
            return (await session.scalars(select(Dataset).where(Dataset.name == name,
                                                                Dataset.owner_id == user.id))).first()

    async def _rows(self, dataset_id) -> list:
        from cognee.infrastructure.databases.relational import get_relational_engine
        from cognee.modules.data.models import Data

        async with get_relational_engine().get_async_session() as session:
            return list((await session.scalars(select(Data).where(Data.dataset_id == dataset_id))).all())

    def _row_tags(self, row) -> list[str]:
        for location in (row.raw_data_location, row.original_data_location):
            if _exists(location):
                path = _path(location)
                try:
                    return tags_in(Path(path).read_text(encoding="utf-8", errors="replace"))
                except OSError:
                    pass
        return tags_in(row.name or "") or tags_in(str(row.external_metadata or ""))

    def _items(self, tags: list[str], pinned: bool):
        if not pinned:
            return [self.docs[tag].text for tag in tags]
        from cognee.tasks.ingestion.data_item import DataItem

        return [DataItem(data=self.docs[tag].text, data_id=UUID(self.docs[tag].data_id)) for tag in tags]

    def _trial(self) -> int:
        current = CURRENT_OP.get() or {}
        try:
            return int(str(current.get("op_id", "0")).split("-")[0])
        except ValueError:
            return 0

    async def _delete_tags(self, group: str, tags: list[str]) -> dict:
        dataset = await self._dataset(group)
        if dataset is None:
            return {"deleted": 0, "status": "no dataset"}
        user = await self._user()
        statuses = []
        for row in await self._rows(dataset.id):
            if set(self._row_tags(row)) & set(tags):
                receipt = await cognee.datasets.delete_data(dataset_id=dataset.id, data_id=row.id, user=user)
                statuses.append(receipt.get("status") if isinstance(receipt, dict) else str(receipt))
        return {"deleted": len(statuses), "status": statuses}

    async def _add(self, group: str, tags: list[str], pinned: bool) -> int:
        await cognee.add(self._items(tags, pinned), dataset_name=group)
        return len(tags)

    async def _cognify(self, group: str, chunks_per_batch: int | None, data_per_batch: int | None = None) -> None:
        kwargs = {"chunks_per_batch": chunks_per_batch} if chunks_per_batch else {}
        if data_per_batch:
            kwargs["data_per_batch"] = data_per_batch
        await cognee.cognify(datasets=[group], **kwargs)

    # --- operations --------------------------------------------------------------------------------------------

    async def ingest(self, item: dict, group: str) -> dict:
        offset = item.get("offset_ms")
        if "offsets" in item:
            k = self._trial()
            offset = item["offsets"][(k - 1) % len(item["offsets"])] if k > 0 else 0
        if offset:
            await asyncio.sleep(offset / 1000)
        entry = item.get("entry", "add_cognify")
        group = group.split("+")[0]  # a case over several datasets acts on the first
        tags = list(item.get("tags", []))
        pinned = bool(item.get("pinned_ids"))
        started = time.perf_counter()
        result: dict = {"entry": entry, "offset_ms": offset or 0}
        if entry == "add":
            result["added"] = await self._add(group, tags, pinned)
        elif entry == "add_cognify":
            result["added"] = await self._add(group, tags, pinned)
            await self._cognify(group, item.get("chunks_per_batch"), item.get("data_per_batch"))
        elif entry == "add_try_cognify":
            result["added"] = await self._add(group, tags, pinned)
            try:
                await self._cognify(group, item.get("chunks_per_batch"), item.get("data_per_batch"))
                result["cognify"] = "ok"
            except Exception as exc:  # noqa: BLE001 - the outcome is the measurement
                result["cognify"] = _error_text(exc)
        elif entry == "cognify":
            await self._cognify(group, item.get("chunks_per_batch"), item.get("data_per_batch"))
        elif entry == "delete":
            result.update(await self._delete_tags(group, tags))
        elif entry == "search":
            result["found"] = len(await self.search(item["query"], group))
        elif entry == "improve":
            result.update(await self._improve(group, item))
        elif entry in ("c3_paused", "c3_gather"):
            result.update(await self._c3(item, entry == "c3_paused"))
        elif entry == "delete_during_cognify":
            other, other_tags = item["other_group"], item["other_tags"]
            await self._add(other, other_tags, pinned)
            deleted, cognified = await asyncio.gather(self._delete_tags(group, tags), self._cognify(other, None, item.get("data_per_batch")),
                                                      return_exceptions=True)
            for label, outcome in (("delete", deleted), ("cognify_other", cognified)):
                if isinstance(outcome, BaseException):
                    raise RuntimeError(f"{label} failed: {_error_text(outcome)}") from outcome
            result.update(deleted)
        else:
            raise ValueError(f"unknown entry {entry!r}")
        result["seconds"] = round(time.perf_counter() - started, 3)
        return result

    async def _improve(self, group: str, item: dict) -> dict:
        """cognee.improve on one dataset; every stage's status, reason, error and counts go in the result.

        v1.6.8 takes ``review_conflicts`` and builds the global context index by default (target blueprint C29);
        cognee 1.6.1 (row R3) has no ``review_conflicts`` argument and builds the index only when asked (C33).
        Both get every graph-fed stage the version has, and no session ids.
        """
        import inspect

        accepted = inspect.signature(cognee.improve).parameters
        kwargs = {"dataset": group, "session_ids": None,
                  "build_global_context_index": item.get("global_context_index", True)}
        if "review_conflicts" in accepted:
            kwargs["review_conflicts"] = item.get("review_conflicts", True)
        outcome = await cognee.improve(**kwargs)
        stages = [{"stage": s.stage, "status": s.status, "reason": s.reason,
                   "error": (s.error or "")[:2000] or None, "counts": dict(s.counts or {})} for s in outcome.stages]
        return {"improve_status": outcome.status, "improve_error": outcome.error, "stages": stages,
                "improve_kwargs": sorted(k for k in kwargs if k != "dataset")}

    async def _c3(self, item: dict, paused: bool) -> dict:
        """#6559: A's copy of a document is deleted while the same bytes are added to B."""
        import importlib

        ingest_module = importlib.import_module("cognee.tasks.ingestion.ingest_data")
        a, b, tags = item["dataset_a"], item["dataset_b"], item["tags"]
        report: dict = {"paused": paused}
        if paused:
            hold, resume = asyncio.Event(), asyncio.Event()
            original = ingest_module.data_item_to_text_file

            async def slow_loader(*args, **kwargs):
                outcome = await original(*args, **kwargs)
                hold.set()
                await resume.wait()  # the window between the stored file and the row commit, held open
                return outcome

            ingest_module.data_item_to_text_file = slow_loader
            try:
                adding = asyncio.create_task(self._add(b, tags, False))
                await asyncio.wait_for(hold.wait(), 120)
                report["delete"] = await self._delete_tags(a, tags)
                resume.set()
                await adding
            finally:
                ingest_module.data_item_to_text_file = original
                resume.set()
        else:
            added, deleted = await asyncio.gather(self._add(b, tags, False), self._delete_tags(a, tags),
                                                  return_exceptions=True)
            if isinstance(added, BaseException):
                raise RuntimeError(f"add(B) failed: {_error_text(added)}") from added
            report["delete"] = deleted if not isinstance(deleted, BaseException) else _error_text(deleted)
        try:
            await self._cognify(b, None, item.get("data_per_batch"))
            report["cognify_b"] = "ok"
        except Exception as exc:  # noqa: BLE001 - the outcome is the measurement
            report["cognify_b"] = _error_text(exc)
        return report

    async def search(self, query: str, group: str) -> list[str]:
        from cognee.modules.search.types import SearchType

        results = await cognee.search(query_text=query, query_type=SearchType.CHUNKS, datasets=[group], top_k=50)
        texts = []
        for result in results or []:
            payload = result.get("search_result", result) if isinstance(result, dict) else result
            for entry in payload if isinstance(payload, list) else [payload]:
                text = entry.get("text") if isinstance(entry, dict) else getattr(entry, "text", None)
                text = text if isinstance(text, str) else str(entry)
                texts.extend(tags_in(text) or [text[:200]])
        return texts  # the tags of the chunks found

    # --- the canonical dump (target blueprint section 6) -------------------------------------------------------

    async def dump(self, group: str) -> dict:
        if "+" in group:
            return {"datasets": {name: await self.dump(name) for name in group.split("+")}}
        from cognee.context_global_variables import set_database_global_context_variables

        dataset = await self._dataset(group)
        if dataset is None:
            return {"dataset": None, "relational": [], "graph": {}, "vector": {}, "provenance": {}}
        user = await self._user()
        relational = []
        for row in await self._rows(dataset.id):
            relational.append({"tags": self._row_tags(row), "raw_exists": _exists(row.raw_data_location),
                               "original_exists": _exists(row.original_data_location),
                               "pinned_id": str(row.id) in {d.data_id for d in self.docs.values()}})
        relational.sort(key=lambda r: (r["tags"], r["raw_exists"] is True, r["original_exists"] is True))
        async with set_database_global_context_variables(dataset.id, user.id):
            graph, ids_by_type = await self._graph()
            vector = await self._vector(ids_by_type)
        return {"dataset": group, "relational": relational, **graph, "vector": vector}

    async def _graph(self) -> tuple[dict, dict]:
        from cognee.infrastructure.databases.graph import get_graph_engine

        engine = await get_graph_engine()
        nodes, edges = await _graph_data(engine)
        props = {str(node_id): data or {} for node_id, data in nodes}
        keys: dict[str, str] = {}
        for node_id, data in props.items():
            kind = data.get("type", "?")
            if kind in ("DocumentChunk",):
                found = tags_in(data.get("text"))
                keys[node_id] = ",".join(found) if found else f"text:{key(str(data.get('text', '')))[:60]}"
            elif data.get("name") and kind not in ("TextDocument", "TextSummary"):
                keys[node_id] = key(str(data["name"]))
        # Documents and summaries take the key of the chunk they are linked to.
        for _ in range(2):
            for source, target, relation, _data in edges:
                source, target = str(source), str(target)
                if relation == "is_part_of" and source in keys and target not in keys:
                    keys[target] = keys[source]
                if relation == "made_from" and target in keys and source not in keys:
                    keys[source] = keys[target]
        counts: dict[str, dict[str, int]] = {}
        ids_by_type: dict[str, set] = {}
        for node_id, data in props.items():
            kind = data.get("type", "?")
            ids_by_type.setdefault(kind, set()).add(node_id)
            label = keys.get(node_id, f"?{kind}")
            counts.setdefault(kind, {})[label] = counts.setdefault(kind, {}).get(label, 0) + 1
        edge_counts: dict[str, int] = {}
        orphans = 0
        provenance: dict[str, list[str]] = {}
        for source, target, relation, _data in edges:
            source, target = str(source), str(target)
            if source not in props or target not in props:
                orphans += 1
                continue
            label = f"{props[source].get('type')}:{keys.get(source, '?')}|{relation}|" \
                    f"{props[target].get('type')}:{keys.get(target, '?')}"
            edge_counts[label] = edge_counts.get(label, 0) + 1
            if relation == "contains" and props[source].get("type") == "DocumentChunk":
                provenance.setdefault(keys.get(source, "?"), []).append(keys.get(target, "?"))
        return ({"graph": {"nodes": {k: dict(sorted(v.items())) for k, v in sorted(counts.items())},
                           "edges": dict(sorted(edge_counts.items())), "orphan_edges": orphans,
                           "node_count": len(props), "edge_count": len(edges)},
                 "provenance": {k: sorted(v) for k, v in sorted(provenance.items())}}, ids_by_type)

    async def _vector(self, ids_by_type: dict[str, set]) -> dict:
        """Ids per collection, read from the store's files (LanceDB) or the adapter (others)."""
        from cognee.infrastructure.databases.vector import get_vector_engine

        engine = get_vector_engine()
        url = getattr(engine, "url", None)
        report: dict = {}
        graph_ids = set().union(*ids_by_type.values()) if ids_by_type else set()
        if url and os.path.isdir(str(url)):
            import lancedb

            db = lancedb.connect(str(url))
            names = sorted(db.table_names())
            for name in names:
                ids = [str(v) for v in db.open_table(name).to_arrow().column("id").to_pylist()]
                report[name] = self._collection_report(name, ids, graph_ids)
        elif os.environ.get("VECTOR_DB_PROVIDER") == "falkor":
            report["_unsupported"] = "no separate vector store to read: the FalkorDB hybrid adapter keeps each "                                      "vector on its graph node"
        else:
            return {"graph_nodes_without_vector": {}, "_note": "no vector store written yet"} if not graph_ids else                 {"graph_nodes_without_vector": {k: len(v) for k, v in ids_by_type.items() if k in INDEXED_TYPES},
                 "_note": f"no vector store found at {url!r}"}
        missing_vectors = {}
        if "_unsupported" not in report:
            for kind, collection in INDEXED_TYPES.items():
                stored = set(report.get(collection, {}).get("_ids", []))
                missing_vectors[kind] = len(ids_by_type.get(kind, set()) - stored)
        for value in report.values():
            if isinstance(value, dict):
                value.pop("_ids", None)
        report["graph_nodes_without_vector"] = missing_vectors
        return report

    @staticmethod
    def _collection_report(name: str, ids: list[str], graph_ids: set) -> dict:
        counts: dict[str, int] = {}
        for value in ids:
            counts[value] = counts.get(value, 0) + 1
        return {"rows": len(ids), "unique_ids": len(counts),
                "duplicate_ids": sum(1 for c in counts.values() if c > 1),
                "max_rows_per_id": max(counts.values(), default=0),
                "without_graph_node": 0 if name.startswith("EdgeType") else sum(1 for v in counts if v not in graph_ids),
                "_ids": sorted(counts)}

    async def graph_counts(self, group: str) -> dict:
        """Cheap counts for the C4 ladder: nodes and edges in the dataset's graph."""
        from cognee.context_global_variables import set_database_global_context_variables
        from cognee.infrastructure.databases.graph import get_graph_engine

        dataset = await self._dataset(group)
        user = await self._user()
        async with set_database_global_context_variables(dataset.id, user.id):
            engine = await get_graph_engine()
            nodes, edges = await _graph_data(engine)
            entities = sum(1 for _id, data in nodes if (data or {}).get("type") == "Entity")
            return {"nodes": len(nodes), "edges": len(edges), "entities": entities,
                    "graph_path": getattr(engine, "db_path", None) or getattr(engine, "_db_path", None)}
