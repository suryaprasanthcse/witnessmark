"""Offline coverage of the O2b cost curve: the retry policy, the metrics, the holder check and the runs."""

import json
import random
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from witnessmark.adapters.base import EngineError, EngineUnavailable, Reply
from witnessmark.history import FAIL, OK, UNKNOWN, validate_history
from witnessmark.timing import Stamp

TARGET = Path(__file__).resolve().parents[2] / "targets" / "03-omnigraph"
sys.path.insert(0, str(TARGET))

import wm_omnigraph as cli  # noqa: E402
from witnessmark_omnigraph import costcurve as cc  # noqa: E402
from witnessmark_omnigraph.capture import OperationCapture  # noqa: E402
from witnessmark_omnigraph.client import OperationResult, Outcome  # noqa: E402

WALL = "2026-11-16T12:00:00.000000Z"
BUILD = {"image": "local/server", "digest": "sha256:abc"}
PRECONDITION = {"type": "precondition_failure", "message": "graph commit moved", "code": 409}


def at(ms: float) -> Stamp:
    return Stamp(int(ms * 1e6), WALL)


def step(kind, start, end, outcome=OK, error=None, token=None, is_open=True):
    return cc.Step(kind, {}, at(start), None if outcome == UNKNOWN else at(end), outcome, error=error,
                   token=token, is_open=is_open)


class ScriptedAgent:
    """Reads and claims that return a fixed script of outcomes, counting what was asked."""

    def __init__(self, claims, reads=None):
        self.claims = list(claims)
        self.reads = list(reads or [])
        self.read_calls = 0
        self.claim_commits = []
        self.tick = 0

    def read(self, attempt):
        self.read_calls += 1
        self.tick += 1
        if self.reads:
            return self.reads.pop(0)
        return step("read", self.tick, self.tick + 0.5, token=f"commit-{attempt}")

    def claim(self, commit, attempt):
        self.claim_commits.append(commit)
        self.tick += 1
        outcome = self.claims.pop(0)
        if outcome == OK:
            return step("claim", self.tick, self.tick + 1)
        if outcome == UNKNOWN:
            return step("claim", self.tick, 0, UNKNOWN, {"type": "unavailable.timeout", "message": "t"})
        return step("claim", self.tick, self.tick + 1, FAIL, outcome)


class RetryPolicyTest(unittest.TestCase):
    def test_re_reads_after_each_precondition_failure_and_resubmits_the_new_commit(self):
        agent = ScriptedAgent([PRECONDITION, PRECONDITION, OK])
        run = cc.drive_agent("c03", agent.read, agent.claim)
        self.assertEqual((run.status, run.attempts, agent.read_calls), ("claimed", 3, 3))
        self.assertEqual(agent.claim_commits, ["commit-1", "commit-2", "commit-3"])
        self.assertEqual([item.kind for item in run.steps], ["read", "claim"] * 3)

    def test_the_cap_is_200_claim_submissions_and_there_is_no_read_after_the_last(self):
        self.assertEqual(cc.MAX_ATTEMPTS, 200)
        agent = ScriptedAgent([PRECONDITION] * 500)
        run = cc.drive_agent("c00", agent.read, agent.claim)
        self.assertEqual((run.status, run.attempts), ("capped", 200))
        self.assertEqual((len(agent.claim_commits), agent.read_calls), (200, 200))
        self.assertEqual(run.steps[-1].kind, "claim")

    def test_a_cap_below_the_default_is_honoured_and_a_win_on_the_last_attempt_counts(self):
        agent = ScriptedAgent([PRECONDITION, PRECONDITION, OK])
        self.assertEqual(cc.drive_agent("c00", agent.read, agent.claim, cap=3).status, "claimed")
        agent = ScriptedAgent([PRECONDITION] * 3)
        self.assertEqual(cc.drive_agent("c00", agent.read, agent.claim, cap=2).status, "capped")

    def test_any_other_refusal_ends_the_agent_without_a_retry(self):
        refusal = {"type": "CardinalityViolation", "message": "card"}
        agent = ScriptedAgent([refusal, OK])
        run = cc.drive_agent("c00", agent.read, agent.claim)
        self.assertEqual((run.status, run.attempts, agent.read_calls), ("refused", 1, 1))

    def test_an_unknown_outcome_ends_the_agent_and_is_not_retried(self):
        agent = ScriptedAgent([UNKNOWN, OK])
        run = cc.drive_agent("c00", agent.read, agent.claim)
        self.assertEqual((run.status, run.attempts), ("unknown", 1))
        self.assertIsNone(run.steps[-1].ret)

    def test_the_read_decides_again(self):
        failed = step("read", 1, 2, FAIL, {"type": "http_500", "message": "x"})
        run = cc.drive_agent("c00", ScriptedAgent([], [failed]).read, ScriptedAgent([OK]).claim)
        self.assertEqual((run.status, run.attempts), ("read_failed", 0))
        unknown = step("read", 1, 0, UNKNOWN, {"type": "unavailable.timeout", "message": "x"})
        self.assertEqual(cc.drive_agent("c00", ScriptedAgent([], [unknown]).read, ScriptedAgent([OK]).claim).status,
                         "unknown")
        closed = step("read", 1, 2, token="commit-1", is_open=False)
        run = cc.drive_agent("c00", ScriptedAgent([], [closed]).read, ScriptedAgent([OK]).claim)
        self.assertEqual((run.status, run.attempts), ("not_open", 0))
        missing = step("read", 1, 2, token=None)
        self.assertEqual(cc.drive_agent("c00", ScriptedAgent([], [missing]).read, ScriptedAgent([OK]).claim).status,
                         "no_commit_id")

    def test_a_claim_with_its_own_guard_needs_no_read(self):
        agent = ScriptedAgent([OK])
        run = cc.drive_agent("c00", None, agent.claim)
        self.assertEqual((run.status, run.attempts, agent.claim_commits), ("claimed", 1, [None]))
        guard = {"type": "guard_false", "message": "not open"}
        self.assertEqual(cc.drive_agent("c00", None, ScriptedAgent([guard]).claim).status, "refused")


