"""Exercise the Cognee harness helpers without loading Cognee."""

import asyncio
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "targets" / "02-cognee"))
try:
    from witnessmark_cognee.graph_pages import _graph_data
    from witnessmark_cognee.scenarios import _shared_store
except ImportError as exc:
    raise unittest.SkipTest(f"Cognee harness helpers unavailable: {exc}") from exc


class SharedStoreTest(unittest.TestCase):
    def setUp(self):
        self.graph = {"nodes": ["alice"], "edges": []}
        self.a = {"graph": self.graph, "relational": [{"id": "a"}]}
        self.b = {"graph": dict(self.graph), "relational": [{"id": "b"}]}

    def test_identical_nonempty_graphs_merge_rows_and_ignore_missing_groups(self):
        states = {"a": self.a, "b": self.b}
        merged = _shared_store(states, ["a", "missing", "b"])
        self.assertEqual(merged, {"graph": self.graph, "relational": [{"id": "a"}, {"id": "b"}]})
        self.assertEqual(self.a["relational"], [{"id": "a"}])
        self.assertEqual(self.b["relational"], [{"id": "b"}])

    def test_different_graphs_return_none(self):
        other = {"graph": {"nodes": ["bob"], "edges": []}}
        self.assertIsNone(_shared_store({"a": self.a, "b": other}, ["a", "b"]))

    def test_one_dump_returns_none(self):
        self.assertIsNone(_shared_store({"a": self.a}, ["a", "missing"]))

    def test_empty_graphs_return_none(self):
        empty = {"graph": {"nodes": [], "edges": []}}
        self.assertIsNone(_shared_store({"a": empty, "b": empty}, ["a", "b"]))


class FakeGraphEngine:
    def __init__(self, node_count, edge_count):
        self.node_count = node_count
        self.edge_count = edge_count
        self.calls = []
        self.get_graph_data = AsyncMock(return_value=(["node"], ["edge"]))

    async def query(self, query, params):
        skip, limit = params["skip"], params["limit"]
        if query.startswith("MATCH (n) RETURN"):
            kind, order_by = "nodes", "ID(n)"
            rows = [(i, ["Entity"], {"id": str(i)}) for i in range(skip, min(skip + limit, self.node_count))]
        elif query.startswith("MATCH (n)-[r]->(m) RETURN"):
            kind, order_by = "edges", "ID(r)"
            rows = [(i, i + 1, "knows", {"index": i}) for i in range(skip, min(skip + limit, self.edge_count))]
        else:
            raise AssertionError(f"Unexpected query: {query}")
        if not query.endswith(f"ORDER BY {order_by} SKIP $skip LIMIT $limit"):
            raise AssertionError(f"Unexpected pagination: {query}")
        self.calls.append((kind, skip, limit, len(rows)))
        return SimpleNamespace(result_set=rows)

    @staticmethod
    def _deserialize_node_properties(properties):
        return {"index": int(properties["id"])}


class GraphDataTest(unittest.TestCase):
    def test_other_provider_uses_only_get_graph_data(self):
        engine = FakeGraphEngine(0, 0)
        with patch.dict("os.environ", {"GRAPH_DATABASE_PROVIDER": "ladybug"}):
            self.assertEqual(asyncio.run(_graph_data(engine)), (["node"], ["edge"]))
        engine.get_graph_data.assert_awaited_once_with()
        self.assertEqual(engine.calls, [])

    def test_falkor_pages_all_nodes_and_edges_in_order(self):
        engine = FakeGraphEngine(12_001, 10_500)
        with patch.dict("os.environ", {"GRAPH_DATABASE_PROVIDER": "falkor"}):
            nodes, edges = asyncio.run(_graph_data(engine))
        self.assertEqual(nodes, [(str(i), {"index": i}) for i in range(12_001)])
        self.assertEqual(edges, [(str(i), str(i + 1), "knows", {"index": i}) for i in range(10_500)])
        self.assertEqual(engine.calls, [
            ("nodes", 0, 5000, 5000), ("nodes", 5000, 5000, 5000), ("nodes", 10000, 5000, 2001),
            ("edges", 0, 5000, 5000), ("edges", 5000, 5000, 5000), ("edges", 10000, 5000, 500),
        ])
        engine.get_graph_data.assert_not_called()

    def test_falkor_exact_multiple_ends_on_empty_page(self):
        engine = FakeGraphEngine(10_000, 0)
        with patch.dict("os.environ", {"GRAPH_DATABASE_PROVIDER": "falkor"}):
            nodes, edges = asyncio.run(_graph_data(engine))
        self.assertEqual(len(nodes), 10_000)
        self.assertEqual(edges, [])
        self.assertEqual(engine.calls, [
            ("nodes", 0, 5000, 5000), ("nodes", 5000, 5000, 5000), ("nodes", 10000, 5000, 0),
            ("edges", 0, 5000, 0),
        ])
