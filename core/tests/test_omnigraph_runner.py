"""Focused tests for the Omnigraph workload loader and network adapter."""

from pathlib import Path
import sys
import threading
import time
import unittest
from unittest import mock

from witnessmark.adapters.base import Reply

TARGET = Path(__file__).resolve().parents[2] / "targets" / "03-omnigraph"
sys.path.insert(0, str(TARGET))

from witnessmark_omnigraph import part2  # noqa: E402
from witnessmark_omnigraph.client import OperationResult, Outcome  # noqa: E402
from witnessmark_omnigraph.engine import OmnigraphSession  # noqa: E402
from witnessmark_omnigraph.workload import load_queries  # noqa: E402


class OmnigraphRunnerTest(unittest.TestCase):
    def test_workload_loader_finds_every_checked_in_declaration(self):
        self.assertEqual(set(load_queries()), {
            "m_reset", "m_fixture_base", "m_fixture_agent", "m_fixture_task",
            "m_o1_fixture", "q_task", "q_task_holder", "q_live", "q_eligible",
            "m_claim_cond", "m_claim_card", "m_ledger", "q_ledger",
        })

    def test_dump_uses_one_snapshot_and_derives_live_lease_record(self):
        session = object.__new__(OmnigraphSession)
        calls = []

        def run(query, params, *, write):
            calls.append((query, params, write))
            if query == "q_task":
                return Reply(["task", "state"], [["task-0", "claimed"]], "commit-7", {})
            return Reply(["holder", "from_seq", "rw"], [["c00", 4, "lease-4"]], "commit-7", {})

        session.run = run
        state = session.dump_task("task-0")

        self.assertEqual(calls[1], ("q_task_holder", {"task_id": "task-0", "_snapshot": "commit-7"}, False))
        self.assertEqual(state["lease_records"], [{
            "id": "lease-4", "task": "task-0", "agent": "c00", "from_seq": 4,
            "until_seq": None, "observed_graph_commit_id": "commit-7", "observed_order": 1,
        }])


class _FakeFalkorSession:
    def __init__(self, log):
        self.log = log

    config = {"appendonly": "no", "appendfsync": "everysec"}

    def call(self, *args):
        self.log.append(args)
        time.sleep(0.001)
        if args[:2] == ("CONFIG", "GET"):
            return [args[2], self.config[args[2]]]
        if args[:2] == ("CONFIG", "SET"):
            self.config[args[2]] = args[3]
            return "OK"
        return "aof_current_size:7\n" if args[0] == "INFO" else []

    def close(self):
        pass


class _FakeFalkorEngine:
    log: list = []

    def __init__(self, *_args, **_kwargs):
        pass

    def session(self, **_kwargs):
        return _FakeFalkorSession(self.log)


class FalkorCurveTest(unittest.TestCase):
    def test_curve_records_delete_time_for_every_measured_repetition(self):
        # Regression: the first batch crashed with UnboundLocalError because the
        # warm-up loop wrote into `samples` before it was assigned.
        _FakeFalkorEngine.log = []
        with mock.patch.object(part2, "make_engine", lambda *a, **k: _FakeFalkorEngine()),                 mock.patch.object(part2, "_rss_mb", lambda _container: 10.0),                 mock.patch.object(part2, "SIZES", (32_000,)),                 mock.patch.object(part2, "WARMUPS", 2),                 mock.patch.object(part2, "REPETITIONS", 3):
            result = part2.run_falkor_curve(Path.cwd())

        # The curve runs under S28's persistence, records it, and puts back what it found.
        self.assertEqual(result["persistence_during_curve"], {"appendonly": "yes", "appendfsync": "always"})
        self.assertEqual(result["persistence_found"], {"appendonly": "no", "appendfsync": "everysec"})
        self.assertEqual(_FakeFalkorSession.config, {"appendonly": "no", "appendfsync": "everysec"})
        row = result["rows"][0]
        self.assertEqual(len(row["samples"]), 3)
        for sample in row["samples"]:
            self.assertGreaterEqual(sample["delete_ms"], 0)
            self.assertEqual(sample["rss_after_mb"], 10.0)
        deletes = [call for call in _FakeFalkorEngine.log if call[0] == "GRAPH.DELETE" and call[1].startswith("o1")]
        copies = [call for call in _FakeFalkorEngine.log if call[0] == "GRAPH.COPY"]
        self.assertEqual(len(copies), 5)  # 2 warm-ups + 3 measured
        self.assertEqual([call[2] for call in copies], [call[1] for call in deletes if call[1] != "o1source" and call[1] != "o1other"])


