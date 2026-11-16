#!/usr/bin/env python3
"""Repro: remove_episode and a concurrent add_episode that names the removed episode's entity (Graphiti G8).

Episode G8S says "Alice works at Acme". Episode G8E repeats that fact and adds "Alice approved the Payments
budget"; before the race it is the only episode that names Payments. remove_episode(G8E) and add_episode(G8N),
"Alice audited Payments", then run at the same time. Done one after the other, in either order, the group ends
with episodes G8S and G8N, the entities Alice, Acme and Payments once each, and the facts "Alice works at Acme"
(carried by G8S) and "Alice audited Payments". The script runs that sequential control first (the remove, then
the add), then the concurrent case once per iteration, and prints expected next to observed for each.

    python repro_g8_remove_vs_add.py [neo4j|falkordb] [iterations]

Needs Neo4j on bolt://127.0.0.1:17687 (no auth) or FalkorDB on 127.0.0.1:16380, and graphiti-core. The model,
embedder and reranker are inline deterministic fakes that answer from the fixture below, so there is no API key
and no call to a model provider. Telemetry is off. On FalkorDB the driver is bound to the group's graph, because
remove_episode reads and deletes through Graphiti.driver (graphiti.py L2174-2213 at v0.31.2).

Exit status: 0 if every concurrent iteration ends in the expected state, 1 if any does not, 2 if the
sequential control does not.
"""

import asyncio
import hashlib
import json
import math
import os
import re
import sys
from datetime import datetime, timedelta, timezone

os.environ["GRAPHITI_TELEMETRY_ENABLED"] = "false"

from graphiti_core import Graphiti  # noqa: E402
from graphiti_core.cross_encoder.client import CrossEncoderClient  # noqa: E402
from graphiti_core.driver.falkordb_driver import FalkorDriver  # noqa: E402
from graphiti_core.driver.neo4j_driver import Neo4jDriver  # noqa: E402
from graphiti_core.edges import EntityEdge  # noqa: E402
from graphiti_core.embedder.client import EmbedderClient  # noqa: E402
from graphiti_core.errors import GroupsEdgesNotFoundError, GroupsNodesNotFoundError  # noqa: E402
from graphiti_core.llm_client.client import LLMClient  # noqa: E402
from graphiti_core.llm_client.config import LLMConfig, ModelSize  # noqa: E402
from graphiti_core.nodes import EntityNode, EpisodeType, EpisodicNode  # noqa: E402
from graphiti_core.telemetry import is_telemetry_enabled  # noqa: E402
from graphiti_core.utils.maintenance.graph_data_operations import clear_data  # noqa: E402

BACKEND = sys.argv[1] if len(sys.argv) > 1 else "neo4j"
ITERATIONS = int(sys.argv[2]) if len(sys.argv) > 2 else 20
GROUP = "repro_g8"
BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)

SHARED, REMOVED, ADDED = "Alice works at Acme", "Alice approved the Payments budget", "Alice audited Payments"
EPISODES = {  # tag: (text, reference time, entities, facts as (source, target, relation, fact, valid_at))
    "G8S": ("Alice works at Acme.", BASE, ("Alice", "Acme"),
            [("Alice", "Acme", "WORKS_AT", SHARED, "2025-01-01T00:00:00Z")]),
    "G8E": ("Alice from Acme approved the Payments budget.", BASE + timedelta(hours=1), ("Alice", "Acme", "Payments"),
            [("Alice", "Acme", "WORKS_AT", SHARED, "2025-01-01T00:00:00Z"),
             ("Alice", "Payments", "APPROVED", REMOVED, "2026-01-01T01:00:00Z")]),
    "G8N": ("Alice audited Payments.", BASE + timedelta(hours=2), ("Alice", "Payments"),
            [("Alice", "Payments", "AUDITED", ADDED, "2026-01-01T02:00:00Z")]),
}
EXPECTED = {"episodes": ["G8N", "G8S"], "entities": ["Acme", "Alice", "Payments"],
            "facts": [f"{ADDED} (1 episode)", f"{SHARED} (1 episode)"]}


# --- deterministic fakes: each answers from EPISODES the way a perfect model would --------------------------------

