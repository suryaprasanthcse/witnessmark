"""Omnigraph scenarios adapted to the core thread runner contract."""

from __future__ import annotations

from collections import Counter

from witnessmark.checkers import Check, check_claim_lease
from witnessmark.history import FAIL, OK
from witnessmark.scenarios import Scenario, client_name

from .engine import OmnigraphSession
from .scenarios import SCHEMA_DOC, SERVER_DOC

TASK = "task-0"
SKILL = "skill-0"
MERGE_REFUSALS = frozenset({"CardinalityViolation", "DivergentInsert", "DivergentUpdate", "DeleteVsUpdate"})
# Error types that carry no server-typed reason: the client's fallbacks for a refusal it could not name.
_UNTYPED = frozenset({"", "refusal", "untyped", "http_error", "protocol"})


def refusal_type(op) -> str | None:
    """The typed reason of a definite refusal, or None when the refusal is untyped."""
    kind = str((op.error or {}).get("type") or "")
    return None if kind in _UNTYPED or kind.startswith("http_") else kind


def refusal_counts(ops) -> dict[str, int]:
    counts = Counter(refusal_type(op) or "untyped" for op in ops if op.outcome == FAIL)
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def typed_refusal_check(base: Check, ops, *, extra_problems: list[str] | None = None,
                        extra_witnesses: list[str] | None = None) -> Check:
    """I1 at the race (M5 maintainer ruling, 2026-11-16).

    Every typed definite refusal is accepted and counted per type. The check fails only on a second
    winner, a second holder, a winner that does not hold its lease (a lost acknowledged write), an
    outcome that could have applied but cannot be accounted for (check_claim_lease), or an untyped
    refusal.
    """
    untyped = [op.op_id for op in ops if op.outcome == FAIL and refusal_type(op) is None]
    problems = ([] if base.held else [base.detail]) + list(extra_problems or [])
    if untyped:
        problems.append(f"{len(untyped)} refusal(s) carried no typed reason")
    counts = "; ".join(f"{kind} {count}" for kind, count in refusal_counts(ops).items()) or "none"
    if not problems:
        return Check(base.invariant, True, base.magnitude, base.unit, f"{base.detail}; refusals by type: {counts}",
                     [])
    witnesses = list(dict.fromkeys(base.witnesses + list(extra_witnesses or []) + untyped))
    return Check(base.invariant, False, max(1, base.magnitude, len(untyped)), base.unit,
                 f"{'; '.join(problems)}; refusals by type: {counts}", witnesses)


class _TaskRace(Scenario):
    def precondition(self, state: dict) -> dict:
        # Each fixture setup publishes a new head even when the logical state is identical.
        comparable = {key: value for key, value in state.items() if key != "snapshot"}
        comparable["lease_records"] = [
            {key: value for key, value in lease.items() if key != "observed_graph_commit_id"}
            for lease in state["lease_records"]
        ]
        return comparable


