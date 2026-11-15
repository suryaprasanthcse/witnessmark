"""M5 Phase B: one actor per client, HTTP 429 as a typed refusal, and the typed-refusal race check."""

from __future__ import annotations

import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

TARGET = Path(__file__).resolve().parents[2] / "targets" / "03-omnigraph"
sys.path.insert(0, str(TARGET))

from witnessmark.history import FAIL, OK, UNKNOWN, Op  # noqa: E402
from witnessmark.timing import stamp  # noqa: E402

import wm_omnigraph as cli  # noqa: E402
from witnessmark_omnigraph import actors, part2  # noqa: E402
from witnessmark_omnigraph.client import OmnigraphClient, Outcome  # noqa: E402
from witnessmark_omnigraph.engine import OmnigraphEngine  # noqa: E402
from witnessmark_omnigraph.runner_scenarios import TASK, ClaimScenario, MergeScenario  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


class _Admission(BaseHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass

    def do_POST(self):  # noqa: N802 - http.server naming
        self.server.seen.append(self.headers.get("Authorization"))
        body = json.dumps({"error": "actor in-flight count cap 16 exceeded", "code": "too_many_requests"}).encode()
        self.send_response(429)
        self.send_header("Retry-After", "1")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _op(i: int, outcome: str, kind: str | None = None) -> Op:
    now = stamp()
    error = {"type": kind, "message": "m"} if kind is not None else None
    return Op("r", 1, "race", f"1-c{i:02d}-0", f"c{i:02d}", "claim", {"agent": f"c{i:02d}"}, now,
              None if outcome == UNKNOWN else now, outcome, error=error)


def _state(holders: list[str]) -> dict:
    return {"snapshot": "s", "holders": {TASK: holders},
            "lease_records": [{"id": f"lease-{h}", "task": TASK, "agent": h, "from_seq": 1, "until_seq": None}
                              for h in holders]}


class AdmissionLimitTest(unittest.TestCase):
    def test_http_429_is_a_definite_admission_limit_refusal_and_sends_the_token(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Admission)
        server.seen = []
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            client = OmnigraphClient(f"http://127.0.0.1:{server.server_address[1]}", bearer_token="wmtok-x")
            result = client.mutate("insert", {})
        finally:
            server.shutdown()
            server.server_close()
        self.assertIs(result.outcome, Outcome.REFUSAL)
        self.assertEqual(result.kind, "admission_limit")
        self.assertEqual(server.seen, ["Bearer wmtok-x"])


class TypedRefusalCheckTest(unittest.TestCase):
    def test_every_typed_refusal_is_accepted_and_counted_per_type(self):
        ops = [_op(0, OK), _op(1, FAIL, "admission_limit"), _op(2, FAIL, "admission_limit"),
               _op(3, FAIL, "precondition_failure"), _op(4, FAIL, "CardinalityViolation"), _op(5, FAIL, "conflict")]
        check = ClaimScenario(True).check(ops, _state(["c00"]), 6)
        self.assertTrue(check.held)
        self.assertIn("refusals by type: admission_limit 2; CardinalityViolation 1; conflict 1; "
                      "precondition_failure 1", check.detail)

    def test_a_second_winner_a_second_holder_or_a_lost_write_fails(self):
        scenario = ClaimScenario(True)
        self.assertFalse(scenario.check([_op(0, OK), _op(1, OK)], _state(["c00"]), 2).held)
        self.assertFalse(scenario.check([_op(0, OK), _op(1, FAIL, "admission_limit")],
                                        _state(["c00", "c01"]), 2).held)
        lost = scenario.check([_op(0, OK), _op(1, FAIL, "precondition_failure")], _state([]), 2)
        self.assertFalse(lost.held)
        self.assertIn("does not hold", lost.detail)

    def test_an_untyped_refusal_fails_and_an_unknown_outcome_fails_only_if_it_could_have_applied(self):
        scenario = ClaimScenario(False)
        for kind in ("refusal", "http_400", ""):
            self.assertFalse(scenario.check([_op(0, OK), _op(1, FAIL, kind)], _state(["c00"]), 2).held, kind)
        # The final state shows the unknown claim did not apply: one acknowledged winner holds the lease.
        self.assertTrue(scenario.check([_op(0, OK), _op(1, UNKNOWN, "connection")], _state(["c00"]), 2).held)
        # No acknowledged winner and the holder is not one of the unknown claimants.
        self.assertFalse(scenario.check([_op(0, FAIL, "admission_limit"), _op(1, UNKNOWN, "connection")],
                                        _state(["c00"]), 2).held)

    def test_the_sequential_control_still_requires_the_documented_refusal(self):
        scenario = ClaimScenario(True)
        documented = [_op(0, OK), _op(1, FAIL, "precondition_failure")]
        other = [_op(0, OK), _op(1, FAIL, "admission_limit")]
        self.assertTrue(scenario.sequential_expected(documented, _state(["c00"]), 2)[0])
        self.assertFalse(scenario.sequential_expected(other, _state(["c00"]), 2)[0])

    def test_merge_accepts_typed_refusals_but_not_two_holders(self):
        scenario = MergeScenario()
        ops = [_op(0, OK), _op(1, FAIL, "admission_limit"), _op(2, FAIL, "CardinalityViolation")]
        self.assertTrue(scenario.check(ops, _state(["c00"]), 3).held)
        self.assertFalse(scenario.check(ops, _state(["c00", "c01"]), 3).held)


class PerClientActorTest(unittest.TestCase):
    def test_the_checked_in_policy_names_every_actor(self):
        self.assertEqual(actors.policy_path(REPO).read_text(encoding="utf-8"), actors.policy_text())
        self.assertEqual(len(actors.all_actors()), 51)
        config = (REPO / "targets" / "03-omnigraph" / "workload" / actors.CLUSTER_CONFIG).read_text(encoding="utf-8")
        self.assertIn(f"file: {actors.POLICY_FILE}", config)

    def test_tokens_are_distinct_and_never_described(self):
        tokens = actors.make_tokens(50)
        self.assertEqual([actor for actor, _ in tokens][:3], ["wm-admin", "wm-c00", "wm-c01"])
        self.assertEqual(len({token for _, token in tokens}), 51)
        described = json.dumps(actors.describe(tokens))
        self.assertNotIn(tokens[1][1], described)
        self.assertEqual(actors.describe(tokens)["client_actors"][-1], "wm-c49")
        with self.assertRaises(ValueError):
            actors.make_tokens(51)

    def test_engine_hands_the_admin_then_each_client_its_own_token(self):
        tokens = actors.make_tokens(3)
        engine = OmnigraphEngine("http://127.0.0.1:18080", "v0.15.0", "img", "sha256:x", actor_tokens=tokens)
        sessions = [engine.session() for _ in range(4)]
        self.assertEqual([s.actor for s in sessions], ["wm-admin", "wm-c00", "wm-c01", "wm-c02"])
        self.assertEqual([s.client.bearer_token for s in sessions], [token for _, token in tokens])
        self.assertEqual(engine.describe()["config"]["actors"]["mode"], "per-client")

    def test_stack_adds_the_override_tokens_and_policy_config(self):
        tokens = actors.make_tokens(2)
        stack = part2.Stack(REPO, "wm-unit", {"image": "i", "digest": "sha256:d"}, "local", actor_tokens=tokens)
        self.assertEqual([path.name for path in stack.compose_files], ["compose.yml", "compose.actors.yml"])
        self.assertEqual(json.loads(stack.environ["WM_OMNIGRAPH_TOKENS_JSON"]), dict(tokens))
        self.assertTrue(stack.environ["WM_OMNIGRAPH_CLUSTER_CONFIG"].endswith(actors.CLUSTER_CONFIG))
        plain = part2.Stack(REPO, "wm-unit", {"image": "i", "digest": "sha256:d"}, "local")
        self.assertEqual([path.name for path in plain.compose_files], ["compose.yml"])
        self.assertNotIn("WM_OMNIGRAPH_TOKENS_JSON", plain.environ)

    def test_race_defaults_to_per_client_actors_when_it_provisions(self):
        manifest = {"scenario": {"id": "o2"}, "verdicts": [{"status": "PASS"}], "path": "fake"}
        with mock.patch.object(cli, "run", return_value=manifest) as run, mock.patch("builtins.print"):
            cli.main(["race", "--build", "v0.15.0", "--scenario", "o2a", "--provision"])
            self.assertEqual(len(run.call_args.args[0].engine.actor_tokens), 51)
            cli.main(["race", "--build", "v0.15.0", "--scenario", "o2a", "--provision", "--actors", "shared"])
            self.assertIsNone(run.call_args.args[0].engine.actor_tokens)


if __name__ == "__main__":
    unittest.main()
