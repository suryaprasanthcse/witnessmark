"""Offline coverage of the M5 Omnigraph entry points."""

import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from witnessmark.adapters.base import Reply
from witnessmark.history import FAIL, OK, Op, validate_history
from witnessmark.timing import stamp

TARGET = Path(__file__).resolve().parents[2] / "targets" / "03-omnigraph"
sys.path.insert(0, str(TARGET))

import wm_omnigraph as cli  # noqa: E402
from witnessmark_omnigraph import controls, part2  # noqa: E402
from witnessmark_omnigraph.capture import OperationCapture  # noqa: E402
from witnessmark_omnigraph.client import OperationResult, Outcome  # noqa: E402
from witnessmark_omnigraph.runner_scenarios import MergeScenario, TASK  # noqa: E402

RUN = "20261116T120000Z-12345678"
BUILD = {"image": "local/server", "digest": "sha256:abc"}


class OwnershipTest(unittest.TestCase):
    def test_bootstrap_checks_and_records_the_exact_lock(self):
        for holder, apply_code in (("A123", 0), ("OTHER", 0), ("A123", 1)):
            with self.subTest(holder=holder, apply_code=apply_code):
                ops = []
                capture = OperationCapture(Path.cwd(), RUN, ops.append)
                stack = part2.Stack(Path.cwd(), "wm-unit-bootstrap", BUILD, "local", capture=capture)
                applied = subprocess.CompletedProcess([], apply_code, "Admission lock: A123\n")
                status = subprocess.CompletedProcess([], 0, f'{{"lock_id": "{holder}"}}')
                ok = subprocess.CompletedProcess([], 0, "")
                with mock.patch.object(stack, "_cluster", side_effect=[applied, status, ok]) as commands, \
                        mock.patch.object(stack, "_assert_fresh_root"), \
                        mock.patch.object(stack, "compose", return_value=ok), mock.patch.object(stack, "_wait_url"):
                    if holder == "A123" and not apply_code:
                        stack.provision()
                        self.assertEqual(commands.call_args.args, ("force-unlock", "A123"))
                        self.assertEqual([op.kind for op in ops[:3]],
                                         ["cluster_apply", "cluster_status", "cluster_force_unlock"])
                        self.assertTrue(all(op.phase == "setup" and op.client == "nemesis" and op.ret for op in ops[:3]))
                        with self.assertRaisesRegex(RuntimeError, "cannot be retried"):
                            stack.provision()
                    else:
                        with self.assertRaises(RuntimeError):
                            stack.provision()
                        self.assertNotIn("force-unlock", [item.args[0] for item in commands.call_args_list])

    def test_transfer_starts_b_only_after_clean_exit_and_release(self):
        for exit_code, killed, holder in ((0, False, None), (0, False, "RETAINED"), (137, True, None), (2, False, None)):
            with self.subTest(exit_code=exit_code, killed=killed, holder=holder):
                stack, capture = mock.Mock(), mock.Mock(k=1)
                stack.clean_stop_a.return_value = {"exit_code": exit_code, "killed": killed, "oom_killed": False}
                stack.cluster_status.return_value = {"lock_id": holder}
                stack.start_b.return_value = subprocess.CompletedProcess([], 0, "")
                capture.client.return_value.mutate.return_value = OperationResult(Outcome.OK, data={})
                state = {"scan_ok": True, "acknowledged_missing": [], "state": {"task": []}}
                with mock.patch.object(part2, "_health", return_value=True), \
                        mock.patch.object(part2, "o4_integrity", return_value=state):
                    result, _ = part2._clean_stop_cell(stack, capture, part2.load_queries())
                self.assertTrue(stack.cluster_status.called)
                if exit_code == 0 and holder is None:
                    stack.start_b.assert_called_once_with(check=False)
                    self.assertEqual(result["reason"], "admission released; B started")
                else:
                    stack.start_b.assert_not_called()
                    self.assertEqual(result["status"], "NOT_EXERCISED")
                    self.assertEqual(result["reason"], part2.RETAINED_ADMISSION)

    def test_exit_inspection_detects_oom_or_sigkill(self):
        for code, oom in ((137, False), (1, True), (0, False)):
            state = part2._shutdown_state(json.dumps({"ExitCode": code, "OOMKilled": oom, "Running": False}))
            self.assertEqual(state["killed"], code == 137 or oom)