class FakeClient:
    """A scripted OmnigraphClient: records the requests and answers from a queue."""

    def __init__(self, reads, claims):
        self.reads, self.claims = list(reads), list(claims)
        self.calls = []

    def query(self, query, params=None, *, name=None, **kw):
        self.calls.append(("query", name, params))
        return self.reads.pop(0)

    def mutate(self, query, params=None, *, name=None, commit_id=None, **kw):
        self.calls.append(("mutate", name, params, commit_id))
        return self.claims.pop(0)


def read_result(commit, state="open"):
    return OperationResult(Outcome.OK, 200, data={"graph_commit_id": commit, "columns": ["task", "state"],
                                                  "rows": [{"task": "task-3", "state": state}]})


class OmnigraphAgentTest(unittest.TestCase):
    QUERIES = {"q_task": "Q", "m_claim_cond": "M"}

    def test_claims_its_own_task_on_the_commit_it_read_and_records_the_refusal_type(self):
        refusal = OperationResult(Outcome.REFUSAL, 409, "precondition_failure", {"precondition_failure": {}}, "moved")
        win = OperationResult(Outcome.OK, 200, data={"commit": {"graph_commit_id": "g9"}})
        client = FakeClient([read_result("g1"), read_result("g4")], [refusal, win])
        run = cc.omnigraph_agent(client, self.QUERIES, 3)
        self.assertEqual((run.status, run.attempts), ("claimed", 2))
        claims = [call for call in client.calls if call[0] == "mutate"]
        self.assertEqual([call[3] for call in claims], ["g1", "g4"])
        self.assertEqual(claims[0][2], {"task_id": "task-3", "agent_id": "c03", "from_seq": 4,
                                        "until_pt": 9_223_372_036_854_775_807, "rw": "lease-03"})
        first, second = run.steps[1], run.steps[3]
        self.assertEqual((first.outcome, first.error_type, first.error["code"]), (FAIL, "precondition_failure", 409))
        self.assertEqual((second.outcome, second.token, second.result), (OK, "g9", {"won": 1, "commit": "g9"}))
        self.assertEqual(run.steps[0].token, "g1")
        self.assertEqual(run.steps[1].inputs["if_graph_commit"], "g1")

    def test_a_task_no_longer_open_ends_the_agent_after_the_read(self):
        client = FakeClient([read_result("g1", state="claimed")], [])
        run = cc.omnigraph_agent(client, self.QUERIES, 3)
        self.assertEqual((run.status, run.attempts), ("not_open", 0))

    def test_a_timeout_is_an_unknown_outcome_with_no_return_time(self):
        timeout = OperationResult(Outcome.UNKNOWN, None, "timeout", None, "timed out")
        run = cc.omnigraph_agent(FakeClient([read_result("g1")], [timeout]), self.QUERIES, 0)
        self.assertEqual(run.status, "unknown")
        self.assertEqual((run.steps[-1].outcome, run.steps[-1].ret), (UNKNOWN, None))

    def test_falkordb_agent_sends_the_naive_claim_once(self):
        session = mock.Mock()
        session.run.return_value = Reply(["won"], [[1]])
        run = cc.falkordb_agent(session, 7)
        query, params = session.run.call_args.args
        self.assertEqual(params, {"task": "task-7", "agent": "c07"})
        self.assertIn("WHERE t.state = 'open'", query)
        self.assertEqual((run.status, run.attempts, len(run.steps)), ("claimed", 1, 1))
        session.run.return_value = Reply(["won"], [[0]])
        self.assertEqual(cc.falkordb_agent(session, 7).steps[0].error_type, "guard_false")
        session.run.side_effect = EngineError("falkordb.error", "bad")
        self.assertEqual(cc.falkordb_agent(session, 7).status, "refused")
        session.run.side_effect = EngineUnavailable("timeout", "late")
        self.assertEqual(cc.falkordb_agent(session, 7).status, "unknown")


