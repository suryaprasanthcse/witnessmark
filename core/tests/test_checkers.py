"""The invariant checkers, on hand-built histories."""

import unittest

from witnessmark.checkers import check_claim_lease, check_claim_state, check_counter, check_disjoint
from witnessmark.history import FAIL, OK, UNKNOWN, Op
from witnessmark.timing import Stamp

T0 = Stamp(0, "2026-11-13T00:00:00.000000Z")
T1 = Stamp(1, "2026-11-13T00:00:00.000001Z")


def op(i, outcome, **values):
    agent = f"c{i:02d}"
    return Op("r", 1, "race", f"1-{agent}-0", agent, "claim", {"agent": agent, **values.pop("input", {})},
              T0, None if outcome == UNKNOWN else T1, outcome, values or None)


class ClaimStateTest(unittest.TestCase):
    def test_one_winner_who_holds_the_task(self):
        ops = [op(0, OK), op(1, FAIL), op(2, FAIL)]
        check = check_claim_state(ops, {"state": "claimed", "holder": "c00"})
        self.assertTrue(check.held)
        self.assertEqual(check.magnitude, 1)

    def test_two_winners_violate(self):
        ops = [op(0, OK), op(1, OK), op(2, FAIL)]
        check = check_claim_state(ops, {"state": "claimed", "holder": "c01"})
        self.assertFalse(check.held)
        self.assertEqual(check.magnitude, 2)
        self.assertEqual(check.witnesses, ["1-c00-0", "1-c01-0"])

    def test_lone_winner_must_be_the_holder(self):
        check = check_claim_state([op(0, OK), op(1, FAIL)], {"state": "claimed", "holder": "c01"})
        self.assertFalse(check.held)

    def test_no_winner_but_held_by_an_unknown_claimant_is_allowed(self):
        check = check_claim_state([op(0, UNKNOWN), op(1, FAIL)], {"state": "claimed", "holder": "c00"})
        self.assertTrue(check.held)

    def test_no_winner_but_held_by_a_refused_claimant_violates(self):
        check = check_claim_state([op(0, FAIL), op(1, FAIL)], {"state": "claimed", "holder": "c01"})
        self.assertFalse(check.held)


class ClaimLeaseTest(unittest.TestCase):
    def test_one_lease(self):
        self.assertTrue(check_claim_lease([op(0, OK), op(1, FAIL)], ["c00"]).held)

    def test_two_leases_violate_even_with_one_acknowledged_winner(self):
        check = check_claim_lease([op(0, OK), op(1, UNKNOWN)], ["c00", "c01"])
        self.assertFalse(check.held)
        self.assertEqual(check.magnitude, 2)

    def test_no_lease_and_no_winner(self):
        self.assertTrue(check_claim_lease([op(0, FAIL)], []).held)


class CounterTest(unittest.TestCase):
    def test_all_increments_survive(self):
        ops = [op(i, OK, v=i + 1) for i in range(5)]
        self.assertTrue(check_counter(ops, 5).held)

    def test_lost_updates_are_counted_and_witnessed(self):
        ops = [op(0, OK, v=1), op(1, OK, v=1), op(2, OK, v=2)]
        check = check_counter(ops, 2)
        self.assertFalse(check.held)
        self.assertEqual(check.magnitude, 1)
        self.assertEqual(sorted(check.witnesses), ["1-c00-0", "1-c01-0"])

    def test_unknown_outcomes_widen_the_allowed_range(self):
        ops = [op(0, OK, v=1), op(1, UNKNOWN)]
        self.assertTrue(check_counter(ops, 2).held)
        self.assertTrue(check_counter(ops, 1).held)
        self.assertFalse(check_counter(ops, 3).held)


class DisjointTest(unittest.TestCase):
    def test_every_acknowledged_write_survives(self):
        ops = [op(i, OK, input={"prop": f"p{i:02d}", "v": i}) for i in range(3)]
        self.assertTrue(check_disjoint(ops, {"p00": 0, "p01": 1, "p02": 2}).held)

    def test_missing_writes_violate(self):
        ops = [op(i, OK, input={"prop": f"p{i:02d}", "v": i}) for i in range(3)]
        check = check_disjoint(ops, {"p00": 0, "p01": None, "p02": None})
        self.assertFalse(check.held)
        self.assertEqual(check.magnitude, 2)
        self.assertEqual(check.witnesses, ["1-c01-0", "1-c02-0"])


if __name__ == "__main__":
    unittest.main()
