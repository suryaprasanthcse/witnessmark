#!/usr/bin/env python3
"""Repro: Graphiti.search(num_results=n) changes the module-level EDGE_HYBRID_SEARCH_RRF.limit,
which add_episode's duplicate and contradiction searches also use.

    python repro_shared_search_limit.py [falkordb|neo4j]

Needs FalkorDB on 127.0.0.1:16380 or Neo4j on bolt://127.0.0.1:17687 (no auth), and graphiti-core.
No LLM or API key. (The consequence for ingestion, eight current versions of a single-valued fact
instead of one, is measured in Witnessmark's G5 scenario.)
"""

import asyncio
import os
import sys

os.environ["GRAPHITI_TELEMETRY_ENABLED"] = "false"

from graphiti_core import Graphiti  # noqa: E402
from graphiti_core.driver.falkordb_driver import FalkorDriver  # noqa: E402
from graphiti_core.driver.neo4j_driver import Neo4jDriver  # noqa: E402
from graphiti_core.cross_encoder.client import CrossEncoderClient  # noqa: E402
from graphiti_core.embedder.client import EmbedderClient  # noqa: E402
from graphiti_core.llm_client.client import LLMClient  # noqa: E402
from graphiti_core.search import search_config_recipes  # noqa: E402

BACKEND = sys.argv[1] if len(sys.argv) > 1 else "falkordb"


class NoLLM(LLMClient):
    async def _generate_response(self, *args, **kwargs):
        raise AssertionError("this repro makes no model call")


class NoReranker(CrossEncoderClient):
    async def rank(self, query, passages):
        return [(passage, 0.0) for passage in passages]


class FixedEmbedder(EmbedderClient):
    async def create(self, input_data):
        return [1.0] + [0.0] * 1023

    async def create_batch(self, input_data_list):
        return [[1.0] + [0.0] * 1023 for _ in input_data_list]


async def main():
    driver = (FalkorDriver(host="127.0.0.1", port=16380) if BACKEND == "falkordb"
              else Neo4jDriver("bolt://127.0.0.1:17687", "neo4j", "unused"))
    graphiti = Graphiti(graph_driver=driver, llm_client=NoLLM(None), embedder=FixedEmbedder(), cross_encoder=NoReranker())
    await graphiti.build_indices_and_constraints()
    before = search_config_recipes.EDGE_HYBRID_SEARCH_RRF.limit
    await graphiti.search("Alice works at Acme", group_ids=["repro_limit"], num_results=1)
    after = search_config_recipes.EDGE_HYBRID_SEARCH_RRF.limit
    print(f"shared EDGE_HYBRID_SEARCH_RRF.limit: before a search {before}, after search(num_results=1) {after} "
          f"(expected {before}: a read should not change the config later writes use)")
    await graphiti.close()
    sys.exit(0 if after == before else 1)


asyncio.run(main())