class PhaseBRunsTest(unittest.TestCase):
    def test_merge_fixture_payload_and_sequential_rule(self):
        scenario = MergeScenario()
        session = mock.Mock()
        scenario.setup(session, 2)
        self.assertEqual([call.args[0] for call in session.client.branch_create.call_args_list],
                         ["agent/c00", "agent/c01"])
        self.assertEqual(scenario.payload("thread", 1, 2)[1], {"source": "agent/c01"})
        now = stamp()
        winner = Op(RUN, 0, "control", "0-c00-0", "c00", "merge", {"agent": "c00"}, now, now, OK)
        loser = Op(RUN, 0, "control", "0-c01-0", "c01", "merge", {"agent": "c01"}, now, now, FAIL,
                   error={"type": "CardinalityViolation", "message": "already held"})
        final = {"snapshot": "first", "holders": {TASK: ["c00"]},
                 "lease_records": [{"id": "lease", "task": TASK, "agent": "c00", "from_seq": 1,
                                    "observed_graph_commit_id": "first"}]}
        self.assertTrue(scenario.sequential_expected([winner, loser], final, 2)[0])
        self.assertEqual(scenario.precondition(final), scenario.precondition(final | {"snapshot": "second"}))
        self.assertNotEqual(scenario.precondition(final),
                            scenario.precondition(final | {"holders": {TASK: ["c01"]}}))

    def test_o2_calibration_flag_preserves_default_gate(self):
        args = ["race", "--build", "v0.15.0", "--scenario", "o2a"]
        manifest = {"scenario": {"id": "o2"}, "verdicts": [{"status": "PASS"}], "path": "fake"}
        with mock.patch.object(cli, "run", return_value=manifest) as run, mock.patch("builtins.print"):
            self.assertEqual(cli.main(args + ["--no-spread-gate"]), 0)
            self.assertIsNone(run.call_args.args[0].spread_gate_ms)
            self.assertEqual(cli.main(args), 0)
            self.assertEqual(run.call_args.args[0].spread_gate_ms, 40.0)

    def test_o6_writes_both_engine_references_and_valid_history(self):
        def reply(query, params, *, write=True):
            if "q_eligible" == query or "RETURN DISTINCT" in query:
                return Reply(["agent", "task"], [["c00", TASK]])
            if "q_live" == query or "count(holder)" in query:
                return Reply(["live"], [[int(params["task_id"] == TASK)]])
            return Reply([], [])

        session = mock.Mock()
        session.run.side_effect = reply
        baseline = mock.Mock()
        baseline.session.return_value = session
        baseline.describe.side_effect = [{"name": name, "image": f"local/{name}", "digest": "sha256:def"}
                                         for name in ("neo4j", "falkordb")]
        with tempfile.TemporaryDirectory() as root:
            with mock.patch.object(part2, "Stack"), mock.patch.object(part2.OmnigraphEngine, "session", return_value=session), \
                    mock.patch.object(controls, "make_engine", return_value=baseline):
                manifest, path = part2.run_o6(Path.cwd(), Path(root), "unit", "v0.15.0", BUILD, "local",
                                              command="python wm_omnigraph.py parity")
            self.assertTrue(manifest["controls"]["sequential"]["met"])
            self.assertEqual(manifest["trials"][0]["classifications"]["q_live_open"], "identical")
            self.assertTrue((path / "state" / "0.json").exists() and (path / "state" / "1.json").exists())
            self.assertIn("local/neo4j", (path / "REPRO.md").read_text(encoding="utf-8"))
            self.assertGreater(validate_history(path / "history.jsonl"), 20)
            self.assertTrue((path / "run.json").exists())

    def test_o1_uses_separate_unrelated_reader_and_writer(self):
        reply = OperationResult(Outcome.OK, data={})

        def completed(*args, **kwargs):
            time.sleep(0.002)
            return reply

        client, capture = mock.Mock(), mock.Mock()
        main, reader, writer = mock.Mock(), mock.Mock(), mock.Mock()
        capture.client.side_effect = [main, reader, writer]
        main.query.side_effect = reader.query.side_effect = writer.mutate.side_effect = completed
        client.branch_create.side_effect = completed
        with mock.patch.object(part2, "_rss_mb", return_value=1.0):
            result = part2._timed_branch_create(client, part2.load_queries(), "unit", capture)
        self.assertEqual([call.kwargs.get("graph") for call in capture.client.call_args_list],
                         [None, "unrelated", "unrelated"])
        self.assertTrue(reader.query.called and writer.mutate.called)
        for field in ("stall_ms", "unrelated_reader_stall_ms", "unrelated_writer_stall_ms"):
            self.assertGreaterEqual(result[field], 0)
