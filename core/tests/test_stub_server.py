"""The HTTP stub endpoint and its schema validator, exercised over real loopback sockets."""

import json
import math
import unittest
import urllib.error
import urllib.request

from witnessmark.stub_server import (SchemaError, StubServer, UnknownPrompt, message_text, request_schema,
                                     validate)

GRAPH_SCHEMA = {
    "title": "KnowledgeGraph",
    "type": "object",
    "properties": {
        "nodes": {"type": "array", "items": {"$ref": "#/$defs/Node"}},
        "edges": {"type": "array", "items": {"$ref": "#/$defs/Edge"}},
    },
    "$defs": {
        "Node": {"type": "object", "required": ["id", "type", "description"],
                 "properties": {"id": {"type": "string"}, "name": {"type": "string"},
                                "type": {"type": "string"}, "description": {"type": "string"}}},
        "Edge": {"type": "object", "required": ["source_node_id", "target_node_id", "relationship_name"],
                 "properties": {"source_node_id": {"type": "string"}, "target_node_id": {"type": "string"},
                                "relationship_name": {"type": "string"},
                                "description": {"anyOf": [{"type": "string"}, {"type": "null"}]}}},
    },
}


def _post(url: str, body: dict) -> tuple[int, dict]:
    request = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read())


class ValidatorTest(unittest.TestCase):
    def test_accepts_a_valid_graph(self):
        validate({"nodes": [{"id": "alice", "type": "Person", "description": "x"}],
                  "edges": [{"source_node_id": "alice", "target_node_id": "acme", "relationship_name": "works_at",
                             "description": None}]}, GRAPH_SCHEMA)

    def test_rejects_missing_required_and_wrong_types(self):
        with self.assertRaises(SchemaError):
            validate({"nodes": [{"id": "alice", "type": "Person"}]}, GRAPH_SCHEMA)
        with self.assertRaises(SchemaError):
            validate({"nodes": "alice"}, GRAPH_SCHEMA)
        with self.assertRaises(SchemaError):
            validate({"edges": [{"source_node_id": "a", "target_node_id": "b", "relationship_name": "r",
                                 "description": 3}]}, GRAPH_SCHEMA)

    def test_additional_properties_false_and_enum(self):
        schema = {"type": "object", "properties": {"a": {"enum": ["x", "y"]}}, "additionalProperties": False}
        validate({"a": "x"}, schema)
        with self.assertRaises(SchemaError):
            validate({"a": "z"}, schema)
        with self.assertRaises(SchemaError):
            validate({"a": "x", "b": 1}, schema)

    def test_schema_found_in_response_format_or_system_prompt(self):
        body = {"response_format": {"type": "json_schema", "json_schema": {"name": "g", "schema": GRAPH_SCHEMA}},
                "messages": []}
        self.assertEqual(request_schema(body)["title"], "KnowledgeGraph")
        fenced = {"messages": [{"role": "system", "content": "Extract.\n```json\n" + json.dumps(GRAPH_SCHEMA)
                                + "\n```\nNothing else."}, {"role": "user", "content": "text [wm:D01]"}]}
        self.assertEqual(request_schema(fenced)["title"], "KnowledgeGraph")
        self.assertEqual(message_text(fenced, "user"), "text [wm:D01]")
        self.assertIsNone(request_schema({"messages": [{"role": "user", "content": "hi"}]}))


class ServerTest(unittest.TestCase):
    def setUp(self):
        def handler(body, schema):
            user = message_text(body, "user")
            if "[wm:D01]" in user:
                return {"nodes": [{"id": "alice", "type": "Person", "description": "Alice"}], "edges": []}, \
                    {"prompt": "graph", "tags": ["D01"]}
            if "[wm:BAD]" in user:
                return {"nodes": [{"id": "alice"}]}, {"prompt": "graph", "tags": ["BAD"]}
            raise UnknownPrompt("no tag")

        self.server = StubServer(handler, dim=16).start()

    def tearDown(self):
        self.server.stop()

    def test_chat_answers_from_the_fixture_and_logs_the_call(self):
        status, payload = _post(self.server.url + "/chat/completions", {
            "model": "openai/witnessmark-stub", "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": "```json\n" + json.dumps(GRAPH_SCHEMA) + "\n```"},
                         {"role": "user", "content": "Alice [wm:D01]"}]})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(payload["choices"][0]["message"]["content"])["nodes"][0]["id"], "alice")
        calls = _get(self.server.url.replace("/v1", "") + "/_wm/ledger?drain=1")["calls"]
        self.assertEqual([c["decision"]["tags"] for c in calls], [["D01"]])
        self.assertEqual(self.server.ledger(), [])

    def test_unknown_prompt_and_schema_breaking_answer_fail_loudly(self):
        status, _ = _post(self.server.url + "/chat/completions", {"messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(status, 400)
        status, _ = _post(self.server.url + "/chat/completions", {
            "messages": [{"role": "system", "content": "```json\n" + json.dumps(GRAPH_SCHEMA) + "\n```"},
                         {"role": "user", "content": "[wm:BAD]"}]})
        self.assertEqual(status, 500)
        self.assertEqual(self.server.unknown, 2)
        self.assertTrue(all("error" in call["decision"] for call in self.server.ledger()))

    def test_embeddings_are_deterministic_and_sized(self):
        status, payload = _post(self.server.url + "/embeddings", {"model": "m", "input": ["Alice works", "Alice works"]})
        self.assertEqual(status, 200)
        first, second = (item["embedding"] for item in payload["data"])
        self.assertEqual(first, second)
        self.assertEqual(len(first), 16)
        self.assertAlmostEqual(math.sqrt(sum(v * v for v in first)), 1.0, places=6)
        status, _ = _post(self.server.url + "/embeddings", {"model": "m", "input": "x", "dimensions": 8})
        self.assertEqual(status, 400)

    def test_binds_to_loopback_only(self):
        with self.assertRaises(ValueError):
            StubServer(lambda body, schema: ("", {}), host="0.0.0.0")


if __name__ == "__main__":
    unittest.main()
