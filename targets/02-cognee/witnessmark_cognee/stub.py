"""Fixture handlers for the shared stub endpoint (target blueprint section 4; master section 8).

Cognee 1.6.8 asks for structured output through litellm's ``response_format``:
for a model litellm does not list as schema-capable it takes the JSON-object path
and puts the Pydantic schema in the system prompt
(cognee/infrastructure/llm/structured_output_framework/litellm_native/native_adapter.py
L316-L386 @ 069f3cc). The core server finds the schema there and validates every
answer against it.

Prompts at v1.6.8, with the default cognify pipeline (summary_method "from_extraction"):

- the connection test (infrastructure/llm/utils.py L175-L190): plain text, answered "test";
- ``KnowledgeGraph`` extraction, once per chunk: the fixture entities and relations of
  every tagged document in the chunk. Entity ids are canonical names (ideal model).

- ``ReviewResponse``, improve's ``review_conflicts`` stage (tasks/memify/review_conflicts/review_entities.py
  L226-L233 @ 069f3cc): every ``Subject [n#]`` heading is reviewed, and the conflicts are the fixture's
  (``fixtures.SCRIPTED_CONFLICTS``, none). A subject the fixture does not name, or a stored conflict shown in the
  prompt, which the fixture cannot judge, is unknown.

- ``GlobalContextSummaryContent`` (cognee 1.6.1 only, row R3): improve's opt-in ``global_context_index`` stage
  summarises its inputs, ``Input n:`` blocks holding text summaries or earlier bucket summaries
  (tasks/memify/global_context_index/summarize.py L14-L32 @ eb90d03). As with ``SummarizedContent``, the answer is a
  fixed string naming the documents the inputs cover; an input that names no fixture document is unknown.

- ``SummarizedContent`` (cognee 1.6.1 only, row R3): before ``summary_method`` existed, every chunk got a second
  model call, ``extract_summary`` (tasks/summarization/summarize_text.py @ eb90d03); the answer is a fixed
  string that names the chunk's tags.

Anything else is unknown and fails loudly.
"""

from __future__ import annotations

import re

from witnessmark.stub_server import StubServer, UnknownPrompt, message_text

from .fixtures import SCRIPTED_CONFLICTS, all_docs, entity_keys, key, tags_in

SUBJECT = re.compile(r"^Subject \[(n\d+)\] (.*) \(types: [^)]*\)$")
INPUT = re.compile(r"^Input \d+:$", re.MULTILINE)
WORD = re.compile(r"[A-Za-z0-9_\-]+")

SERVER: StubServer | None = None  # set in the coordinator process only
CONNECTION_TEST = 'Respond to me with the following string: "test"'


class FixtureHandler:
    def __init__(self) -> None:
        self.docs = all_docs()
        self.entities = entity_keys()

    def __call__(self, body: dict, schema: dict | None):
        system, user = message_text(body, "system"), message_text(body, "user")
        if CONNECTION_TEST in system:
            return "test", {"prompt": "connection_test"}
        title = (schema or {}).get("title")
        if title == "KnowledgeGraph":
            tags = [tag for tag in tags_in(user) if tag in self.docs]
            if not tags:
                raise UnknownPrompt(f"KnowledgeGraph prompt without a known tag: {user[:120]!r}")
            nodes, edges, seen = [], [], set()
            for tag in tags:
                doc = self.docs[tag]
                for entity in doc.entities:
                    if entity.name not in seen:
                        seen.add(entity.name)
                        nodes.append({"id": entity.name, "name": entity.name, "type": entity.type,
                                      "description": f"{entity.type} {entity.name}"})
                for relation in doc.relations:
                    edges.append({"source_node_id": relation.source, "target_node_id": relation.target,
                                  "relationship_name": relation.relation,
                                  "description": f"{relation.source} {relation.relation.replace('_', ' ')} "
                                                 f"{relation.target}"})
            return {"nodes": nodes, "edges": edges}, {"prompt": "KnowledgeGraph", "tags": tags,
                                                     "nodes": len(nodes), "edges": len(edges)}
        if title == "ReviewResponse":
            return self.review(user)
        if title == "GlobalContextSummaryContent":
            return self.context_summary(user)
        if title == "SummarizedContent":
            tags = [tag for tag in tags_in(user) if tag in self.docs]
            return {"summary": "Summary of " + (", ".join(tags) if tags else "an untagged chunk") + "."},                 {"prompt": "SummarizedContent", "tags": tags}
        raise UnknownPrompt(f"no handler for schema {title!r}; system prompt starts {system[:80]!r}")


    def review(self, user: str):
        """One conflict-review call: review every subject shown, report the conflicts the fixture scripts (none)."""
        lines = (user or "").splitlines()
        subjects = [(m.group(1), m.group(2)) for m in (SUBJECT.match(line) for line in lines) if m]
        if not subjects:
            raise UnknownPrompt(f"ReviewResponse prompt without a Subject heading: {(user or '')[:120]!r}")
        unknown = [name for _label, name in subjects if key(name) not in self.entities]
        if unknown:
            raise UnknownPrompt(f"ReviewResponse prompt names subjects the fixture does not: {unknown[:5]}")
        if any(line.startswith("Existing") for line in lines):
            raise UnknownPrompt("ReviewResponse prompt shows a stored conflict, which the fixture cannot judge")
        scripted = [name for _label, name in subjects if SCRIPTED_CONFLICTS.get(key(name))]
        if scripted:
            raise UnknownPrompt(f"the fixture scripts conflicts for {scripted[:5]}, which this handler does not answer")
        return ({"reviewed": [label for label, _name in subjects], "conflicts": [], "drop": []},
                {"prompt": "ReviewResponse", "subjects": [key(name) for _label, name in subjects], "conflicts": 0})


    def documents_named(self, text: str) -> list[str]:
        """Fixture tags in a text, as ``[wm:TAG]`` or as the bare tags the stub's own summaries name."""
        found = [tag for tag in tags_in(text) if tag in self.docs]
        found += [word for word in WORD.findall(text or "") if word in self.docs and word not in found]
        return list(dict.fromkeys(found))

    def context_summary(self, user: str):
        """cognee 1.6.1's global context summary: a fixed string naming the documents its inputs cover."""
        blocks = [block.strip() for block in INPUT.split(user or "")[1:]]
        if not blocks:
            raise UnknownPrompt(f"GlobalContextSummaryContent prompt without an Input block: {(user or '')[:120]!r}")
        empty = [n for n, block in enumerate(blocks, 1) if not self.documents_named(block)]
        if empty:
            raise UnknownPrompt(f"GlobalContextSummaryContent inputs {empty[:5]} name no fixture document")
        tags = self.documents_named(user)
        return ({"summary": "Summary of " + ", ".join(tags) + "."},
                {"prompt": "GlobalContextSummaryContent", "inputs": len(blocks), "tags": tags})


def start(dim: int) -> StubServer:
    global SERVER
    SERVER = StubServer(FixtureHandler(), dim=dim).start()
    return SERVER