def finished(client, attempts, status, start, claim_end, claim_ms=1.0):
    run = cc.AgentRun(client, [], attempts, status)
    run.steps = [step("read", start, start + 1, token="g"), step("claim", start + 1, claim_end)]
    return run


class MetricsTest(unittest.TestCase):
    def test_attempts_wasted_medians_times_and_latencies(self):
        # Three agents; attempts 1, 2 and 6; every task claimed.
        runs = [finished("c00", 1, "claimed", 0, 3), finished("c01", 2, "claimed", 2, 10),
                finished("c02", 6, "claimed", 4, 20)]
        runs[2].steps.append(step("claim", 21, 50))  # the last claim answers at 50 ms
        metrics = cc.trial_metrics(runs)
        self.assertEqual((metrics["attempts_total"], metrics["claimed"], metrics["wasted_attempts"]), (9, 3, 6))
        self.assertEqual((metrics["agent_attempts"], metrics["agent_attempts_median"],
                          metrics["agent_attempts_max"]), ([1, 2, 6], 2, 6))
        self.assertEqual(metrics["release_spread_ms"], 4.0)
        self.assertEqual(metrics["time_to_all_claimed_ms"], 50.0)
        self.assertEqual(metrics["agent_status"], {"claimed": 3})
        self.assertEqual(metrics["claim_latency_ms"]["n"], 4)
        self.assertEqual(metrics["read_latency_ms"], {"n": 3, "p50": 1.0, "p99": 1.0})
        self.assertEqual((metrics["operations"], metrics["unknown_operations"]), (7, 0))

    def test_time_to_all_claimed_needs_every_agent_to_claim(self):
        runs = [finished("c00", 1, "claimed", 0, 3), finished("c01", 200, "capped", 0, 9)]
        metrics = cc.trial_metrics(runs)
        self.assertIsNone(metrics["time_to_all_claimed_ms"])
        self.assertEqual(metrics["wasted_attempts"], 200)
        self.assertEqual(metrics["time_to_last_event_ms"], 9.0)

    def test_percentiles_are_over_claim_submissions(self):
        run = cc.AgentRun("c00", [step("claim", 0, ms) for ms in range(1, 101)], 100, "capped")
        latency = cc.trial_metrics([run])["claim_latency_ms"]
        self.assertEqual(latency["n"], 100)
        self.assertAlmostEqual(latency["p50"], 50.5)
        self.assertAlmostEqual(latency["p99"], 99.01)

    def test_unknown_operations_are_counted_and_have_no_latency(self):
        run = cc.AgentRun("c00", [step("claim", 0, 5), step("claim", 6, 0, UNKNOWN)], 2, "unknown")
        metrics = cc.trial_metrics([run])
        self.assertEqual((metrics["unknown_operations"], metrics["claim_latency_ms"]["n"]), (1, 1))


