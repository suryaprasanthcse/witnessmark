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

- ``SummarizedContent`` (cognee 1.6.1 only, row R3): before ``summary_method`` existed, every chunk got a second
  model call, ``extract_summary`` (tasks/summarization/summarize_text.py @ eb90d03); the answer is a fixed
  string that names the chunk's tags.

Anything else is unknown and fails loudly.
"""

from __future__ import annotations

from witnessmark.stub_server import StubServer, UnknownPrompt, message_text

from .fixtures import all_docs, tags_in

SERVER: StubServer | None = None  # set in the coordinator process only
CONNECTION_TEST = 'Respond to me with the following string: "test"'


class FixtureHandler:
    def __init__(self) -> None:
        self.docs = all_docs()

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
        if title == "SummarizedContent":
            tags = [tag for tag in tags_in(user) if tag in self.docs]
            return {"summary": "Summary of " + (", ".join(tags) if tags else "an untagged chunk") + "."},                 {"prompt": "SummarizedContent", "tags": tags}
        raise UnknownPrompt(f"no handler for schema {title!r}; system prompt starts {system[:80]!r}")


def start(dim: int) -> StubServer:
    global SERVER
    SERVER = StubServer(FixtureHandler(), dim=dim).start()
    return SERVER
