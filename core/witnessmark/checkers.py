"""Invariant checkers (master blueprint section 5).

Each checker is a pure function of one trial's operations and its final
state. It never talks to an engine.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .history import OK, UNKNOWN, Op


@dataclass
class Check:
    invariant: str
    held: bool
    magnitude: float
    unit: str
    detail: str
    witnesses: list[str] = field(default_factory=list)

    def to_json(self) -> dict:
        return {
            "invariant": self.invariant,
            "held": self.held,
            "magnitude": self.magnitude,
            "unit": self.unit,
            "detail": self.detail,
            "witnesses": self.witnesses,
        }


def _winners(ops: list[Op]) -> list[Op]:
    return [op for op in ops if op.outcome == OK]


def _unknown_agents(ops: list[Op]) -> set:
    return {op.input.get("agent") for op in ops if op.outcome == UNKNOWN}


def check_claim_state(ops: list[Op], task: dict) -> Check:
    """I1 Form A for a claim guarded by the task's own state.

    (a) at most one acknowledged winner; (b) a lone winner is the final
    holder; (c) with no winner, the task is unheld or held by a claimant
    whose outcome is unknown.
    """
    winners = _winners(ops)
    state, holder = task.get("state"), task.get("holder")
    problems = []
    if len(winners) > 1:
        problems.append(f"{len(winners)} clients were told they won")
    elif len(winners) == 1:
        winner = winners[0].input.get("agent")
        if state != "claimed" or holder != winner:
            problems.append(f"the winner {winner} is not the final holder (state {state!r}, holder {holder!r})")
    elif state == "claimed" and holder not in _unknown_agents(ops):
        problems.append(f"no client won, yet the task is held by {holder!r}")
    witnesses = [op.op_id for op in winners] if problems else []
    detail = "; ".join(problems) if problems else f"{len(winners)} winner(s); final holder {holder!r}"
    return Check("I1A", not problems, len(winners), "winners", detail, witnesses)


def check_claim_lease(ops: list[Op], holders: list[str]) -> Check:
    """I1 Form A for a lease held as an edge: (a)–(c) as above, plus (d) at most one live lease."""
    winners = _winners(ops)
    problems = []
    if len(winners) > 1:
        problems.append(f"{len(winners)} clients were told they won")
    if len(holders) > 1:
        problems.append(f"{len(holders)} live leases on one task")
    if len(winners) == 1 and holders != [winners[0].input.get("agent")]:
        problems.append(f"the winner {winners[0].input.get('agent')} does not hold the only lease (holders {holders})")
    if not winners and holders and not set(holders) <= _unknown_agents(ops):
        problems.append(f"no client won, yet leases are held by {holders}")
    witnesses = [op.op_id for op in winners] if problems else []
    magnitude = max(len(winners), len(holders))
    detail = "; ".join(problems) if problems else f"{len(winners)} winner(s); lease holders {holders}"
    return Check("I1A", not problems, magnitude, "winners", detail, witnesses)


def check_counter(ops: list[Op], value: int) -> Check:
    """I2 for increments: the final value lies in [acknowledged, acknowledged + unknown].

    Two acknowledged increments that returned the same value witness a lost update.
    """
    acknowledged = _winners(ops)
    unknown = sum(1 for op in ops if op.outcome == UNKNOWN)
    lost = max(0, len(acknowledged) - value)
    extra = max(0, value - len(acknowledged) - unknown)
    by_value: dict = defaultdict(list)
    for op in acknowledged:
        returned = (op.result or {}).get("v")
        by_value[returned].append(op.op_id)
    witnesses = [op_id for ids in by_value.values() if len(ids) > 1 for op_id in ids]
    problems = []
    if lost:
        problems.append(f"{len(acknowledged)} acknowledged increments, final value {value}: {lost} lost")
    if extra:
        problems.append(f"final value {value} exceeds {len(acknowledged)} acknowledged plus {unknown} unknown")
    detail = "; ".join(problems) if problems else f"{len(acknowledged)} acknowledged increments, final value {value}"
    return Check("I2", not problems, lost, "lost updates", detail, witnesses if problems else [])


def check_disjoint(ops: list[Op], props: dict) -> Check:
    """I2 for writes to disjoint properties of one node: every acknowledged write survives."""
    missing = [op for op in _winners(ops) if props.get(op.input.get("prop")) != op.input.get("v")]
    detail = (f"{len(missing)} of {len(_winners(ops))} acknowledged writes are missing" if missing
              else f"all {len(_winners(ops))} acknowledged writes survived")
    return Check("I2", not missing, len(missing), "lost writes", detail, [op.op_id for op in missing])