def observed(*pairs):
    return {"tasks": [{"task": f"task-{i}", "state": "claimed" if holders else "open", "holders": holders}
                      for i, holders in enumerate(pairs)]}


class HolderCheckTest(unittest.TestCase):
    def runs(self, *statuses):
        return [cc.AgentRun(cc.client_name(i), [], 1, status) for i, status in enumerate(statuses)]

    def test_every_task_held_by_its_own_agent_passes(self):
        result = cc.check_holders(self.runs("claimed", "claimed"), observed(["c00"], ["c01"]))
        self.assertEqual(result, {"held": True, "violations": []})

    def test_wrong_or_extra_holders_are_violations(self):
        result = cc.check_holders(self.runs("claimed", "claimed"), observed(["c01"], ["c01", "c00"]))
        self.assertFalse(result["held"])
        self.assertEqual(len(result["violations"]), 2)

    def test_an_unfinished_agent_holds_nothing_but_an_unknown_one_may(self):
        self.assertTrue(cc.check_holders(self.runs("capped"), observed([]))["held"])
        self.assertFalse(cc.check_holders(self.runs("capped"), observed(["c00"]))["held"])
        self.assertTrue(cc.check_holders(self.runs("unknown"), observed(["c00"]))["held"])
        self.assertTrue(cc.check_holders(self.runs("unknown"), observed([]))["held"])
        self.assertFalse(cc.check_holders(self.runs("unknown", "capped"), observed(["c01"], ["c00"]))["held"])

    def test_an_acknowledged_claim_that_is_not_held_is_a_violation(self):
        self.assertFalse(cc.check_holders(self.runs("claimed"), observed([]))["held"])

    def test_a_missing_task_is_reported(self):
        self.assertIn("not found", cc.check_holders(self.runs("claimed"), {"tasks": []})["violations"][0])


