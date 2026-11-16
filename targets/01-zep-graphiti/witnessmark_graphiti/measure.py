"""Pure measurement logic for G6-G8 (target blueprint section 5): no Graphiti, no engine, no Docker.

Kept apart from the instruments in observe.py so the unit tests can exercise it with the standard library alone.
"""

from __future__ import annotations

import re
from collections import Counter

READY_STATES = {"falkordb": "OPERATIONAL", "neo4j": "ONLINE"}
_PROGRESS = re.compile(r"^\[[^\]]*\]\s*[\d/]*\s*:?\s*")


def status_category(raw: str | None) -> str:
    """FalkorDB reports e.g. '[Indexing] 0/1000: UNDER CONSTRUCTION'; keep the state, drop the progress."""
    if raw is None:
        return "absent"
    text = _PROGRESS.sub("", str(raw)).strip().upper()
    return text or "UNKNOWN"


# --- index state ----------------------------------------------------------------------------------------------


def falkordb_index_keys(rows: list[dict]) -> set[tuple]:
    """One key per (entity type, label, field, index type) from db.indexes() rows."""
    keys = set()
    for row in rows:
        types = row.get("types") or {}
        for field, kinds in types.items():
            for kind in kinds if isinstance(kinds, (list, tuple)) else [kinds]:
                keys.add((str(row.get("entitytype")), str(row.get("label")), str(field), str(kind)))
    return keys


def neo4j_index_keys(rows: list[dict]) -> set[tuple]:
    return {(str(row.get("name")),) for row in rows}


def index_keys(backend: str, rows: list[dict]) -> set[tuple]:
    return falkordb_index_keys(rows) if backend == "falkordb" else neo4j_index_keys(rows)


def index_summary(backend: str, rows: list[dict], expected: set[tuple] | None) -> dict:
    """Counts of the index rows by state, and whether every expected index is present and ready."""
    ready_state = READY_STATES[backend]
    field = "status" if backend == "falkordb" else "state"
    states = Counter(status_category(row.get(field)) for row in rows)
    present = index_keys(backend, rows)
    missing = sorted(expected - present) if expected is not None else []
    relates = [row for row in rows if str(row.get("label") if backend == "falkordb" else row.get("name")) in
               ("RELATES_TO", "edge_name_and_fact")]
    if backend == "falkordb":
        relates = [row for row in relates if "FULLTEXT" in str(row.get("types"))]
    relates_state = status_category(relates[0].get(field)) if relates else "absent"
    return {
        "rows": len(rows),
        "states": dict(sorted(states.items())),
        "missing": len(missing),
        "relates_to_fulltext": relates_state,
        "ready": bool(rows) and not missing and all(status_category(row.get(field)) == ready_state for row in rows),
    }


def under_construction(summary: dict) -> bool:
    return any("CONSTRUCTION" in state or state == "POPULATING" for state in summary.get("states", {}))


# --- monitor samples ------------------------------------------------------------------------------------------


def sample_key(sample: dict) -> tuple:
    """What makes two consecutive samples the same observation."""
    return (sample.get("graph"), sample.get("error"), sample.get("probe_rows"), sample.get("probe_error"),
            tuple(sorted((sample.get("summary") or {}).get("states", {}).items())),
            (sample.get("summary") or {}).get("missing"), (sample.get("summary") or {}).get("relates_to_fulltext"),
            (sample.get("summary") or {}).get("ready"))


def compress(samples: list[dict]) -> list[dict]:
    """Runs of identical consecutive samples (per graph), each kept once with its count and first/last times."""
    runs: list[dict] = []
    open_run: dict[object, dict] = {}
    for sample in samples:
        graph = sample.get("graph")
        key = sample_key(sample)
        current = open_run.get(graph)
        if current is not None and current["_key"] == key:
            current["samples"] += 1
            current["ret"] = sample["ret"]
            current["ret_ns"] = sample.get("ret_ns")
            continue
        run = {**sample, "samples": 1, "_key": key}
        runs.append(run)
        open_run[graph] = run
    for run in runs:
        run.pop("_key", None)
    return runs


def first_ready_ns(samples: list[dict], graph=None) -> int | None:
    for sample in samples:
        if sample.get("graph") == graph and (sample.get("summary") or {}).get("ready"):
            return sample["inv_ns"]
    return None


def state_before(samples: list[dict], at_ns: int, graph=None) -> dict | None:
    """The last sample of ``graph`` that finished before ``at_ns``."""
    found = None
    for sample in samples:
        if sample.get("graph") == graph and sample["ret_ns"] <= at_ns:
            found = sample
    return found


