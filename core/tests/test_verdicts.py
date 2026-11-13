"""Verdicts, control records, run ids and the reporter's statistics."""

import datetime
import unittest
from pathlib import Path

from witnessmark.evidence import digest, make_run_id, redact
from witnessmark.report import proposed_gate_ms
from witnessmark.scenarios import Expectation
from witnessmark.verdicts import percentile, role_control, summarize, verdict


def trial(held, magnitude=1, valid=True):
    return {"valid": valid, "checks": [{"held": held, "magnitude": magnitude, "witnesses": [] if held else ["w"]}]}


NEGATIVE = Expectation("negative", "baseline", "ref")
POSITIVE_KD = Expectation("positive", "documented", "ref", "KD-N1")


class VerdictTest(unittest.TestCase):
    def test_pass_when_no_valid_trial_violates(self):
        record = verdict("I1A", [trial(True), trial(True)], True, NEGATIVE, "winners")
        self.assertEqual(record["status"], "PASS")
        self.assertEqual((record["trials_violating"], record["trials_valid"]), (0, 2))

    def test_fail_without_a_known_deviation(self):
        record = verdict("I1A", [trial(True), trial(False, 3)], True, NEGATIVE, "winners")
        self.assertEqual(record["status"], "FAIL")
        self.assertEqual(record["magnitude"], {"min": 1, "median": 2.0, "max": 3, "unit": "winners"})

    def test_known_deviation(self):
        record = verdict("I1A", [trial(False, 4)], True, POSITIVE_KD, "winners")
        self.assertEqual(record["status"], "KNOWN_DEVIATION")
        self.assertIn("KD-N1", record["note"])

    def test_invalid_when_the_sequential_control_fails(self):
        self.assertEqual(verdict("I1A", [trial(True)], False, NEGATIVE, "winners")["status"], "INVALID")

    def test_invalid_trials_do_not_count(self):
        record = verdict("I1A", [trial(False, valid=False), trial(True)], True, NEGATIVE, "winners")
        self.assertEqual((record["status"], record["trials_valid"]), ("PASS", 1))

    def test_role_controls(self):
        self.assertTrue(role_control("negative", "c", [trial(True)])["met"])
        self.assertFalse(role_control("negative", "c", [trial(False)])["met"])
        self.assertTrue(role_control("positive", "c", [trial(True), trial(False)])["met"])
        self.assertFalse(role_control("positive", "c", [trial(True)])["met"])
        self.assertFalse(role_control("negative", "c", [trial(True, valid=False)])["met"])


class StatisticsTest(unittest.TestCase):
    def test_percentile_is_nearest_rank(self):
        values = list(range(1, 101))
        self.assertEqual(percentile(values, 50), 50)
        self.assertEqual(percentile(values, 99), 99)
        self.assertEqual(percentile([3.0], 99), 3.0)
        self.assertIsNone(percentile([], 50))

    def test_summarize(self):
        self.assertEqual(summarize([1, 3, 2]), {"min": 1, "median": 2, "max": 3})
        self.assertEqual(summarize([]), {})

    def test_proposed_gate(self):
        self.assertEqual(proposed_gate_ms([1.0] * 99 + [4.2]), 2.0)
        self.assertEqual(proposed_gate_ms([0.1, 0.2]), 1.0)
        self.assertIsNone(proposed_gate_ms([]))


class EvidenceIdTest(unittest.TestCase):
    def test_run_id_format_and_determinism(self):
        started = datetime.datetime(2026, 11, 13, 9, 30, 5, tzinfo=datetime.timezone.utc)
        run_id = make_run_id(started, {"a": 1})
        self.assertRegex(run_id, r"^20261113T093005Z-[0-9a-f]{8}$")
        self.assertEqual(run_id, make_run_id(started, {"a": 1}))
        self.assertNotEqual(run_id, make_run_id(started, {"a": 2}))

    def test_digest_ignores_key_order(self):
        self.assertEqual(digest({"a": 1, "b": 2}), digest({"b": 2, "a": 1}))

    def test_redact_replaces_the_home_directory_in_every_spelling(self):
        home = str(Path.home())
        text = f"File {home}\\x.py; {home.replace(chr(92), '/')}/y.py; {home.replace(chr(92), chr(92) * 2)}\\\\z"
        cleaned = redact(text)
        self.assertNotIn(Path.home().name, cleaned)
        self.assertEqual(cleaned.count("~"), 3)


if __name__ == "__main__":
    unittest.main()