class TrialAndSweepTest(unittest.TestCase):
    def evaluate(self, runs, **overrides):
        values = dict(faults=[], hung=False, healthy_before=True, healthy_after=True, precondition_ok=True,
                      observed=observed(*[[run.client] for run in runs]), gate_ms=None)
        values.update(overrides)
        return cc.evaluate_trial(1, len(runs), 0, False, runs, **values)

    def good(self, n=2):
        return [finished(cc.client_name(i), 1, "claimed", i * 5, 20) for i in range(n)]

    def test_a_clean_trial_is_valid_and_carries_the_holder_check(self):
        trial = self.evaluate(self.good())
        self.assertTrue(trial["valid"])
        self.assertEqual((trial["holders_ok"], trial["violations"], trial["warmup"], trial["n"]), (True, [], False, 2))
        self.assertNotIn("invalid_reason", trial)

    def test_each_validity_gate_invalidates_with_a_reason(self):
        for name, extra, text in (
                ("health before", {"healthy_before": False}, "unhealthy before"),
                ("health after", {"healthy_after": False}, "unhealthy after"),
                ("precondition", {"precondition_ok": False}, "precondition digest"),
                ("hung", {"hung": True}, "still running"),
                ("fault", {"faults": ["c00 raised ValueError: x"]}, "client fault"),
        ):
            with self.subTest(name):
                trial = self.evaluate(self.good(), **extra)
                self.assertFalse(trial["valid"])
                self.assertIn(text, trial["invalid_reason"])

    def test_the_spread_gate_is_off_unless_set(self):
        runs = [finished("c00", 1, "claimed", 0, 20), finished("c01", 1, "claimed", 100, 120)]
        self.assertTrue(self.evaluate(runs, gate_ms=None)["valid"])
        self.assertFalse(self.evaluate(runs, gate_ms=40.0)["valid"])
        self.assertIn("release spread", self.evaluate(runs, gate_ms=40.0)["invalid_reason"])
        self.assertTrue(self.evaluate(runs, gate_ms=200.0)["valid"])
        self.assertEqual(cc.spread_gate(None)["state"], "off")
        self.assertEqual(cc.spread_gate(None)["gate_ms"], None)
        self.assertEqual(cc.spread_gate(40.0), {"state": "on", "gate_ms": 40.0})

    def test_more_than_five_percent_unknown_operations_invalidate(self):
        runs = self.good(1)
        runs[0].steps = [step("claim", 0, 1)] * 9 + [step("claim", 2, 0, UNKNOWN)]
        runs[0].status = "claimed"
        self.assertFalse(self.evaluate(runs)["valid"])
        runs[0].steps = [step("claim", 0, 1)] * 20 + [step("claim", 2, 0, UNKNOWN)]
        self.assertTrue(self.evaluate(runs)["valid"])

    def test_a_holder_violation_is_a_finding_with_its_run_id(self):
        runs = self.good()
        trial = self.evaluate(runs, observed=observed(["c01"], ["c01"]))
        self.assertFalse(trial["holders_ok"])
        found = cc.findings_for("RUN-ID", [trial, self.evaluate(self.good())])
        self.assertEqual(len(found), 1)
        self.assertEqual((found[0]["run_id"], found[0]["k"], found[0]["kind"]), ("RUN-ID", 1, "holder_violation"))

    def trial(self, n, warmup, valid, attempts):
        return {"n": n, "warmup": warmup, "valid": valid, "attempts_total": attempts,
                "wasted_attempts": attempts - n, "agent_attempts_median": 1, "agent_attempts_max": attempts - n + 1,
                "time_to_all_claimed_ms": float(attempts), "release_spread_ms": 1.0,
                "claim_latency_ms": {"p50": 2.0, "p99": 3.0}, "violations": []}

    def test_summaries_exclude_warm_ups_and_invalid_trials_and_report_medians_and_iqr(self):
        trials = [self.trial(2, True, True, 999), self.trial(2, False, True, 2), self.trial(2, False, True, 4),
                  self.trial(2, False, True, 6), self.trial(2, False, True, 8), self.trial(2, False, False, 500),
                  self.trial(1, False, True, 1)]
        rows = {row["n"]: row for row in cc.summarize_sweep(trials, (1, 2))}
        two = rows[2]
        self.assertEqual((two["measured_repetitions"], two["valid_repetitions"], two["invalid_repetitions"]),
                         (5, 4, 1))
        self.assertEqual((two["attempts_total"]["median"], two["attempts_total"]["q1"], two["attempts_total"]["q3"]),
                         (5, 3.5, 6.5))
        self.assertEqual(two["wasted_attempts"]["n"], 4)
        self.assertEqual(two["claim_latency_p99_ms"]["median"], 3.0)
        self.assertEqual(rows[1]["wasted_attempts"]["median"], 0)

    def test_the_declared_sweep_and_protocol(self):
        plan = cc.sweep_plan(False)
        self.assertEqual((plan["agents"], plan["warmups"], plan["measured_repetitions"], plan["max_attempts"]),
                         ([1, 2, 5, 10, 25, 50], 3, 5, 200))
        smoke = cc.sweep_plan(True)
        self.assertEqual((smoke["agents"], smoke["warmups"], smoke["measured_repetitions"]), ([1, 2], 1, 1))
        order = list(cc.rounds(cc.sweep_plan(False)))
        self.assertEqual(len(order), 6 * 8)
        self.assertEqual(order[:7], [(0, 1, True), (0, 2, True), (0, 5, True), (0, 10, True), (0, 25, True),
                                     (0, 50, True), (1, 1, True)])
        self.assertEqual(sum(1 for _, _, warm in order if warm), 6 * 3)
        self.assertEqual(list(cc.rounds(smoke)), [(0, 1, True), (0, 2, True), (1, 1, False), (1, 2, False)])


