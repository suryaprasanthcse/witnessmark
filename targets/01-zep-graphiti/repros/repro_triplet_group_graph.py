#!/usr/bin/env python3
"""Repro: on FalkorDB, Graphiti.add_triplet writes a group's triplet into the default graph.

On FalkorDB every group_id is its own graph, and add_episode writes to the group's
graph through a per-call driver clone. add_triplet uses self.driver instead, so its
nodes and edge land in the default graph (`default_db`), where group-scoped reads
such as EntityEdge.get_by_group_ids(driver.clone(group), [group]) never look.

Needs FalkorDB on 127.0.0.1:16380 (or pass host and port) and graphiti-core.
No LLM or API key: the edge carries its own dates, so add_triplet makes no model call.

    python repro_triplet_group_graph.py [host] [port]
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

os.environ["GRAPHITI_TELEMETRY_ENABLED"] = "false"

from graphiti_core import Graphiti  # noqa: E402
from graphiti_core.driver.falkordb_driver import FalkorDriver  # noqa: E402
from graphiti_core.edges import EntityEdge  # noqa: E402
from graphiti_core.cross_encoder.client import CrossEncoderClient  # noqa: E402
from graphiti_core.embedder.client import EmbedderClient  # noqa: E402
from graphiti_core.errors import GroupsEdgesNotFoundError  # noqa: E402
from graphiti_core.llm_client.client import LLMClient  # noqa: E402
from graphiti_core.nodes import EntityNode  # noqa: E402
from graphiti_core.utils.maintenance.graph_data_operations import clear_data  # noqa: E402

HOST = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 16380
GROUP = "repro_triplet"


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


async def edges_in(driver, group):
    try:
        return await EntityEdge.get_by_group_ids(driver, [group])
    except GroupsEdgesNotFoundError:
        return []


async def main():
    graphiti = Graphiti(graph_driver=FalkorDriver(host=HOST, port=PORT), llm_client=NoLLM(None),
                        embedder=FixedEmbedder(), cross_encoder=NoReranker())
    group_graph = graphiti.driver.clone(database=GROUP)
    await clear_data(group_graph, [GROUP])
    await clear_data(graphiti.driver, [GROUP])
    await group_graph.build_indices_and_constraints()
    await graphiti.driver.build_indices_and_constraints()

    now = datetime.now(timezone.utc)
    alice = EntityNode(name="Alice", group_id=GROUP, labels=["Entity"], summary="", created_at=now)
    acme = EntityNode(name="Acme", group_id=GROUP, labels=["Entity"], summary="", created_at=now)
    edge = EntityEdge(group_id=GROUP, source_node_uuid=alice.uuid, target_node_uuid=acme.uuid, created_at=now,
                      name="WORKS_AT", fact="Alice works at Acme", episodes=[], valid_at=now)
    await graphiti.add_triplet(alice, edge, acme)

    in_group = await edges_in(group_graph, GROUP)
    in_default = await edges_in(graphiti.driver, GROUP)
    print(f"edges for {GROUP} in graph '{GROUP}' (where add_episode writes and group reads look): "
          f"{len(in_group)} (expected 1)")
    print(f"edges for {GROUP} in the default graph: {len(in_default)} (expected 0)")
    await graphiti.close()
    sys.exit(0 if len(in_group) == 1 and not in_default else 1)


asyncio.run(main())
