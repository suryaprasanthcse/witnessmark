"""Graphiti bindings for Witnessmark's deterministic stubs (target blueprint section 4).

Each handler reads the context Graphiti rendered into its prompt and answers
the way a perfect model would, given exactly that context. Any duplicate or
temporal error that appears afterwards therefore comes from the pipeline, not
from the model. Prompts the fixtures cannot answer fail loudly.
"""

from __future__ import annotations

import ast
import json
import re

from graphiti_core.cross_encoder.client import CrossEncoderClient
from graphiti_core.embedder.client import EmbedderClient
from graphiti_core.llm_client.client import LLMClient
from graphiti_core.llm_client.config import LLMConfig, ModelSize

from witnessmark.fixtures import Fixture
from witnessmark.stubs import StubLedger, embed, overlap
from witnessmark.timing import stamp


class StubError(RuntimeError):
    pass


def section(text: str, *tags: str) -> str | None:
    """The body of the first <TAG> ... </TAG> block found, for the first tag that is present."""
    for tag in tags:
        match = re.search(rf"<{re.escape(tag)}>[ \t]*\n(.*?)\n[ \t]*</{re.escape(tag)}>", text, re.S)
        if match:
            return match.group(1).strip()
    return None


CURRENT = ("CURRENT MESSAGE", "CURRENT_MESSAGE", "CURRENT MESSAGES", "TEXT", "JSON")


def _current_episodes(fixture: Fixture, text: str):
    episodes = fixture.episodes_in(section(text, *CURRENT))
    if not episodes:
        raise StubError("the prompt's current message carries no known [wm:...] tag")
    return episodes


def extract_entities(fixture: Fixture, text: str):
    episodes = _current_episodes(fixture, text)
    seen, entities = set(), []
    for index, episode in enumerate(episodes):
        for entity in episode.entities:
            if entity.name not in seen:
                seen.add(entity.name)
                entities.append({"name": entity.name, "entity_type_id": 0, "episode_indices": [index]})
    return {"extracted_entities": entities}, {"episodes": [e.tag for e in episodes],
                                              "entities": [e["name"] for e in entities]}


def extract_edges(fixture: Fixture, text: str):
    episodes = _current_episodes(fixture, text)
    edges = [{"source_entity_name": fact.source, "target_entity_name": fact.target, "relation_type": fact.relation,
              "fact": fact.fact, "valid_at": fact.valid_at, "invalid_at": fact.invalid_at, "episode_indices": [index]}
             for index, episode in enumerate(episodes) for fact in episode.facts]
    return {"edges": edges}, {"episodes": [e.tag for e in episodes], "facts": [e["fact"] for e in edges]}


def combined_extraction(fixture: Fixture, text: str):
    """add_episode_bulk's single prompt for entities and facts (dates come from a later batch prompt)."""
    episodes = _current_episodes(fixture, text)
    entities, seen = [], set()
    for episode in episodes:
        for entity in episode.entities:
            if entity.name not in seen:
                seen.add(entity.name)
                entities.append({"name": entity.name, "entity_type_id": 0})
    facts = [{"source_entity_name": fact.source, "target_entity_name": fact.target, "relation_type": fact.relation,
              "fact": fact.fact, "episode_indices": [index]}
             for index, episode in enumerate(episodes) for fact in episode.facts]
    return {"extracted_entities": entities, "edges": facts}, {"episodes": [e.tag for e in episodes],
                                                              "facts": [f["fact"] for f in facts]}


def timestamps(fixture: Fixture, text: str):
    fact_text = section(text, "FACT")
    fact = fixture.fact(fact_text)
    answer = {"valid_at": fact.valid_at if fact else None, "invalid_at": fact.invalid_at if fact else None}
    return answer, {"fact": fact_text, "known": fact is not None, **answer}


def timestamps_batch(fixture: Fixture, text: str):
    facts = json.loads(section(text, "FACTS") or "[]")
    answers = []
    for entry in facts:
        fact = fixture.fact(entry.get("fact"))
        answers.append({"valid_at": fact.valid_at if fact else None, "invalid_at": fact.invalid_at if fact else None})
    return {"timestamps": answers}, {"facts": [entry.get("fact") for entry in facts], "answers": answers}


def dedupe_nodes(fixture: Fixture, text: str):
    entities = json.loads(section(text, "ENTITIES") or "[]")
    existing = json.loads(section(text, "EXISTING ENTITIES") or "[]")
    resolutions = []
    for entity in entities:
        key = fixture.entity_key(entity.get("name"))
        match = next((candidate["candidate_id"] for candidate in existing
                      if key is not None and fixture.entity_key(candidate.get("name")) == key), -1)
        resolutions.append({"id": entity["id"], "name": entity.get("name", ""), "duplicate_candidate_id": match})
    return {"entity_resolutions": resolutions}, {
        "entities": [entity.get("name") for entity in entities],
        "candidates": [candidate.get("name") for candidate in existing],
        "resolved_to": [resolution["duplicate_candidate_id"] for resolution in resolutions],
    }