def _not_ready_kind(sample: dict) -> str:
    if sample.get("error"):
        return "error"
    summary = sample.get("summary") or {}
    if under_construction(summary):
        return "under construction"
    if summary.get("missing"):
        return "missing"
    return "not ready"


def uc_report(samples: list[dict], builds: list[dict], graph=None, database: str | None = None) -> dict:
    """KD-F4: how long the indexes stayed not ready after the first completed build on ``database`` returned.

    Sampling is discrete, so the answer is a pair of bounds: at least until the last sample that still saw them not
    ready was invoked, at most until the first ready sample returned. Both are 0 when they were ready first.
    """
    mine = [s for s in samples if s.get("graph") == graph]
    ready_at = next((i for i, s in enumerate(mine) if (s.get("summary") or {}).get("ready")), None)
    done = sorted(b["ret_ns"] for b in builds if b.get("database") == database and b.get("outcome") == "ok"
                  and b.get("ret_ns") is not None)
    uc = [s for s in mine if under_construction(s.get("summary") or {})]
    rows_uc = [s["probe_rows"] for s in uc if isinstance(s.get("probe_rows"), int)]
    bounds, kinds = None, []
    if ready_at is not None and done:
        before = mine[:ready_at]
        after_done = [s for s in before if s["inv_ns"] >= done[0]]
        kinds = sorted({_not_ready_kind(s) for s in after_done})
        at_least = (after_done[-1]["inv_ns"] - done[0]) / 1e6 if after_done else 0.0
        at_most = max(0.0, (mine[ready_at]["ret_ns"] - done[0]) / 1e6)
        bounds = {"at_least_ms": round(at_least, 3), "at_most_ms": round(max(at_most, at_least), 3)}
    return {
        "not_ready_after_creation_ms": bounds,
        "not_ready_after_creation_kinds": kinds,
        "builds_completed_on_graph": len(done),
        "under_construction_seen": bool(uc),
        "under_construction_samples": sum(s.get("samples", 1) for s in uc),
        "under_construction_span_ms": (round((mine[ready_at]["inv_ns"] - uc[0]["inv_ns"]) / 1e6, 3)
                                       if uc and ready_at is not None else None),
        "probe_rows_while_under_construction": {"min": min(rows_uc), "max": max(rows_uc)} if rows_uc else None,
        "probe_errors_while_under_construction": sum(1 for s in uc if s.get("probe_error")),
        "ready_seen": ready_at is not None,
        "samples": len(mine),
    }


# --- recovery after a stalled search ----------------------------------------------------------------------------

#: Queries the harness itself runs while it looks for and ends leftover transactions.
OWN_QUERIES = ("SHOW TRANSACTIONS", "TERMINATE TRANSACTIONS")


def leftover_transactions(rows: list[dict]) -> list[str]:
    """The ids of server transactions to end after a stall: every open one except the harness's own lookup."""
    return sorted(str(row["transactionId"]) for row in rows
                  if not str(row.get("currentQuery") or "").lstrip().upper().startswith(OWN_QUERIES))


# --- answers --------------------------------------------------------------------------------------------------


def classify(answer: dict, control: list[str]) -> str:
    """identical | different | error, comparing answers as multisets (master blueprint section 5.4)."""
    if answer.get("error"):
        return "error"
    return "identical" if Counter(answer.get("facts") or []) == Counter(control) else "different"


def suite_summary(answers: list[dict], control: dict[str, list[str]]) -> dict:
    kinds = Counter(classify(answer, control.get(answer["query"], [])) for answer in answers)
    order = sum(1 for answer in answers if not answer.get("error") and answer.get("facts") != control.get(answer["query"])
                and classify(answer, control.get(answer["query"], [])) == "identical")
    return {"queries": len(answers), "identical": kinds["identical"], "different": kinds["different"],
            "errors": kinds["error"], "order_only": order,
            "error_types": dict(sorted(Counter(a["error"]["type"] for a in answers if a.get("error")).items()))}


# --- G7 -------------------------------------------------------------------------------------------------------


def items(state: dict) -> dict[str, set]:
    """The comparable items of a Graphiti dump: episodes, entity names, fact texts."""
    return {"episodes": set(state.get("episodes", [])),
            "entities": {entity["name"] for entity in state.get("entities", [])},
            "facts": {fact["fact"] for fact in state.get("facts", [])}}


def lost_items(before: dict, after: dict) -> dict:
    a, b = items(before), items(after)
    lost = {kind: sorted(a[kind] - b[kind]) for kind in a}
    return {"lost": {kind: len(values) for kind, values in lost.items()},
            "lost_total": sum(len(values) for values in lost.values()),
            "examples": {kind: values[:3] for kind, values in lost.items() if values},
            "before": {kind: len(values) for kind, values in a.items()},
            "after": {kind: len(values) for kind, values in b.items()}}
