#!/usr/bin/env python3
"""Repro: concurrent Graphiti.search calls fail with "Too many connections" on FalkorDB.

FalkorDriver builds its falkordb client with redis-py's default pool: 100 connections,
and a caller that finds them all busy gets MaxConnectionsError instead of waiting.
Each search fans out several queries, so a modest number of concurrent searches is
enough. Neo4j's driver waits for a free connection instead (pass `neo4j` to compare).

    python repro_falkordb_pool.py [falkordb|neo4j] [concurrent searches]

Needs FalkorDB on 127.0.0.1:16380 or Neo4j on bolt://127.0.0.1:17687 (no auth), and
graphiti-core. No LLM or API key: search makes no model call.
"""

import asyncio
import collections
import os
import sys

os.environ["GRAPHITI_TELEMETRY_ENABLED"] = "false"

from graphiti_core import Graphiti  # noqa: E402
from graphiti_core.driver.falkordb_driver import FalkorDriver  # noqa: E402
from graphiti_core.driver.neo4j_driver import Neo4jDriver  # noqa: E402
from graphiti_core.cross_encoder.client import CrossEncoderClient  # noqa: E402
from graphiti_core.embedder.client import EmbedderClient  # noqa: E402
from graphiti_core.llm_client.client import LLMClient  # noqa: E402

BACKEND = sys.argv[1] if len(sys.argv) > 1 else "falkordb"
CONCURRENT = int(sys.argv[2]) if len(sys.argv) > 2 else 60
GROUP = "repro_pool"


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

    async def one(i):
        try:
            await graphiti.search(f"Alice works at Acme {i}", group_ids=[GROUP])
            return "ok"
        except Exception as exc:  # noqa: BLE001
            return type(exc).__name__

    sequential = collections.Counter([await one(i) for i in range(5)])
    concurrent = collections.Counter(await asyncio.gather(*(one(i) for i in range(CONCURRENT))))
    print(f"{BACKEND}: 5 searches one at a time -> {dict(sequential)}")
    print(f"{BACKEND}: {CONCURRENT} searches at once -> {dict(concurrent)} (expected all ok)")
    await graphiti.close()
    sys.exit(0 if set(concurrent) == {"ok"} else 1)


asyncio.run(main())