def dedupe_node(fixture: Fixture, text: str):
    entity = json.loads(section(text, "NEW ENTITY") or "{}")
    existing = json.loads(section(text, "EXISTING ENTITIES") or "[]")
    key = fixture.entity_key(entity.get("name"))
    match = next((candidate.get("candidate_id", candidate.get("idx", -1)) for candidate in existing
                  if key is not None and fixture.entity_key(candidate.get("name")) == key), -1)
    answer = {"id": entity.get("id", 0), "name": entity.get("name", ""), "duplicate_candidate_id": match}
    return answer, {"entity": entity.get("name"), "candidates": [c.get("name") for c in existing], "resolved_to": match}


def dedupe_edges(fixture: Fixture, text: str):
    existing = ast.literal_eval(section(text, "EXISTING FACTS") or "[]")
    candidates = ast.literal_eval(section(text, "FACT INVALIDATION CANDIDATES") or "[]")
    new_text = section(text, "NEW FACT")
    new = fixture.fact(new_text)
    duplicates = [entry["idx"] for entry in existing if fixture.same_assertion(new, fixture.fact(entry["fact"]))]
    contradicted = [entry["idx"] for entry in existing + candidates
                    if fixture.contradicts(new, fixture.fact(entry["fact"]))]
    return {"duplicate_facts": duplicates, "contradicted_facts": contradicted}, {
        "new_fact": new_text,
        "existing": [entry["fact"] for entry in existing],
        "candidates": [entry["fact"] for entry in candidates],
        "duplicates": duplicates,
        "contradicted": contradicted,
    }


def no_summaries(fixture: Fixture, text: str):
    return {"summaries": []}, {}


def empty_summary(fixture: Fixture, text: str):
    return {"summary": ""}, {}


def empty_description(fixture: Fixture, text: str):
    return {"description": ""}, {}


def no_attributes(fixture: Fixture, text: str):
    return {}, {}


HANDLERS = {
    "extract_nodes.extract_message": extract_entities,
    "extract_nodes.extract_text": extract_entities,
    "extract_nodes.extract_json": extract_entities,
    "extract_edges.edge": extract_edges,
    "extract_nodes_and_edges.extract_message": combined_extraction,
    "extract_edges.extract_timestamps": timestamps,
    "extract_edges.extract_timestamps_batch": timestamps_batch,
    "dedupe_nodes.nodes": dedupe_nodes,
    "dedupe_nodes.node": dedupe_node,
    "dedupe_edges.resolve_edge": dedupe_edges,
    "extract_nodes.extract_summaries_batch": no_summaries,
    "extract_nodes.extract_entity_summaries_from_episodes": no_summaries,
    "summarize_nodes.summarize_pair": empty_summary,
    "summarize_nodes.summarize_context": empty_summary,
    "summarize_nodes.summary_description": empty_description,
    "extract_nodes.extract_attributes": no_attributes,
    "extract_edges.extract_attributes": no_attributes,
}


class StubLLM(LLMClient):
    def __init__(self, fixture: Fixture, ledger: StubLedger):
        super().__init__(LLMConfig(api_key="witnessmark-stub", model="witnessmark-stub",
                                   small_model="witnessmark-stub"))
        self.fixture = fixture
        self.ledger = ledger

    async def generate_response(self, messages, response_model=None, max_tokens=None, model_size=ModelSize.medium,
                                group_id=None, prompt_name=None, *, attribute_extraction=False, model=None):
        inv = stamp()
        name = prompt_name or (response_model.__name__ if response_model is not None else "unnamed")
        handler = HANDLERS.get(name)
        text = "\n".join(message.content for message in messages)
        if handler is None:
            raise StubError(f"no stub answer for prompt {name!r}")
        response, decision = handler(self.fixture, text)
        if response_model is not None and handler is not no_attributes:
            response_model(**response)  # the answer must fit the schema Graphiti will parse it with
        self.ledger.record(name, text, response, decision, inv)
        return response

    async def _generate_response(self, *args, **kwargs):
        raise StubError("the stub answers in generate_response only")


class StubEmbedder(EmbedderClient):
    def __init__(self, dim: int = 1024):
        self.dim = dim

    async def create(self, input_data):
        text = input_data if isinstance(input_data, str) else " ".join(str(part) for part in input_data)
        return embed(text, self.dim)

    async def create_batch(self, input_data_list):
        return [embed(text, self.dim) for text in input_data_list]


class StubReranker(CrossEncoderClient):
    async def rank(self, query, passages):
        return sorted(((passage, overlap(query, passage)) for passage in passages), key=lambda pair: (-pair[1], pair[0]))