class RaceTest(unittest.TestCase):
    def test_agents_are_released_together_and_the_runs_come_back(self):
        released = []

        def work(i):
            released.append(i)
            return cc.AgentRun(cc.client_name(i), [], 0, "claimed")

        runs, faults, hung = cc.race_agents(5, lambda i: None, work, rng=random.Random(1), timeout_s=5)
        self.assertEqual((len(runs), faults, hung), (5, [], False))
        self.assertEqual(sorted(released), [0, 1, 2, 3, 4])

    def test_a_warm_up_failure_is_a_fault_and_nobody_acts(self):
        def warm(i):
            if i == 2:
                raise OSError("no route")

        acted = []
        runs, faults, hung = cc.race_agents(4, warm, lambda i: acted.append(i), rng=random.Random(1), timeout_s=5)
        self.assertEqual((runs, acted), ([], []))
        self.assertTrue(any("c02 could not warm up" in fault for fault in faults))

    def test_a_raising_agent_is_a_harness_fault(self):
        def work(i):
            if i == 1:
                raise ValueError("bug")
            return cc.AgentRun(cc.client_name(i), [], 0, "claimed")

        runs, faults, _ = cc.race_agents(3, lambda i: None, work, rng=random.Random(1), timeout_s=5)
        self.assertEqual(len(runs), 2)
        self.assertEqual(len(faults), 1)

    def test_a_hung_agent_is_reported(self):
        gate = threading.Event()
        runs, faults, hung = cc.race_agents(2, lambda i: None, lambda i: gate.wait(5) or None,
                                            rng=random.Random(1), timeout_s=0.3)
        gate.set()
        self.assertTrue(hung)


class EmitTest(unittest.TestCase):
    def test_steps_become_race_history_records_in_time_order(self):
        ops = []
        capture = OperationCapture(Path.cwd(), "20261116T120000Z-12345678", ops.append)
        capture.trial(4, "race")
        runs = [cc.AgentRun("c01", [step("read", 5, 6, token="g1"), step("claim", 7, 9, FAIL, PRECONDITION)], 1, "x"),
                cc.AgentRun("c00", [step("claim", 1, 3), step("claim", 10, 0, UNKNOWN,
                                                              {"type": "unavailable.timeout", "message": "t"})], 2, "y")]
        cc.emit_runs(capture, runs)
        self.assertEqual([(op.client, op.kind, op.outcome) for op in ops],
                         [("c00", "claim", OK), ("c01", "read", OK), ("c01", "claim", FAIL), ("c00", "claim", UNKNOWN)])
        self.assertTrue(all(op.phase == "race" and op.k == 4 for op in ops))
        self.assertEqual(ops[2].error["type"], "precondition_failure")
        self.assertIsNone(ops[3].ret)
        self.assertEqual(len({op.op_id for op in ops}), 4)


# --------------------------------------------------------------- whole runs against fakes

class FakeOmnigraph:
    """An in-process graph with one commit counter, so a conditional claim fails when anything committed."""

    def __init__(self):
        self.lock = threading.Lock()
        self.commit = 0
        self.tasks, self.holders = {}, {}

    def publish(self):
        self.commit += 1
        return f"g{self.commit}"


class FakeHttpClient:
    server = None

    def __init__(self, endpoint="http://127.0.0.1:1", graph="witnessmark", *, timeout=60.0, observed=None, **_):
        self.observed = observed

    def _seen(self, method, path, body, result):
        if self.observed is not None:
            self.observed(method, path, body, cc.stamp(), cc.stamp(), result)
        return result

    def health(self):
        return self._seen("GET", "/healthz", None, OperationResult(Outcome.OK, 200, data={"ok": True}))

    def query(self, query, params=None, *, name=None, snapshot=None, **kw):
        server = self.server
        with server.lock:
            if name == "q_task":
                task = params["task_id"]
                rows = [{"task": task, "state": server.tasks[task]}] if task in server.tasks else []
                data = {"graph_commit_id": f"g{server.commit}", "columns": ["task", "state"], "rows": rows}
            else:
                holder = server.holders.get(params["task_id"])
                data = {"graph_commit_id": f"g{server.commit}", "columns": ["holder"],
                        "rows": [{"holder": holder}] if holder else []}
        return self._seen("POST", "/query", {"name": name}, OperationResult(Outcome.OK, 200, data=data))

    def mutate(self, query, params=None, *, name=None, commit_id=None, **kw):
        server = self.server
        with server.lock:
            if name == "m_claim_cond":
                if commit_id != f"g{server.commit}":
                    result = OperationResult(Outcome.REFUSAL, 409, "precondition_failure",
                                             {"precondition_failure": {}}, "the graph commit moved")
                else:
                    server.tasks[params["task_id"]] = "claimed"
                    server.holders[params["task_id"]] = params["agent_id"]
                    result = OperationResult(Outcome.OK, 200, data={"commit": {"graph_commit_id": server.publish()}})
            else:
                if name == "m_reset":
                    server.tasks.clear()
                    server.holders.clear()
                elif name in ("m_fixture_base", "m_fixture_task"):
                    server.tasks[params["task_id"]] = "open"
                result = OperationResult(Outcome.OK, 200, data={"commit": {"graph_commit_id": server.publish()}})
        return self._seen("POST", "/mutate", {"name": name}, result)