class StackReadinessTest(unittest.TestCase):
    def test_provision_waits_on_readyz_not_healthz(self):
        # Regression: /healthz answers before the graph loads, so the first data
        # request through the 17 ms proxy got 503 graph_unavailable.
        stack = part2.Stack(Path.cwd(), "wm-m4-unit", {"image": "x", "digest": "sha256:0"}, "local")
        waits = []
        done = mock.Mock(stdout="Admission lock: ABC123\n", returncode=0)
        status = mock.Mock(stdout='{"lock_id": "ABC123"}\n', returncode=0)
        with mock.patch.object(stack, "compose", return_value=done), \
                mock.patch.object(stack, "_assert_fresh_root"), \
                mock.patch.object(stack, "_cluster", side_effect=[done, status, done]), \
                mock.patch.object(stack, "_wait_url", side_effect=waits.append):
            stack.provision()
            stack.start_b()
        self.assertEqual(waits, ["http://127.0.0.1:18080/readyz", "http://127.0.0.1:18081/readyz"])


class O4ClassificationTest(unittest.TestCase):
    def test_a_gap_is_never_labelled_a_boundary_or_a_pass(self):
        classify = part2.classify_o4_cell
        # No successor: nothing was exercised, whatever the build.
        self.assertEqual(classify("edge-b2dbaff", "local", False)[0], "NOT_EXERCISED")
        self.assertEqual(classify("v0.15.0", "local", False)[0], "NOT_EXERCISED")
        # A takeover on the edge build without an epoch claim says nothing about the fence.
        self.assertEqual(classify("edge-b2dbaff", "minio", True)[0], "NOT_EXERCISED")
        # Only a real failover on the release that predates the fence is the documented baseline.
        self.assertEqual(classify("v0.15.0", "minio", True)[0], "BOUNDARY")
        for build in ("edge-b2dbaff", "v0.15.0"):
            for storage in ("local", "minio"):
                for ready in (False, True):
                    self.assertNotIn(classify(build, storage, ready)[0], ("PASS", "FAIL"))


class RedactionTest(unittest.TestCase):
    def test_paths_under_a_user_home_and_the_repo_are_removed(self):
        repo = Path("C:/work/harness")
        home = "C:" + "/".join(("", "Users", "someone"))
        home_win = home.replace("/", chr(92))
        app_dir = "App" + "Data"
        win_path = chr(92).join((home_win, app_dir, "Local", "x.py"))
        text = f'File "{win_path}" at {home}/proj and {repo}/core and C:/work/harness/core'
        cleaned = part2.redact_paths(text, repo)
        for leaked in ("someone", "Users", app_dir, "work"):
            self.assertNotIn(leaked, cleaned)


class LeaseTest(unittest.TestCase):
    def test_only_o4_shortens_the_cluster_lease(self):
        build = {"image": "x", "digest": "sha256:0"}
        default = part2.Stack(Path.cwd(), "wm-m4-unit", build, "minio")
        shortened = part2.Stack(Path.cwd(), "wm-m4-unit", build, "minio", lease_seconds=part2.LEASE_SECONDS)
        self.assertEqual(default.environ["WM_CLUSTER_LEASE_SECONDS"], "30")
        self.assertEqual(shortened.environ["WM_CLUSTER_LEASE_SECONDS"], "2")


