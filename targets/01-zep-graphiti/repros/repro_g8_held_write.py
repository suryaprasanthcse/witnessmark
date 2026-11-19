#!/usr/bin/env python3
"""Repro: remove_episode and a concurrent add_episode, plain and with the add's bulk write held (Graphiti G8).

The fixture and the plain case are P5's (repro_g8_remove_vs_add.py). Episode G8S says "Alice works at Acme". Episode
G8E repeats that fact and adds "Alice approved the Payments budget"; before the race it is the only episode that names
Payments. remove_episode(G8E) and add_episode(G8N), "Alice audited Payments", are then released together. Done one
after the other, in either order, the group ends with episodes G8S and G8N, the entities Alice, Acme and Payments once
each, and the facts "Alice works at Acme" (carried by G8S) and "Alice audited Payments".

Variants:
    gather  the two calls released together through an asyncio.Barrier, nothing else changed (P5's concurrent case)
    held    the same, but add_episode's bulk write (add_nodes_and_edges_bulk, which writes the episode, its MENTIONS
            edges, its entities and its facts) waits until remove_episode has run its per-entity MENTIONS count for
            every entity the removed episode mentions. Everything else in both calls runs unchanged. The hold is a
            wrapper installed by this script around graphiti_core.graphiti.add_nodes_and_edges_bulk,
            graphiti_core.graphiti.get_mentioned_nodes and the Graphiti instance's driver.execute_query, for the
            concurrent case only.

    python repro_g8_held_write.py [neo4j|falkordb] [gather|held] [iterations]

Needs Neo4j on bolt://127.0.0.1:17687 (no auth) or FalkorDB on 127.0.0.1:16380, and graphiti-core. The model,
embedder and reranker are inline deterministic fakes that answer from the fixture below, so there is no API key and no
call to a model provider. Telemetry is off. On FalkorDB the driver is bound to the group's graph, because
remove_episode reads and deletes through Graphiti.driver.

Exit status: 0 if every concurrent iteration ends in the expected state, 1 if any does not, 2 if the sequential
control does not, 3 if a hold timed out.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

GROUP = "repro_g8"
BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)
HOLD_TIMEOUT_S = 60.0
COUNT_MARK = "AS episode_count"  # remove_episode's per-entity MENTIONS count, and no other query in graphiti-core

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


# --- the hold -----------------------------------------------------------------------------------------------------


class HeldWrite:
    """Holds add_episode's bulk write until remove_episode has counted the MENTIONS of every entity it mentions.

    remove_episode calls get_mentioned_nodes once, then runs one COUNT_MARK query per returned entity, then saves and
    deletes. The hold opens when the last of those counts has returned (or at once if there is no entity). A bulk write
    that arrives after that passes without waiting. `events` keeps (label, ms since `start`) in the order they happened.
    """

    def __init__(self, timeout_s: float = HOLD_TIMEOUT_S, clock=time.perf_counter):
        self.timeout_s = timeout_s
        self.clock = clock
        self.t0 = clock()
        self.counted = asyncio.Event()
        self.expected: int | None = None
        self.seen = 0
        self.timed_out = False
        self.events: list[tuple[str, float]] = []

    def start(self) -> None:
        self.t0 = self.clock()

    def note(self, label: str) -> None:
        self.events.append((label, (self.clock() - self.t0) * 1000))

    def at(self, label: str) -> float | None:
        return next((ms for name, ms in self.events if name == label), None)

    def _maybe_open(self) -> None:
        if self.expected is not None and self.seen >= self.expected and not self.counted.is_set():
            self.note("count done")
            self.counted.set()

    def install(self, module, driver):
        """Wrap module.get_mentioned_nodes, module.add_nodes_and_edges_bulk and driver.execute_query; return undo."""
        original_mentioned = module.get_mentioned_nodes
        original_bulk = module.add_nodes_and_edges_bulk
        original_execute = driver.execute_query
        had_own = "execute_query" in vars(driver)

        async def get_mentioned_nodes(*args, **kwargs):
            nodes = await original_mentioned(*args, **kwargs)
            self.expected = len(nodes)
            self.note(f"remove found {len(nodes)} mentioned entities")
            self._maybe_open()
            return nodes

        async def execute_query(query, *args, **kwargs):
            result = await original_execute(query, *args, **kwargs)
            if COUNT_MARK in str(query):
                self.seen += 1
                self._maybe_open()
            return result

        async def add_nodes_and_edges_bulk(*args, **kwargs):
            self.note("bulk write reached the hold")
            try:
                await asyncio.wait_for(self.counted.wait(), self.timeout_s)
            except asyncio.TimeoutError:
                self.timed_out = True
                self.note("hold timed out")
            self.note("bulk write starts")
            result = await original_bulk(*args, **kwargs)
            self.note("bulk write returned")
            return result

        module.get_mentioned_nodes = get_mentioned_nodes
        module.add_nodes_and_edges_bulk = add_nodes_and_edges_bulk
        driver.execute_query = execute_query

        def undo():
            module.get_mentioned_nodes = original_mentioned
            module.add_nodes_and_edges_bulk = original_bulk
            if had_own:
                driver.execute_query = original_execute
            else:
                del driver.execute_query  # the class's method shows through again

        return undo

    def summary(self) -> str:
        reached, started, done = self.at("bulk write reached the hold"), self.at("bulk write starts"), self.at("count done")
        parts = [f"count done {fmt(done)}"]
        if reached is None:
            parts.append("bulk write never reached")
        else:
            held = started - reached if started is not None else None
            parts.append(f"bulk write reached the hold {fmt(reached)}, started {fmt(started)}"
                         + (f" (held {held:.1f} ms)" if held is not None and done is not None and reached < done
                            else " (not held: the count had already run)"))
        if self.timed_out:
            parts.append("HOLD TIMED OUT")
        return "; ".join(parts)


def fmt(ms: float | None) -> str:
    return "–" if ms is None else f"at {ms:.1f} ms"


# --- deterministic answers: each answers from EPISODES the way a perfect model would --------------------------------


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


def hashed_vector(text: str) -> list[float]:
    """A signed bag of words hashed into 1,024 buckets: equal texts give equal vectors."""
    vector = [0.0] * 1024
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        digest = hashlib.sha256(word.encode()).digest()
        vector[int.from_bytes(digest[:4], "big") % 1024] += 1.0 if digest[4] & 1 else -1.0
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector] if any(vector) else [1.0] + [0.0] * 1023


def compare(state: dict) -> tuple[bool, dict, dict]:
    lost = {k: sorted(set(EXPECTED[k]) - set(state[k])) for k in EXPECTED}
    extra = {k: sorted(set(state[k]) - set(EXPECTED[k])) for k in EXPECTED}
    return state == EXPECTED, lost, extra


# --- graphiti-core, imported only when the repro runs ---------------------------------------------------------------


def build(backend: str):
    os.environ["GRAPHITI_TELEMETRY_ENABLED"] = "false"
    import graphiti_core.graphiti as graphiti_module
    from graphiti_core import Graphiti
    from graphiti_core.cross_encoder.client import CrossEncoderClient
    from graphiti_core.driver.falkordb_driver import FalkorDriver
    from graphiti_core.driver.neo4j_driver import Neo4jDriver
    from graphiti_core.edges import EntityEdge
    from graphiti_core.embedder.client import EmbedderClient
    from graphiti_core.errors import GroupsEdgesNotFoundError, GroupsNodesNotFoundError
    from graphiti_core.llm_client.client import LLMClient
    from graphiti_core.llm_client.config import LLMConfig, ModelSize
    from graphiti_core.nodes import EntityNode, EpisodeType, EpisodicNode
    from graphiti_core.telemetry import is_telemetry_enabled
    from graphiti_core.utils.maintenance.graph_data_operations import clear_data

    class FixtureLLM(LLMClient):
        def __init__(self):
            super().__init__(LLMConfig(api_key="unused", model="fixture", small_model="fixture"))

        async def generate_response(self, messages, response_model=None, max_tokens=None,
                                    model_size=ModelSize.medium, group_id=None, prompt_name=None, *,
                                    attribute_extraction=False, model=None):
            if prompt_name not in ANSWERS:
                raise RuntimeError(f"no fixture answer for prompt {prompt_name!r}")
            answer = ANSWERS[prompt_name]("\n".join(message.content for message in messages))
            if response_model is not None and answer:
                response_model(**answer)  # the answer must fit the schema Graphiti parses it with
            return answer

        async def _generate_response(self, *args, **kwargs):
            raise RuntimeError("answers come from generate_response only")

    class HashedEmbedder(EmbedderClient):
        async def create(self, input_data):
            return hashed_vector(input_data if isinstance(input_data, str) else " ".join(map(str, input_data)))

        async def create_batch(self, input_data_list):
            return [await self.create(text) for text in input_data_list]

    class OverlapReranker(CrossEncoderClient):
        async def rank(self, query, passages):
            words = set(query.lower().split())
            return sorted(((p, len(words & set(p.lower().split())) / (len(words | set(p.lower().split())) or 1))
                           for p in passages), key=lambda pair: (-pair[1], pair[0]))

    if is_telemetry_enabled():
        raise SystemExit("Graphiti telemetry is on; set GRAPHITI_TELEMETRY_ENABLED=false")
    driver = (FalkorDriver(host="127.0.0.1", port=16380, database=GROUP) if backend == "falkordb"
              else Neo4jDriver("bolt://127.0.0.1:17687", "neo4j", "unused"))
    graphiti = Graphiti(graph_driver=driver, llm_client=FixtureLLM(), embedder=HashedEmbedder(),
                        cross_encoder=OverlapReranker())

    async def add(tag):
        text, when, _, _ = EPISODES[tag]
        result = await graphiti.add_episode(name=tag, episode_body=f"{text} [wm:{tag}]", source_description="repro",
                                            reference_time=when, source=EpisodeType.message, group_id=GROUP)
        return result.episode.uuid

    async def reset_and_seed():
        await clear_data(graphiti.driver, [GROUP])
        await graphiti.build_indices_and_constraints()
        if backend == "falkordb":
            for _ in range(400):
                records, _, _ = await graphiti.driver.execute_query("CALL db.indexes() YIELD status RETURN status")
                if all(str(r["status"]).upper() == "OPERATIONAL" for r in records):
                    break
                await asyncio.sleep(0.05)
        else:
            await graphiti.driver.execute_query("CALL db.awaitIndexes(120)")
        await add("G8S")
        return await add("G8E")

    async def everything(kind):
        try:
            return await kind.get_by_group_ids(graphiti.driver, [GROUP])
        except (GroupsEdgesNotFoundError, GroupsNodesNotFoundError):
            return []

    async def observe():
        await settle()
        entities, facts, episodes = (await everything(EntityNode), await everything(EntityEdge),
                                     await everything(EpisodicNode))
        return {"episodes": sorted(e.name for e in episodes), "entities": sorted(e.name for e in entities),
                "facts": sorted(f"{f.fact} ({len(f.episodes or [])} episode{'s' if len(f.episodes or []) != 1 else ''})"
                                for f in facts)}

    async def close():
        await clear_data(graphiti.driver, [GROUP])
        await graphiti.close()

    return {"graphiti": graphiti, "module": graphiti_module, "add": add, "reset_and_seed": reset_and_seed,
            "observe": observe, "close": close}


async def settle():
    """Let the drivers' background index builds finish."""
    pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task() and not t.done()]
    if pending:
        await asyncio.wait(pending, timeout=30)


