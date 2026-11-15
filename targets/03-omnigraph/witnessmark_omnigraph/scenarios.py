"""No-run scaffolding for Omnigraph scenarios O2, O3 and O6.

The classes follow :class:`witnessmark.memory.RaceScenario`: ``clients``
declares one isolated database client per item, ``check`` consumes only history
and final state, and ``sequential_expected`` describes the phase-2 control.

For claim checks, ``states["main"]`` has ``holders`` (task id to agent-id list)
and ``lease_records`` (I1A half-open commit-sequence intervals). O6 states are
engine to query to either ``{"outcome": "ok", "rows": [...]}`` or a rejected
observation. Phase 2 runner wiring will produce these canonical observations.
"""

from __future__ import annotations

from witnessmark.checkers import Check, check_claim_lease, check_equivalent_rows
from witnessmark.history import FAIL, OK
from witnessmark.memory import RaceScenario

PIN = "b2dbaff7584eb849a98fa139876e0ae474e929ea"
SERVER_DOC = f"https://github.com/ModernRelay/omnigraph/blob/{PIN}/docs/user/operations/server.md"
SCHEMA_DOC = f"https://github.com/ModernRelay/omnigraph/blob/{PIN}/docs/user/schema/index.md"
MERGE_DOC = f"https://github.com/ModernRelay/omnigraph/blob/{PIN}/docs/user/branches/merge.md"

CLIENTS = 50
TASK = "task-0"


def _main(states: dict) -> dict:
    return states.get("main", {})


def _holders(states: dict, task: str) -> list[str]:
    holders = _main(states).get("holders", {})
    return list(holders.get(task, []))


def _leases(states: dict, task: str) -> list[dict]:
    return [record for record in _main(states).get("lease_records", []) if record.get("task") == task]


def _typed_refusals(ops, allowed: set[str]) -> Check:
    bad = []
    for op in ops:
        if op.outcome == OK:
            continue
        kind = (op.error or {}).get("kind")
        if op.outcome != FAIL or kind not in allowed:
            bad.append(op)
    expected = ", ".join(sorted(allowed))
    detail = (f"all non-winners were typed refusals ({expected})" if not bad else
              f"{len(bad)} non-winner outcome(s) were not typed refusals ({expected})")
    return Check("DOC", not bad, len(bad), "unexpected outcomes", detail, [op.op_id for op in bad])


class _OneTaskClaims(RaceScenario):
    invariants = ("I1A",)
    support = "supported"
    basis = "documented"
    basis_ref = SERVER_DOC
    entry = ""
    refusal_kinds: set[str] = set()

    def params(self):
        return {"clients": CLIENTS, "trials": 20, "task": TASK, "branch": "main", "entry": self.entry}

    def clients(self):
        return [("main", {"entry": self.entry, "task": TASK, "agent": f"c{i:02d}"})
                for i in range(CLIENTS)]

    def check(self, ops, states):
        checks = [check_claim_lease(ops, _holders(states, TASK), _leases(states, TASK))]
        if self.refusal_kinds:
            checks.append(_typed_refusals(ops, self.refusal_kinds))
        return checks

    def sequential_expected(self, ops, states):
        checks = self.check(ops, states)
        return all(check.held for check in checks), "one winner, its live lease, no overlapping lease records", \
            "; ".join(check.detail for check in checks)


class O2AConditionalClaims(_OneTaskClaims):
    """O2a: all clients read one head then conditionally claim one task."""

    id = "o2a.conditional_one_task"
    entry = "read_then_claim_cond"
    refusal_kinds = {"precondition_failure"}


class O2BDisjointConditionalClaims(RaceScenario):
    """O2b: logically disjoint claims expose branch-wide false-conflict cost."""

    id = "o2b.conditional_disjoint_tasks"
    invariants = ("I1A",)
    support = "supported"
    basis = "documented"
    basis_ref = SERVER_DOC

    def params(self):
        return {"clients": CLIENTS, "tasks": CLIENTS, "branch": "main", "retry_preconditions": True}

    def clients(self):
        return [("main", {"entry": "read_then_claim_cond_until_definite", "task": f"task-{i}",
                          "agent": f"c{i:02d}"}) for i in range(CLIENTS)]

    def check(self, ops, states):
        checks = []
        for op in ops:
            task = op.input["task"]
            checks.append(check_claim_lease([op], _holders(states, task), _leases(states, task)))
        return checks

    def sequential_expected(self, ops, states):
        checks = self.check(ops, states)
        return all(check.held for check in checks), "all 50 disjoint tasks held by their claimant", \
            f"{sum(check.held for check in checks)} of {len(checks)} task checks held"


class O2CCardinalityClaims(_OneTaskClaims):
    """O2c: the HeldBy ``@card(0..1)`` constraint arbitrates the race."""

    id = "o2c.cardinality_one_task"
    entry = "claim_card"
    basis_ref = SCHEMA_DOC
    refusal_kinds = {"CardinalityViolation"}


class O3BranchMerge(_OneTaskClaims):
    """O3: claim on one branch per agent, then merge into main."""

    entry = "claim_branch_then_merge"
    refusal_kinds = {"CardinalityViolation", "DivergentInsert", "DivergentUpdate", "DeleteVsUpdate"}
    basis_ref = MERGE_DOC

    def __init__(self, concurrent: bool):
        self.concurrent = concurrent
        self.id = f"o3.branch_merge.{'concurrent' if concurrent else 'sequential'}"

    def params(self):
        params = super().params()
        params.update({"branches": CLIENTS, "merge_mode": "concurrent" if self.concurrent else "sequential"})
        return params

    def clients(self):
        return [("main", {"entry": self.entry, "task": TASK, "agent": f"c{i:02d}",
                          "branch": f"agent/c{i:02d}", "concurrent_merge": self.concurrent})
                for i in range(CLIENTS)]


class O6TraversalParity(RaceScenario):
    """O6: compare GQ traversal rows with both Cypher baselines."""

    id = "o6.traversal_parity"
    invariants = ("I4",)
    support = "supported"
    basis = "documented"
    basis_ref = SERVER_DOC
    ENGINES = ("omnigraph", "falkordb", "neo4j")
    QUERIES = (("q_eligible", True), ("q_live", False))

    def clients(self):
        return [(engine, {"entry": "parity_query", "engine": engine, "query": query})
                for query, _ in self.QUERIES for engine in self.ENGINES]

    def check(self, ops, states):
        checks = []
        for query, ordered in self.QUERIES:
            observations = {engine: states.get(engine, {}).get(query) for engine in self.ENGINES}
            rejected = [engine for engine, observation in observations.items()
                        if not isinstance(observation, dict) or observation.get("outcome") != "ok"]
            if rejected:
                checks.append(Check("I4", False, len(rejected), "rejected engines",
                                    f"{query} rejected by {', '.join(rejected)}", rejected))
                continue
            rows = {engine: observations[engine].get("rows", []) for engine in self.ENGINES}
            check = check_equivalent_rows(rows, ordered=ordered)
            check.detail = f"{query}: {check.detail}"
            checks.append(check)
        return checks

    def sequential_expected(self, ops, states):
        checks = self.check(ops, states)
        return all(check.held for check in checks), "both queries identical across all three engines", \
            "; ".join(check.detail for check in checks)


SCENARIOS = (
    O2AConditionalClaims(),
    O2BDisjointConditionalClaims(),
    O2CCardinalityClaims(),
    O3BranchMerge(concurrent=False),
    O3BranchMerge(concurrent=True),
    O6TraversalParity(),
)
