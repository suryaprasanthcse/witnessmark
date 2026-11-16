"""Phase D: the scripted conflict-review prompt and the C2 improve checks, with fakes and no Cognee."""

import json
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "targets" / "02-cognee"))
try:
    from witnessmark_cognee import scenarios, stub
    from witnessmark_cognee.fixtures import SCRIPTED_CONFLICTS, entity_keys
except ImportError as exc:
    raise unittest.SkipTest(f"Cognee harness helpers unavailable: {exc}") from exc

from witnessmark.history import OK, UNKNOWN, Op
from witnessmark.stub_server import StubServer, UnknownPrompt
from witnessmark.timing import Stamp

# The ReviewResponse schema as pydantic renders it at cognee 069f3cc
# (cognee/tasks/memify/review_conflicts/schema.py L20-L26).
REVIEW_SCHEMA = {
    "title": "ReviewResponse",
    "type": "object",
    "required": ["reviewed"],
    "properties": {
        "reviewed": {"type": "array", "items": {"type": "string"}, "title": "Reviewed"},
        "conflicts": {"type": "array", "items": {"$ref": "#/$defs/ReportedConflict"}, "title": "Conflicts"},
        "drop": {"type": "array", "items": {"type": "string"}, "title": "Drop"},
    },
    "$defs": {
        "ReportedConflict": {
            "type": "object", "title": "ReportedConflict",
            "required": ["about", "attribute", "kind", "text"],
            "properties": {
                "about": {"type": "string"}, "attribute": {"type": "string"},
                "kind": {"enum": ["time_varying", "fixed"], "type": "string"}, "text": {"type": "string"},
                "current": {"type": "array", "items": {"type": "string"}},
                "superseded": {"type": "array", "items": {"type": "string"}},
                "conflicting": {"type": "array", "items": {"type": "string"}},
            },
        },
    },
}

# A prompt in the shape build_review_prompt writes (build_review_prompt.py L46-L81 @ 069f3cc).
PROMPT = "\n\n".join([
    "Subject [n1] Acme Robotics (types: Organization)\n"
    "[r1] n2 --works_at--> n1 | Alice Moreau works at Acme Robotics | d1\n"
    "[r2] n3 --works_at--> n1 | Dana Petrov works at Acme Robotics | d2\n"
    "Competing relationships: r1, r2",
    "Subject [n4] Alice Moreau (types: Person)\n"
    "[r1] n4 --works_at--> n1 | Alice Moreau works at Acme Robotics | d1\n"
    "[r3] n4 --works_at--> n5 | Alice Moreau works at Cobalt Analytics | d3",
    "[n2] Alice Moreau (types: Person)\n[n3] Dana Petrov (types: Person)\n[n5] Cobalt Analytics (types: Organization)",
    "[d1] text_a.txt\n[d2] text_b.txt\n[d3] text_c.txt",
])


def _body(user: str) -> dict:
    system = ("Review the facts under each Subject.\n```json\n" + json.dumps(REVIEW_SCHEMA) + "\n```")
    return {"model": "witnessmark-stub", "messages": [{"role": "system", "content": system},
                                                       {"role": "user", "content": user}],
            "response_format": {"type": "json_object"}}


def _post(url: str, body: dict) -> tuple[int, dict]:
    request = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        with error:
            return error.code, json.loads(error.read())


