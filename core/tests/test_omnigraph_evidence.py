"""Offline checks of the Omnigraph Part 2 evidence contract."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from witnessmark.history import Op, UNKNOWN, read_history, validate_history, write_history
from witnessmark.timing import stamp

TARGET = Path(__file__).resolve().parents[2] / "targets" / "03-omnigraph"
sys.path.insert(0, str(TARGET))

from witnessmark_omnigraph.capture import LOG_CAP, RunCapture, repro_command  # noqa: E402
from witnessmark_omnigraph.client import OperationResult, Outcome  # noqa: E402

RUN = "20261116T120000Z-12345678"


class HistoryValidationTest(unittest.TestCase):
    def test_rejects_a_history_row_that_violates_the_schema(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "history.jsonl"
            op = Op(RUN, 1, "race", "1-c00-1", "c00", "query", {}, stamp(), None, UNKNOWN)
            write_history(path, [op])
            self.assertEqual(validate_history(path), 1)
            for edits in ({"phase": "invalid"}, {"ret": stamp().to_json()},
                          {"inv": {"mono_ns": 3, "wall": "2026-11-16", "domain": "host"}},
                          {"error": {"type": "http"}}):
                with self.subTest(edits=edits):
                    path.write_text(json.dumps(op.to_json() | edits) + "\n", encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "history line 1"):
                        validate_history(path)


class Part2EvidenceTest(unittest.TestCase):
    def test_history_state_manifest_and_redacted_reproduction(self):
        with tempfile.TemporaryDirectory() as root:
            repo = Path(root).resolve()
            home = "C:/" + "/".join(("Users", "someone", "scratch"))
            command = repro_command(repo, ["i6", "--evidence", home.replace("/", chr(92))])
            manifest = {
                "run_id": RUN, "harness": {"commit": "a" * 40, "dirty": False},
                "components": [{"name": "omnigraph-server", "version": "v0.15.0", "image": "local/test",
                                "digest": "sha256:abc", "config": {"backend": "local"}}],
                "scenario": {"id": "o1.i6_controls", "mode": "controls"},
            }
            capture = RunCapture(repo, repo / "evidence", manifest, command)
            try:
                capture.trial(1)
                client = capture.client("http://127.0.0.1:18080")
                with patch.object(client, "_send", side_effect=[
                    OperationResult(Outcome.OK, data={"graph_commit_id": "commit-1"}),
                    OperationResult(Outcome.UNKNOWN, kind="timeout", message=home),
                ]):
                    client.query("query", {"password": "key-to-hide"}, name="q_task")
                    client.mutate("mutation", name="m_claim")
                capture.action("pause", "wm-omnigraph-a", lambda: subprocess.CompletedProcess([], 0))
                log = capture.write_log("wm-minio", ("é" * LOG_CAP) + "\nRootUser: example-id\n"
                                        "RootPass: example-secret\n" + home)
                trial = {}
                capture.final_state(trial, {"rows": [1]})
                capture.write_manifest(manifest | {"trials": [trial]})
            finally:
                capture.close()
            self.assertEqual(capture.path.relative_to(repo / "evidence").as_posix(),
                             f"omnigraph/v0.15.0.local/o1.i6_controls.controls/{RUN}")
            history = capture.path / "history.jsonl"
            self.assertEqual(validate_history(history), 3)
            read, unknown, pause = read_history(history)
            self.assertEqual(read["token"], "commit-1")
            self.assertEqual(read["input"]["body"]["params"]["password"], "<redacted>")
            self.assertIsNone(unknown["ret"])
            self.assertEqual((pause["phase"], pause["client"], pause["kind"]), ("nemesis", "nemesis", "pause"))
            self.assertLessEqual(pause["inv"]["mono_ns"], pause["ret"]["mono_ns"])
            self.assertNotIn("someone", history.read_text(encoding="utf-8"))
            state = json.loads((capture.path / trial["state_file"]).read_text(encoding="utf-8"))
            self.assertEqual(state["state"], {"rows": [1]})
            self.assertTrue(state["digest"].startswith("sha256:"))
            log_file = capture.path / log
            self.assertLessEqual(log_file.stat().st_size, LOG_CAP)
            log_text = log_file.read_text(encoding="utf-8")
            for value in ("someone", "example-id", "example-secret"):
                self.assertNotIn(value, log_text)
            self.assertIn("RootUser: <redacted>", log_text)
            repro = (capture.path / "REPRO.md").read_text(encoding="utf-8")
            for value in ("someone", chr(92)):
                self.assertNotIn(value, repro)
            for value in ("<user-home>", "local", "sha256:abc", "dirty: false"):
                self.assertIn(value, repro)