class _FakeLedgerClient:
    """Branch create copies a ledger; appends land on whichever branch they name."""

    def __init__(self):
        self.rows = {"main": []}
        self.lock = threading.Lock()

    def _ok(self, data=None):
        return OperationResult(Outcome.OK, status=200, data=data)

    def branch_delete(self, name):
        self.rows.pop(name, None)
        return self._ok()

    def load_ndjson(self, _payload):
        return self._ok()

    def branch_create(self, name, from_branch="main"):
        with self.lock:
            self.rows[name] = list(self.rows[from_branch])
        return self._ok()

    def mutate(self, _query, params, name=None, branch="main"):
        with self.lock:
            self.rows[branch].append({"seq": params["seq"], "rule": params["rule"]})
        return self._ok()

    def query(self, _query, params, name=None, branch="main"):
        with self.lock:
            rows = [{"seq": r["seq"]} for r in self.rows[branch] if r["rule"] == params["rule"]]
        return self._ok({"rows": rows})


class I6ControlTest(unittest.TestCase):
    def test_the_branch_is_cut_after_appends_landed_so_the_prefix_is_not_empty(self):
        # Regression: a fixed sleep cut the branch before the first append on a slow store,
        # and an empty prefix passed I6a trivially.
        queries = {"m_ledger": "m_ledger", "q_ledger": "q_ledger"}
        result = part2._i6_controls(_FakeLedgerClient(), queries)
        self.assertTrue(result["i6a_exercised"])
        self.assertTrue(result["i6a_gapless_prefix"])
        self.assertGreaterEqual(result["i6a_prefix_length"], part2.I6_BRANCH_AFTER)
        self.assertEqual(result["branch_prefix_seq"], list(range(1, result["i6a_prefix_length"] + 1)))
        self.assertTrue(result["i6b_isolation"])

    def test_an_empty_prefix_is_not_a_pass(self):
        class Slow(_FakeLedgerClient):
            def branch_create(self, name, from_branch="main"):
                result = super().branch_create(name, from_branch)
                if name == "i6-prefix":
                    self.rows[name] = []  # a branch that holds none of the ledger
                return result

        result = part2._i6_controls(Slow(), {"m_ledger": "m_ledger", "q_ledger": "q_ledger"})
        self.assertFalse(result["i6a_exercised"])
        self.assertFalse(result["i6a_gapless_prefix"])


class _FakeScanClient:
    def __init__(self, agents, ok=True):
        self.agents, self.ok = agents, ok

    def branch_list(self, detailed=False):
        return OperationResult(Outcome.OK, status=200, data={"branches": ["main"]})

    def query(self, _query, _params, name=None, branch="main", snapshot=None):
        if not self.ok:
            return OperationResult(Outcome.UNKNOWN, kind="connection", message="closed")
        rows = [{"agent": a, "task": "t"} for a in self.agents] if name == "q_eligible" else []
        return OperationResult(Outcome.OK, status=200, data={"rows": rows})


class O4IntegrityTest(unittest.TestCase):
    queries = {name: name for name in ("q_task", "q_task_holder", "q_eligible", "q_ledger")}

    def test_an_acknowledged_write_that_is_absent_is_reported(self):
        result = part2.o4_integrity(_FakeScanClient(["a-p1-b"]), self.queries, ["a-p1-b", "b-p1-b"])
        self.assertTrue(result["scan_ok"])
        self.assertEqual(result["acknowledged_missing"], ["b-p1-b"])

    def test_every_acknowledged_write_present(self):
        result = part2.o4_integrity(_FakeScanClient(["a", "b"]), self.queries, ["a", "b"])
        self.assertEqual(result["acknowledged_missing"], [])

    def test_a_failed_scan_is_not_a_clean_scan_and_hides_no_loss_claim(self):
        result = part2.o4_integrity(_FakeScanClient([], ok=False), self.queries, ["a"])
        self.assertFalse(result["scan_ok"])
        self.assertIsNone(result["acknowledged_missing"])


if __name__ == "__main__":
    unittest.main()