class ReviewFixtureTest(unittest.TestCase):
    def setUp(self):
        self.handler = stub.FixtureHandler()

    def test_no_corpus_scripts_a_conflict(self):
        self.assertEqual(SCRIPTED_CONFLICTS, {})
        self.assertIn("acme robotics", entity_keys())

    def test_every_subject_is_reviewed_in_order_and_no_conflict_is_reported(self):
        answer, decision = self.handler(_body(PROMPT), REVIEW_SCHEMA)
        self.assertEqual(answer, {"reviewed": ["n1", "n4"], "conflicts": [], "drop": []})
        self.assertEqual(decision["subjects"], ["acme robotics", "alice moreau"])

    def test_a_subject_the_fixture_does_not_name_is_unknown(self):
        with self.assertRaises(UnknownPrompt):
            self.handler(_body("Subject [n1] Zed Unknown (types: Person)\n[r1] n1 --x--> n2 | y | d1"), REVIEW_SCHEMA)

    def test_a_prompt_without_subjects_is_unknown(self):
        with self.assertRaises(UnknownPrompt):
            self.handler(_body("[n1] Acme Robotics (types: Organization)"), REVIEW_SCHEMA)

    def test_a_stored_conflict_is_unknown(self):
        prompt = PROMPT.replace("(types: Organization)\n", "(types: Organization)\nExisting [f1] employer (subject)\n", 1)
        with self.assertRaises(UnknownPrompt):
            self.handler(_body(prompt), REVIEW_SCHEMA)

    def test_1_6_1_context_summary_names_the_documents_its_inputs_cover(self):
        schema = {"title": "GlobalContextSummaryContent", "type": "object", "required": ["summary"],
                  "properties": {"summary": {"type": "string"}}}
        user = "Input 1:\nSummary of C2B001.\n\nInput 2:\nSummary of C2B002, C2B003."
        answer, decision = self.handler(_body(user), schema)
        self.assertEqual(answer, {"summary": "Summary of C2B001, C2B002, C2B003."})
        self.assertEqual(decision["inputs"], 2)
        with self.assertRaises(UnknownPrompt):
            self.handler(_body("Input 1:\nSummary of C2B001.\n\nInput 2:\nSomething else."), schema)
        with self.assertRaises(UnknownPrompt):
            self.handler(_body("no inputs here"), schema)

    def test_over_http_the_answer_validates_and_an_unknown_prompt_gets_400(self):
        server = StubServer(stub.FixtureHandler(), dim=16).start()
        try:
            status, reply = _post(server.url + "/chat/completions", _body(PROMPT))
            self.assertEqual(status, 200)
            content = json.loads(reply["choices"][0]["message"]["content"])
            self.assertEqual(content["reviewed"], ["n1", "n4"])
            status, _reply = _post(server.url + "/chat/completions",
                                   _body("Subject [n1] Zed Unknown (types: Person)"))
            self.assertEqual(status, 400)
            ledger = server.ledger(drain=True)
            self.assertEqual([call["prompt"] for call in ledger], ["ReviewResponse", "unknown"])
        finally:
            server.stop()


def _op(k, client, entry, outcome=OK, result=None, error=None, **extra):
    inv = Stamp(1_000 + k, "2026-11-16T00:00:00.000000Z", "host")
    ret = Stamp(2_000 + k, "2026-11-16T00:00:01.000000Z", "host") if outcome != UNKNOWN else None
    return Op("run", k, "race", f"{k}-{client}-0", client, "ingest", {"group": extra.pop("group"), "entry": entry,
                                                                       **extra}, inv, ret, outcome, result, error)


def _state(scenario, tags):
    corpus = scenario.corpus
    entities = {}
    for tag in tags:
        for entity in corpus.doc(tag).entities:
            entities[" ".join(entity.name.lower().split())] = 1
    edges = {f"Entity:{k.split('|')[0]}|{k.split('|')[1]}|Entity:{k.split('|')[2]}": 1
             for k in corpus.relation_keys(tags)}
    types = {" ".join(e.type.lower().split()): 1 for t in tags for e in corpus.doc(t).entities}
    return {
        "graph": {"nodes": {"Entity": entities, "EntityType": types, "GlobalContextSummary": {"?": 9},
                            "DocumentChunk": {t: 1 for t in tags}, "TextDocument": {t: 1 for t in tags},
                            "TextSummary": {t: 1 for t in tags}},
                  "edges": edges, "orphan_edges": 0},
        "provenance": {t: sorted(" ".join(e.name.lower().split()) for e in corpus.doc(t).entities) for t in tags},
        "relational": [],
        "vector": {"Entity_name": {"max_rows_per_id": 1, "without_graph_node": 0}, "graph_nodes_without_vector": {}},
    }


def _rows(tags):
    return [{"tags": [t], "raw_exists": True, "original_exists": True} for t in tags]


STAGES_OK = [{"stage": s, "status": "skipped", "reason": "no_session_ids", "error": None, "counts": {}}
             for s in ("feedback_weights", "persist_session_qa", "persist_agent_traces", "extract_agent_context",
                       "distill_sessions", "update_user_preferences", "build_truth_subspace")] + [
    {"stage": "review_conflicts", "status": "completed", "reason": None, "error": None, "counts": {}},
    {"stage": "global_context_index", "status": "completed", "reason": None, "error": None, "counts": {}}]