def section(text, *tags):
    for tag in tags:
        match = re.search(rf"<{re.escape(tag)}>[ \t]*\n(.*?)\n[ \t]*</{re.escape(tag)}>", text, re.S)
        if match:
            return match.group(1).strip()
    return None


def current_episode(text):
    tags = re.findall(r"\[wm:(G8[SEN])\]", section(text, "CURRENT MESSAGE", "CURRENT_MESSAGE", "CURRENT MESSAGES")
                      or "")
    if not tags:
        raise RuntimeError("the prompt's current message names no fixture episode")
    return EPISODES[tags[0]]


def extract_nodes(text):
    return {"extracted_entities": [{"name": name, "entity_type_id": 0, "episode_indices": [0]}
                                   for name in current_episode(text)[2]]}


def extract_edges(text):
    return {"edges": [{"source_entity_name": s, "target_entity_name": t, "relation_type": r, "fact": f,
                       "valid_at": v, "invalid_at": None, "episode_indices": [0]}
                      for s, t, r, f, v in current_episode(text)[3]]}


def resolve_edge(text):
    import ast
    existing = ast.literal_eval(section(text, "EXISTING FACTS") or "[]")
    new = " ".join((section(text, "NEW FACT") or "").lower().split())
    return {"duplicate_facts": [e["idx"] for e in existing if " ".join(e["fact"].lower().split()) == new],
            "contradicted_facts": []}  # no fixture fact contradicts another


def dedupe_nodes(text):
    entities = json.loads(section(text, "ENTITIES") or "[]")
    existing = json.loads(section(text, "EXISTING ENTITIES") or "[]")
    return {"entity_resolutions": [
        {"id": e["id"], "name": e.get("name", ""),
         "duplicate_candidate_id": next((c["candidate_id"] for c in existing
                                         if c.get("name", "").lower() == e.get("name", "").lower()), -1)}
        for e in entities]}


ANSWERS = {
    "extract_nodes.extract_message": extract_nodes,
    "extract_edges.edge": extract_edges,
    "dedupe_edges.resolve_edge": resolve_edge,
    "dedupe_nodes.nodes": dedupe_nodes,
    "extract_nodes.extract_summaries_batch": lambda text: {"summaries": []},
    "extract_nodes.extract_entity_summaries_from_episodes": lambda text: {"summaries": []},
    "extract_nodes.extract_attributes": lambda text: {},
    "extract_edges.extract_attributes": lambda text: {},
}


class FixtureLLM(LLMClient):
    def __init__(self):
        super().__init__(LLMConfig(api_key="unused", model="fixture", small_model="fixture"))

    async def generate_response(self, messages, response_model=None, max_tokens=None, model_size=ModelSize.medium,
                                group_id=None, prompt_name=None, *, attribute_extraction=False, model=None):
        if prompt_name not in ANSWERS:
            raise RuntimeError(f"no fixture answer for prompt {prompt_name!r}")
        answer = ANSWERS[prompt_name]("\n".join(message.content for message in messages))
        if response_model is not None and answer:
            response_model(**answer)  # the answer must fit the schema Graphiti parses it with
        return answer

    async def _generate_response(self, *args, **kwargs):
        raise RuntimeError("answers come from generate_response only")


class HashedEmbedder(EmbedderClient):
    """A signed bag of words hashed into 1,024 buckets: equal texts give equal vectors."""

    async def create(self, input_data):
        vector = [0.0] * 1024
        text = input_data if isinstance(input_data, str) else " ".join(map(str, input_data))
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            digest = hashlib.sha256(word.encode()).digest()
            vector[int.from_bytes(digest[:4], "big") % 1024] += 1.0 if digest[4] & 1 else -1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector] if any(vector) else [1.0] + [0.0] * 1023

    async def create_batch(self, input_data_list):
        return [await self.create(text) for text in input_data_list]


class OverlapReranker(CrossEncoderClient):
    async def rank(self, query, passages):
        words = set(query.lower().split())
        return sorted(((p, len(words & set(p.lower().split())) / (len(words | set(p.lower().split())) or 1))
                       for p in passages), key=lambda pair: (-pair[1], pair[0]))


# --- the repro ---------------------------------------------------------------------------------------------------