class ClaimScenario(_TaskRace):
    invariant = "I1A"
    kind = "claim"
    shapes = {"thread": ""}
    allowed_refusals: set[str] = set()

    def __init__(self, conditional: bool):
        self.conditional = conditional
        self.id = "o2a.conditional_one_task" if conditional else "o2c.cardinality_one_task"
        self.mutation = "m_claim_cond" if conditional else "m_claim_card"
        self.basis_ref = SERVER_DOC if conditional else SCHEMA_DOC
        self.allowed_refusals = {"precondition_failure"} if conditional else {"CardinalityViolation"}
        self._commit_id: str | None = None

    def setup(self, session: OmnigraphSession, n: int) -> None:
        session.run("m_fixture_base", {"task_id": TASK, "skill_id": SKILL})
        for i in range(n):
            session.run("m_fixture_agent", {"agent_id": client_name(i), "skill_id": SKILL})
        observed = session.run("q_task", {"task_id": TASK}, write=False)
        self._commit_id = observed.token
        if self.conditional and self._commit_id is None:
            raise RuntimeError("q_task did not return the conditional graph commit id")

    def payload(self, shape: str, i: int, n: int):
        params = {
            "task_id": TASK,
            "agent_id": client_name(i),
            "from_seq": i + 1,
            "until_pt": 9_223_372_036_854_775_807,
            "rw": f"lease-{i:02d}",
        }
        if self.conditional:
            params["_commit_id"] = self._commit_id
        recorded = {"task": TASK, "agent": client_name(i), "from_seq": i + 1}
        return self.mutation, params, recorded

    def classify(self, reply):
        return OK, {"won": 1, "commit": reply.token}

    def observe(self, session: OmnigraphSession, n: int) -> dict:
        return session.dump_task(TASK)

    def check(self, ops, state, n):
        base = check_claim_lease(ops, state["holders"].get(TASK, []), state["lease_records"])
        return typed_refusal_check(base, ops)

    def sequential_expected(self, ops, state, n):
        # The sequential control keeps the documented answer exactly: one winner and, for every later
        # claim, the scenario's documented refusal type (precondition_failure or CardinalityViolation).
        winners = [op.input.get("agent") for op in ops if op.outcome == OK]
        holders = state["holders"].get(TASK, [])
        check = self.check(ops, state, n)
        documented = all(op.outcome == OK or (op.outcome == FAIL and refusal_type(op) in self.allowed_refusals)
                         for op in ops)
        met = winners == [client_name(0)] and holders == [client_name(0)] and check.held and documented
        return met, "one winner, its live lease, typed refusals, no overlapping lease records", \
            f"winners {winners}; holders {holders}; {check.detail}"


def merge_branches(n: int) -> list[str]:
    return [f"agent/{client_name(i)}" for i in range(n)]


def prepare_merge_fixture(session: OmnigraphSession, n: int) -> list:
    branches = merge_branches(n)
    for branch in branches:
        session.client.branch_delete(branch)
    session.run("m_fixture_base", {"task_id": TASK, "skill_id": SKILL})
    for i in range(n):
        session.run("m_fixture_agent", {"agent_id": client_name(i), "skill_id": SKILL})
    creates = [session.client.branch_create(branch, from_branch="main") for branch in branches]
    for result in creates:
        session._raise(result)
    for i, branch in enumerate(branches):
        session.run("m_claim_card", {"task_id": TASK, "agent_id": client_name(i), "from_seq": i + 1,
                                    "until_pt": 9_223_372_036_854_775_807,
                                    "rw": f"branch-lease-{i:02d}", "_branch": branch})
    return creates


class MergeScenario(_TaskRace):
    id = "o3.merge_agents"
    invariant = "I1A"
    kind = "merge"
    shapes = {"thread": ""}
    basis_ref = ("https://github.com/ModernRelay/omnigraph/blob/"
                 "b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/dev/merge.md")

    def setup(self, session, n):
        prepare_merge_fixture(session, n)

    def payload(self, shape, i, n):
        agent = client_name(i)
        source = f"agent/{agent}"
        return "merge_agent_branch", {"source": source}, {"task": TASK, "agent": agent, "source": source}

    def classify(self, reply):
        return OK, {"won": 1, "commit": reply.token}

    def observe(self, session, n):
        return session.dump_task(TASK)

    def check(self, ops, state, n):
        holders = state["holders"].get(TASK, [])
        records = state["lease_records"]
        lease = check_claim_lease(ops, holders, records)
        problems = []
        if len(holders) != 1:
            problems.append(f"holders {holders}, not exactly one")
        if len(records) != 1:
            problems.append(f"{len(records)} lease records, not exactly one")
        return typed_refusal_check(lease, ops, extra_problems=problems)

    def sequential_expected(self, ops, state, n):
        check = self.check(ops, state, n)
        winners = [op.input["agent"] for op in ops if op.outcome == OK]
        losers_typed = all(op.outcome == FAIL and (op.error or {}).get("type") in MERGE_REFUSALS
                           for op in ops[1:])
        return (check.held and winners == [client_name(0)] and losers_typed,
                "first merge and its lease, followed by typed conflicts",
                f"winners {winners}; {check.detail}")
