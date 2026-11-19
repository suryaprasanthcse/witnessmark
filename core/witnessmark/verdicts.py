"""Verdicts and control records (master blueprint sections 5.8 and 6.2)."""

from __future__ import annotations

import statistics


def summarize(values: list[float]) -> dict:
    if not values:
        return {}
    return {"min": min(values), "median": statistics.median(values), "max": max(values)}


def percentile(values: list[float], q: float) -> float | None:
    """Nearest-rank percentile, q in (0, 100]."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, min(len(ordered), -(-int(q * len(ordered)) // 100)))
    return ordered[rank - 1]


def verdict(invariant: str, trials: list[dict], sequential_met: bool, expectation, unit: str) -> dict:
    valid = [trial for trial in trials if trial["valid"]]
    violating = [trial for trial in valid if not trial["checks"][0]["held"]]
    if not sequential_met or not valid:
        status = "INVALID"
    elif not violating:
        status = "PASS"
    elif expectation.known_deviation:
        status = "KNOWN_DEVIATION"
    else:
        status = "FAIL"
    record = {
        "invariant": invariant,
        "status": status,
        "trials_violating": len(violating),
        "trials_valid": len(valid),
        "magnitude": {**summarize([trial["checks"][0]["magnitude"] for trial in valid]), "unit": unit},
        "basis": expectation.basis,
        "basis_ref": expectation.basis_ref,
        "witnesses": [w for trial in violating[:3] for w in trial["checks"][0]["witnesses"]],
    }
    if expectation.known_deviation:
        record["note"] = f"known deviation {expectation.known_deviation} (master blueprint section 7.5)"
    if not sequential_met:
        record["note"] = "the sequential control failed, so nothing may be claimed"
    return record


DECLARED_TRIALS = "declared trials"
CHECKING_CASES = "cases checking the invariant"


def sufficiency(declared: int, valid: int, counted: str) -> dict:
    """Master §9.7: a verdict on fewer than half of its declared count reads as insufficient valid trials."""
    return {"declared": declared, "valid": valid, "sufficient": valid * 2 >= declared, "counted": counted}


def add_sufficiency(manifest: dict) -> dict:
    """Add §9.7's `sufficiency` field to every verdict of a manifest about to be written. `status` is kept as computed.

    The count is read from the manifest. A case suite, whose trials carry a `case` id, judges each invariant only in
    the cases that check it, so its count is those trials (valid or not); every other run counts `scenario.trials`.
    A manifest without a verdict list (a measurement run, §9.2) is left as it is.
    """
    verdicts = manifest.get("verdicts")
    if not isinstance(verdicts, list):
        return manifest
    trials = manifest.get("trials") or []
    case_suite = any(trial.get("case") for trial in trials)
    for record in verdicts:
        if case_suite:
            declared = sum(1 for trial in trials
                           if any(check.get("invariant") == record["invariant"] for check in trial.get("checks") or []))
            record["sufficiency"] = sufficiency(declared, record["trials_valid"], CHECKING_CASES)
        else:
            record["sufficiency"] = sufficiency(manifest["scenario"]["trials"], record["trials_valid"], DECLARED_TRIALS)
    return manifest


def role_control(role: str, configuration: str, trials: list[dict]) -> dict:
    valid = [trial for trial in trials if trial["valid"]]
    violating = sum(1 for trial in valid if not trial["checks"][0]["held"])
    if role == "negative":
        expected, met = f"no violation in {len(valid)} valid trials", violating == 0
    elif role == "positive":
        expected, met = f"at least one violation in {len(valid)} valid trials", violating >= 1
    else:
        raise ValueError(f"unknown control role {role!r}")
    return {
        "kind": role,
        "configuration": configuration,
        "expected": expected,
        "observed": f"{violating} of {len(valid)} valid trials violated the invariant",
        "met": bool(met and valid),
    }