class FakeStack:
    lease_seconds = 30

    def __init__(self, *a, **kw):
        self.provisioned = self.down_called = False

    def provision(self):
        self.provisioned = True

    def down(self, **kw):
        self.down_called = True


class WholeRunTest(unittest.TestCase):
    def run_omnigraph(self, evidence, **kw):
        FakeHttpClient.server = FakeOmnigraph()
        host = {"os": "test", "cpu": "test", "cores": 0, "memory_gb": 0}
        with mock.patch.object(cc, "OmnigraphClient", FakeHttpClient), \
                mock.patch("witnessmark_omnigraph.capture.OmnigraphClient", FakeHttpClient), \
                mock.patch.object(cc, "Stack", FakeStack), \
                mock.patch("witnessmark_omnigraph.part2.witnessmark_env.host_info", return_value=host):
            return cc.run_o2b(Path(__file__).resolve().parents[2], evidence, "unit", "v0.15.0", BUILD, "local",
                              command="python targets/03-omnigraph/wm_omnigraph.py costcurve --smoke", **kw)

    def test_a_smoke_run_writes_all_four_files_and_a_valid_history(self):
        with tempfile.TemporaryDirectory() as root:
            manifest, path = self.run_omnigraph(Path(root), smoke=True)
            for name in ("run.json", "history.jsonl", "REPRO.md", "state"):
                self.assertTrue((path / name).exists(), name)
            self.assertGreater(validate_history(path / "history.jsonl"), 8)
            saved = json.loads((path / "run.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], "complete")
            self.assertEqual(saved["sweep"]["agents"], [1, 2])
            self.assertEqual((saved["sweep"]["warmups"], saved["sweep"]["measured_repetitions"]), (1, 1))
            self.assertTrue(saved["smoke"])
            self.assertEqual(saved["spread_gate"]["state"], "off")
            self.assertEqual(saved["scenario"]["id"], "o2b.disjoint_claims")
            self.assertEqual(path.parent.name, "o2b.disjoint_claims.sweep")
            self.assertEqual(len(saved["trials"]), 4)
            self.assertEqual([t["warmup"] for t in saved["trials"]], [True, True, False, False])
            self.assertTrue(all(t["valid"] and t["holders_ok"] for t in saved["trials"]))
            self.assertEqual(saved["findings"], [])
            self.assertEqual([row["n"] for row in saved["summary"]], [1, 2])
            self.assertEqual(saved["summary"][0]["wasted_attempts"]["median"], 0)
            state = json.loads((path / saved["trials"][3]["state_file"]).read_text(encoding="utf-8"))
            self.assertEqual([row["holders"] for row in state["state"]["tasks"]], [["c00"], ["c01"]])
            records = [json.loads(line) for line in (path / "history.jsonl").read_text(encoding="utf-8").splitlines()]
            race = [r for r in records if r["phase"] == "race"]
            self.assertTrue({r["kind"] for r in race} <= {"read", "claim"})
            self.assertTrue(any(r["phase"] == "setup" for r in records))
            self.assertIn("python targets/03-omnigraph/wm_omnigraph.py costcurve", (path / "REPRO.md").read_text(encoding="utf-8"))

    def test_the_gate_state_and_seed_reach_the_manifest(self):
        with tempfile.TemporaryDirectory() as root:
            manifest, _ = self.run_omnigraph(Path(root), smoke=True, gate_ms=1000.0, seed=7)
            self.assertEqual(manifest["spread_gate"], {"state": "on", "gate_ms": 1000.0})
            self.assertEqual(manifest["seed"], 7)

    def test_a_crash_leaves_an_error_note_and_tears_the_stack_down(self):
        with tempfile.TemporaryDirectory() as root:
            FakeHttpClient.server = FakeOmnigraph()
            with mock.patch.object(cc, "OmnigraphClient", FakeHttpClient), \
                    mock.patch("witnessmark_omnigraph.capture.OmnigraphClient", FakeHttpClient), \
                    mock.patch.object(cc, "Stack", FakeStack), \
                    mock.patch.object(cc, "_setup_omnigraph", side_effect=RuntimeError("no graph")):
                with self.assertRaises(RuntimeError):
                    cc.run_o2b(Path(__file__).resolve().parents[2], Path(root), "unit", "v0.15.0", BUILD, "local",
                               command="x", smoke=True)
            self.assertEqual(len(list(Path(root).rglob("ERROR.md"))), 1)

    def test_a_falkordb_smoke_run_succeeds_on_the_first_attempt_and_writes_four_files(self):
        class Session:
            def __init__(self, store):
                self.store = store

            def run(self, query, params=None, *, write=True):
                with self.store["lock"]:
                    if query == cc.FALKOR_SETUP:
                        self.store["tasks"] = {f"task-{i}": ["open", ""] for i in range(params["n"])}
                        return Reply([], [])
                    if query == cc.FALKOR_OBSERVE:
                        return Reply([], [[k, v[0], v[1]] for k, v in sorted(self.store["tasks"].items())])
                    task = self.store["tasks"][params["task"]]
                    if task[0] != "open":
                        return Reply(["won"], [[0]])
                    task[:] = ["claimed", params["agent"]]
                    return Reply(["won"], [[1]])

            def ping(self):
                pass

            def call(self, *args):
                return "OK"

            def close(self):
                pass

        store = {"lock": threading.Lock(), "tasks": {}}
        engine = mock.Mock()
        engine.name, engine.repo = "falkordb", "FalkorDB/FalkorDB"
        engine.describe.return_value = {"role": "baseline", "name": "falkordb", "version": "6.0.4", "digest": "sha256:1"}
        engine.health.return_value = {"ok": True}
        engine.session.side_effect = lambda timeout=60: Session(store)
        host = {"os": "test", "cpu": "test", "cores": 0, "memory_gb": 0}
        with tempfile.TemporaryDirectory() as root, mock.patch.object(cc, "make_engine", return_value=engine), \
                mock.patch.object(cc.witnessmark_env, "host_info", return_value=host):
            manifest, path = cc.run_o2b_falkordb(Path(__file__).resolve().parents[2], Path(root), "unit",
                                                 command="python wm_omnigraph.py costcurve --engine falkordb --smoke",
                                                 smoke=True)
            for name in ("run.json", "history.jsonl", "REPRO.md", "state"):
                self.assertTrue((path / name).exists(), name)
            validate_history(path / "history.jsonl")
            self.assertEqual(path.parent.name, "o2b.claim_state_disjoint.sweep")
            self.assertEqual(path.parent.parent.name, "falkordb")
            measured = [t for t in manifest["trials"] if not t["warmup"]]
            self.assertTrue(all(t["wasted_attempts"] == 0 and t["valid"] and t["holders_ok"] for t in measured))
            self.assertEqual(manifest["spread_gate"]["state"], "off")
            self.assertEqual(manifest["status"], "complete")


class CommandTest(unittest.TestCase):
    def test_costcurve_needs_a_build_for_omnigraph(self):
        with self.assertRaises(SystemExit), mock.patch("sys.stderr"):
            cli.main(["costcurve", "--batch", "x"])

    def test_costcurve_dispatches_to_each_engine(self):
        manifest = {"scenario": {"id": "s"}, "trials": [], "summary": [], "status": "complete"}
        with mock.patch.object(cli, "run_o2b", return_value=(manifest, Path("p"))) as omnigraph, \
                mock.patch.object(cli, "run_o2b_falkordb", return_value=(manifest, Path("p"))) as falkordb, \
                mock.patch("builtins.print"):
            self.assertEqual(cli.main(["costcurve", "--build", "v0.15.0", "--batch", "b", "--smoke"]), 0)
            self.assertTrue(omnigraph.call_args.kwargs["smoke"])
            self.assertIsNone(omnigraph.call_args.kwargs["gate_ms"])
            self.assertEqual(cli.main(["costcurve", "--engine", "falkordb", "--batch", "b"]), 0)
            self.assertEqual(falkordb.call_count, 1)


if __name__ == "__main__":
    unittest.main()
