"""Invariant checkers (master blueprint section 5).

Each checker is a pure function of one trial's operations and its final
state. It never talks to an engine.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
import re

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


def check_claim_lease(ops: list[Op], holders: list[str], lease_records: list[dict] | None = None) -> Check:
    """I1 Form A for edge leases, including historical interval overlap.

    ``lease_records`` use half-open commit-order intervals: ``from_seq`` is
    inclusive and ``until_seq`` is exclusive; ``None`` means still live.
    Records for different tasks are independent.
    """
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

    malformed = []
    overlaps = []
    records = lease_records or []
    for record in records:
        if record.get("from_seq") is None:
            malformed.append(str(record.get("id", "?")))
    valid = [record for record in records if record.get("from_seq") is not None]
    for index, first in enumerate(valid):
        for second in valid[index + 1:]:
            if first.get("task") != second.get("task"):
                continue
            start_1, end_1 = first["from_seq"], first.get("until_seq")
            start_2, end_2 = second["from_seq"], second.get("until_seq")
            before_end_2 = end_2 is None or start_1 < end_2
            before_end_1 = end_1 is None or start_2 < end_1
            if before_end_2 and before_end_1:
                overlaps.append((str(first.get("id", "?")), str(second.get("id", "?"))))
    if malformed:
        problems.append(f"lease records without from_seq: {malformed}")
    if overlaps:
        problems.append(f"overlapping lease-record pairs: {overlaps}")

    witnesses = [op.op_id for op in winners]
    witnesses += malformed
    witnesses += [record_id for pair in overlaps for record_id in pair]
    witnesses = list(dict.fromkeys(witnesses)) if problems else []
    magnitude = max(len(winners), len(holders), 2 if overlaps else 0)
    detail = "; ".join(problems) if problems else f"{len(winners)} winner(s); lease holders {holders}"
    return Check("I1A", not problems, magnitude, "competing claims or leases", detail, witnesses)


_ISO_INSTANT = re.compile(r"^\d{4}-\d\d-\d\d[Tt ]\d\d:\d\d:\d\d(?:\.\d+)?(?:[Zz]|[+-]\d\d:\d\d)$")


def _canonical(value):
    """A sortable, hashable representation for an I4 result cell."""
    if value is None:
        return ("null",)
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, (int, float, Decimal)):
        try:
            number = Decimal(str(value))
            if number.is_finite():
                return ("number", number.normalize())
        except (ValueError, ArithmeticError):
            pass
        return ("number", str(value))
    if isinstance(value, str) and _ISO_INSTANT.match(value):
        try:
            instant = datetime.fromisoformat(value.replace("Z", "+00:00").replace("z", "+00:00"))
            return ("instant", instant.astimezone(timezone.utc).isoformat(timespec="microseconds"))
        except ValueError:
            pass
    if isinstance(value, dict):
        return ("object", tuple(sorted((str(key), _canonical(item)) for key, item in value.items())))
    if isinstance(value, (list, tuple)):
        return ("list", tuple(_canonical(item) for item in value))
    return (type(value).__name__, str(value))


def normalize_rows(rows: list[dict], *, ordered: bool = False):
    """Apply master section 5.4 normalisation to result rows.

    Row order is ignored as a multiset unless the query has an ordering clause;
    duplicate multiplicity always counts. Numbers and timestamp instants are
    canonicalised, recursively, before comparison.
    """
    canonical = [_canonical(row) for row in rows]
    return tuple(canonical) if ordered else Counter(canonical)


def check_equivalent_rows(results: dict[str, list[dict]], *, ordered: bool = False) -> Check:
    """I4 comparison for named engines after result normalisation."""
    if not results:
        return Check("I4", False, 0, "engine results", "no engine results were supplied")
    names = list(results)
    reference = names[0]
    expected = normalize_rows(results[reference], ordered=ordered)
    different = [name for name in names[1:] if normalize_rows(results[name], ordered=ordered) != expected]
    held = not different
    detail = (f"identical normalised results from {', '.join(names)}" if held else
              f"silently different normalised result: {', '.join(different)} differs from {reference}")
    return Check("I4", held, len(different), "different engines", detail, different)


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


def check_unique_keys(counts: dict[str, int], what: str, witnesses: dict[str, list[str]] | None = None,
                      invariant: str = "I1B") -> Check:
    """I1 Form B: every canonical key that exists exists exactly once."""
    duplicated = {key: count for key, count in counts.items() if count > 1}
    detail = (", ".join(f"{key} x{count}" for key, count in sorted(duplicated.items())) + f" ({what})"
              if duplicated else f"{len(counts)} {what}, one record each")
    found = [w for key in sorted(duplicated) for w in (witnesses or {}).get(key, [])]
    return Check(invariant, not duplicated, max(counts.values(), default=0), "records per key", detail, found)


def check_present(expected: list[str], present: set, what: str, invariant: str = "I2") -> Check:
    """I2 for memory layers: everything the acknowledged writes introduced is there."""
    missing = [item for item in expected if item not in present]
    detail = (f"{len(missing)} of {len(expected)} {what} missing: {missing[:5]}" if missing
              else f"all {len(expected)} {what} present")
    return Check(invariant, not missing, len(missing), f"missing {what}", detail, missing[:20])


def _moment(value):
    from datetime import datetime

    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def check_no_overlapping_current(versions: list[dict], what: str) -> Check:
    """I7a: no two current versions of one functional key overlap in valid time.

    Each version is {"label", "valid_at", "invalid_at", "current"}; ISO timestamps, None meaning open.
    """
    current = [v for v in versions if v["current"]]
    overlaps = []
    for i, first in enumerate(current):
        for second in current[i + 1:]:
            start_1, end_1 = _moment(first["valid_at"]), _moment(first["invalid_at"])
            start_2, end_2 = _moment(second["valid_at"]), _moment(second["invalid_at"])
            before_end_2 = end_2 is None or start_1 is None or start_1 < end_2
            before_end_1 = end_1 is None or start_2 is None or start_2 < end_1
            if before_end_2 and before_end_1:
                overlaps.append((first["label"], second["label"]))
    detail = (f"{len(current)} current versions of {what}; overlapping pairs: {overlaps[:5]}" if overlaps
              else f"{len(current)} current version(s) of {what}, none overlapping")
    return Check("I7A", not overlaps, len(current), "current versions", detail,
                 sorted({label for pair in overlaps for label in pair}))


def check_disjoint(ops: list[Op], props: dict) -> Check:
    """I2 for writes to disjoint properties of one node: every acknowledged write survives."""
    missing = [op for op in _winners(ops) if props.get(op.input.get("prop")) != op.input.get("v")]
    detail = (f"{len(missing)} of {len(_winners(ops))} acknowledged writes are missing" if missing
              else f"all {len(_winners(ops))} acknowledged writes survived")
    return Check("I2", not missing, len(missing), "lost writes", detail, [op.op_id for op in missing])