class C2ImproveTest(unittest.TestCase):
    def setUp(self):
        self.s = scenarios.C2Improve()
        kept = self.s.tags[self.s.A] + self.s.tags[self.s.B]
        shared = _state(self.s, kept)
        self.states = {g: dict(shared, relational=_rows(self.s.tags[g]) if g != self.s.C else [])
                       for g in self.s.groups()}

    def ops(self, improve_result=None, improve_outcome=OK):
        return [_op(1, "c00", "add_cognify", group=self.s.A, tags=self.s.tags[self.s.A]),
                _op(1, "c01", "improve", improve_outcome,
                    result=improve_result if improve_result is not None else {"stages": STAGES_OK},
                    error=None if improve_outcome == OK else {"type": "target.X", "message": "boom"}, group=self.s.B),
                _op(1, "c02", "delete", group=self.s.C, tags=self.s.tags[self.s.C])]

    def checks(self, ops):
        return {(c.invariant, c.unit): c for c in self.s.check(ops, self.states)}

    def test_clients_and_setup_shape(self):
        entries = [item["entry"] for _group, item in self.s.clients()]
        self.assertEqual(entries, ["add_cognify", "improve", "delete"])
        self.assertIn("improve", self.s.params()["clients"]["B"])

    def test_clean_trial_holds_every_check(self):
        checks = self.s.check(self.ops(), self.states)
        self.assertTrue(all(c.held for c in checks), [c.detail for c in checks if not c.held])
        self.assertEqual(self.checks(self.ops())[("IMP", "improve stages errored")].magnitude, 0)

    def test_errored_improve_stage_with_writer_conflict_is_counted(self):
        stages = [dict(s) for s in STAGES_OK]
        stages[-1].update(status="errored", error="RuntimeError: Too many concurrent writers <- x")
        checks = self.checks(self.ops({"stages": stages}))
        imp = checks[("IMP", "improve stages errored")]
        self.assertFalse(imp.held)
        self.assertEqual(imp.witnesses, ["1-c01-0:global_context_index"])
        c2w = checks[("C2W", "operations or improve stages failed with writer conflicts")]
        self.assertFalse(c2w.held)
        self.assertEqual(c2w.magnitude, 1)

    def test_improve_that_raised_fails_imp(self):
        checks = self.checks(self.ops(improve_outcome=UNKNOWN))
        self.assertFalse(checks[("IMP", "improve stages errored")].held)

    def test_missing_b_document_breaks_i2(self):
        dropped = self.s.tags[self.s.B][0]
        for g in self.s.groups():
            self.states[g]["graph"]["nodes"]["DocumentChunk"].pop(dropped, None)
        checks = self.s.check(self.ops(), self.states)
        self.assertTrue(any(c.invariant == "I2" and not c.held for c in checks))

    def test_sequential_control_needs_both_stages_completed_and_the_rest_skipped(self):
        ok, _expected, observed = self.s.sequential_expected(self.ops(), self.states)
        self.assertTrue(ok, observed)
        stages = [dict(s) for s in STAGES_OK]
        stages[-2].update(status="already_completed", reason="no_new_facts")
        ok, _expected, observed = self.s.sequential_expected(self.ops({"stages": stages}), self.states)
        self.assertFalse(ok)
        self.assertIn("review_conflicts", observed)
        stages = [dict(s) for s in STAGES_OK]
        stages[0].update(status="completed", reason=None)
        ok, _expected, observed = self.s.sequential_expected(self.ops({"stages": stages}), self.states)
        self.assertFalse(ok)
        self.assertIn("outside the declared set", observed)

    def test_sequential_control_on_1_6_1_stage_set(self):
        stages = [s for s in STAGES_OK if s["stage"] != "review_conflicts"]
        stages.insert(-1, {"stage": "triplet_enrichment", "status": "skipped", "reason": "triplet_embedding_disabled",
                           "error": None, "counts": {}})
        ok, _expected, observed = self.s.sequential_expected(self.ops({"stages": stages}), self.states)
        self.assertTrue(ok, observed)
        for g in self.s.groups():
            self.states[g]["graph"]["nodes"]["GlobalContextSummary"] = {}
        ok, _expected, observed = self.s.sequential_expected(self.ops({"stages": stages}), self.states)
        self.assertFalse(ok)
        self.assertIn("GlobalContextSummary", observed)


if __name__ == "__main__":
    unittest.main()