async def outcome(call):
    try:
        await call
        return "ok"
    except Exception as exc:  # noqa: BLE001 - an exception is a result here
        return f"{type(exc).__name__}: {exc}"[:120]


def report(label, ops, state):
    same, lost, extra = compare(state)
    print(f"{label}: remove {ops[0]}, add {ops[1]} -> {'as expected' if same else 'DIFFERENT'}")
    for key in EXPECTED:
        print(f"    {key:9s} expected {EXPECTED[key]}")
        print(f"    {'':9s} observed {state[key]}")
    if not same:
        print(f"    missing {lost}; unexpected {extra}")
    return same


async def run(backend: str, variant: str, iterations: int) -> int:
    from importlib.metadata import distribution
    dist = distribution("graphiti-core")
    origin = json.loads(dist.read_text("direct_url.json") or "{}")
    source = (f"{origin.get('url')}@{origin.get('vcs_info', {}).get('commit_id')}" if origin.get("vcs_info")
              else "a package index")
    print(f"repro_g8_held_write: backend {backend}, variant {variant}, {iterations} iterations; "
          f"graphiti-core {dist.version} from {source}")
    kit = build(backend)
    graphiti = kit["graphiti"]
    if variant == "held":
        HeldWrite().install(kit["module"], graphiti.driver)()  # fails here if a hook target is missing
    try:
        g8e = await kit["reset_and_seed"]()
        ops = [await outcome(graphiti.remove_episode(g8e)), await outcome(kit["add"]("G8N"))]
        if not report("sequential control (remove, then add)", ops, await kit["observe"]()):
            print("the sequential control did not reach the expected state; the concurrent result means nothing")
            return 2
        differing = held_count = timeouts = 0
        for i in range(1, iterations + 1):
            g8e = await kit["reset_and_seed"]()
            hold = HeldWrite() if variant == "held" else None
            undo = hold.install(kit["module"], graphiti.driver) if hold else None
            barrier = asyncio.Barrier(3)

            async def released(name, make_call):
                await barrier.wait()
                if hold:
                    hold.note(f"{name} released")
                result = await outcome(make_call())
                if hold:
                    hold.note(f"{name} returned")
                return result

            try:
                if hold:
                    hold.start()  # times are ms from here, just before the two calls are released
                tasks = [asyncio.create_task(released("remove", lambda: graphiti.remove_episode(g8e))),
                         asyncio.create_task(released("add", lambda: kit["add"]("G8N")))]
                await barrier.wait()
                ops = list(await asyncio.gather(*tasks))
            finally:
                if undo:
                    undo()
            same = report(f"concurrent {i:02d}", ops, await kit["observe"]())
            differing += not same
            if hold:
                print(f"    hold: {hold.summary()}")
                print("    order: " + ", ".join(f"{label} {ms:.1f}" for label, ms in hold.events))
                reached, done = hold.at("bulk write reached the hold"), hold.at("count done")
                held_count += reached is not None and done is not None and reached < done
                timeouts += hold.timed_out
        line = (f"{backend} {variant}: sequential control as expected; concurrent: {differing} of {iterations} "
                "iterations differed from the expected state")
        if variant == "held":
            line += (f"; the bulk write reached the hold before the count had run in {held_count} of {iterations}"
                     f"; hold timeouts {timeouts}")
        print(line)
        if timeouts:
            return 3
        return 1 if differing else 0
    finally:
        await kit["close"]()


def main(argv: list[str]) -> int:
    backend = argv[1] if len(argv) > 1 else "neo4j"
    variant = argv[2] if len(argv) > 2 else "gather"
    iterations = int(argv[3]) if len(argv) > 3 else 20
    if backend not in ("neo4j", "falkordb") or variant not in ("gather", "held"):
        print("usage: python repro_g8_held_write.py [neo4j|falkordb] [gather|held] [iterations]", file=sys.stderr)
        return 64
    return asyncio.run(run(backend, variant, iterations))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