def make_graphiti():
    if is_telemetry_enabled():
        raise SystemExit("Graphiti telemetry is on; set GRAPHITI_TELEMETRY_ENABLED=false")
    driver = (FalkorDriver(host="127.0.0.1", port=16380, database=GROUP) if BACKEND == "falkordb"
              else Neo4jDriver("bolt://127.0.0.1:17687", "neo4j", "unused"))
    return Graphiti(graph_driver=driver, llm_client=FixtureLLM(), embedder=HashedEmbedder(),
                    cross_encoder=OverlapReranker())


async def settle():
    """Let the drivers' background index builds finish."""
    pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task() and not t.done()]
    if pending:
        await asyncio.wait(pending, timeout=30)


async def add(graphiti, tag):
    text, when, _, _ = EPISODES[tag]
    result = await graphiti.add_episode(name=tag, episode_body=f"{text} [wm:{tag}]", source_description="repro",
                                        reference_time=when, source=EpisodeType.message, group_id=GROUP)
    return result.episode.uuid


async def reset_and_seed(graphiti):
    await clear_data(graphiti.driver, [GROUP])
    await graphiti.build_indices_and_constraints()
    if BACKEND == "falkordb":
        for _ in range(400):
            records, _, _ = await graphiti.driver.execute_query("CALL db.indexes() YIELD status RETURN status")
            if all(str(r["status"]).upper() == "OPERATIONAL" for r in records):
                break
            await asyncio.sleep(0.05)
    else:
        await graphiti.driver.execute_query("CALL db.awaitIndexes(120)")
    await add(graphiti, "G8S")
    return await add(graphiti, "G8E")


async def everything(kind, driver):
    try:
        return await kind.get_by_group_ids(driver, [GROUP])
    except (GroupsEdgesNotFoundError, GroupsNodesNotFoundError):
        return []


async def observe(graphiti):
    await settle()
    entities = await everything(EntityNode, graphiti.driver)
    facts = await everything(EntityEdge, graphiti.driver)
    episodes = await everything(EpisodicNode, graphiti.driver)
    return {"episodes": sorted(e.name for e in episodes), "entities": sorted(e.name for e in entities),
            "facts": sorted(f"{f.fact} ({len(f.episodes or [])} episode{'s' if len(f.episodes or []) != 1 else ''})"
                            for f in facts)}


async def outcome(call):
    try:
        await call
        return "ok"
    except Exception as exc:  # noqa: BLE001 - an exception is a result here
        return f"{type(exc).__name__}: {exc}"[:120]


def report(label, ops, state):
    lost = {k: sorted(set(EXPECTED[k]) - set(state[k])) for k in EXPECTED}
    extra = {k: sorted(set(state[k]) - set(EXPECTED[k])) for k in EXPECTED}
    same = state == EXPECTED
    print(f"{label}: remove {ops[0]}, add {ops[1]} -> {'as expected' if same else 'DIFFERENT'}")
    for key in EXPECTED:
        print(f"    {key:9s} expected {EXPECTED[key]}")
        print(f"    {'':9s} observed {state[key]}")
    if not same:
        print(f"    missing {lost}; unexpected {extra}")
    return same


async def main():
    graphiti = make_graphiti()
    try:
        g8e = await reset_and_seed(graphiti)
        ops = [await outcome(graphiti.remove_episode(g8e)), await outcome(add(graphiti, "G8N"))]
        control = report("sequential control (remove, then add)", ops, await observe(graphiti))
        if not control:
            print("the sequential control did not reach the expected state; the concurrent result means nothing")
            sys.exit(2)
        differing = 0
        for i in range(1, ITERATIONS + 1):
            g8e = await reset_and_seed(graphiti)
            barrier = asyncio.Barrier(3)

            async def released(make_call):
                await barrier.wait()
                return await outcome(make_call())

            tasks = [asyncio.create_task(released(lambda: graphiti.remove_episode(g8e))),
                     asyncio.create_task(released(lambda: add(graphiti, "G8N")))]
            await barrier.wait()
            ops = list(await asyncio.gather(*tasks))
            differing += not report(f"concurrent {i:02d}", ops, await observe(graphiti))
        print(f"{BACKEND}: sequential control as expected; concurrent: {differing} of {ITERATIONS} iterations "
              "differed from the expected state")
        sys.exit(1 if differing else 0)
    finally:
        await clear_data(graphiti.driver, [GROUP])
        await graphiti.close()


asyncio.run(main())
