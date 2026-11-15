"""Omnigraph scenarios adapted to the core thread runner contract."""

from __future__ import annotations

from witnessmark.checkers import Check, check_claim_lease
from witnessmark.history import FAIL, OK
from witnessmark.scenarios import Scenario, client_name

from .engine import OmnigraphSession
from .scenarios import SCHEMA_DOC, SERVER_DOC

TASK = "task-0"
SKILL = "skill-0"
MERGE_REFUSALS = frozenset({"CardinalityViolation", "DivergentInsert", "DivergentUpdate", "DeleteVsUpdate"})


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
        unexpected = [op for op in ops if op.outcome != OK and
                      (op.outcome != FAIL or (op.error or {}).get("type") not in self.allowed_refusals)]
        if not unexpected:
            return base
        return Check("I1A", False, max(base.magnitude, len(unexpected)), base.unit,
                     f"{base.detail}; {len(unexpected)} non-winner outcome(s) were not typed refusals "
                     f"{sorted(self.allowed_refusals)}",
                     list(dict.fromkeys(base.witnesses + [op.op_id for op in unexpected])))

    def sequential_expected(self, ops, state, n):
        winners = [op.input.get("agent") for op in ops if op.outcome == OK]
        holders = state["holders"].get(TASK, [])
        check = self.check(ops, state, n)
        met = winners == [client_name(0)] and holders == [client_name(0)] and check.held
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
        lease = check_claim_lease(ops, holders, state["lease_records"])
        unexpected = [op.op_id for op in ops if op.outcome == FAIL
                      and (op.error or {}).get("type") not in MERGE_REFUSALS]
        if lease.held and not unexpected and len(holders) == 1 and len(state["lease_records"]) == 1:
            return lease
        detail = f"{lease.detail}; holders {holders}; unexpected merge refusals {unexpected}"
        return Check(self.invariant, False, max(1, lease.magnitude, len(unexpected)), lease.unit,
                     detail, list(dict.fromkeys(lease.witnesses + unexpected)))

    def sequential_expected(self, ops, state, n):
        check = self.check(ops, state, n)
        winners = [op.input["agent"] for op in ops if op.outcome == OK]
        losers_typed = all(op.outcome == FAIL and (op.error or {}).get("type") in MERGE_REFUSALS
                           for op in ops[1:])
        return (check.held and winners == [client_name(0)] and losers_typed,
                "first merge and its lease, followed by typed conflicts",
                f"winners {winners}; {check.detail}")
