"""The reporter: every table is rebuilt from evidence/ alone (master blueprint sections 9.6 and 10)."""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

from .verdicts import percentile


def load_runs(evidence_root: Path) -> list[dict]:
    runs = []
    for path in sorted(Path(evidence_root).rglob("run.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["_dir"] = path.parent.as_posix()
        runs.append(manifest)
    return runs


def latest_batch(runs: list[dict]) -> str | None:
    batches = sorted({(run.get("started_at", ""), run.get("batch")) for run in runs if run.get("batch")})
    return batches[-1][1] if batches else None


def in_batch(runs: list[dict], batch: str | None) -> list[dict]:
    selected = [run for run in runs if batch is None or run.get("batch") == batch]
    return sorted(selected, key=lambda run: run.get("started_at", ""))


def _control(run: dict, kind: str) -> dict | None:
    return next((control for control in run.get("controls", []) if control["kind"] == kind), None)


def _role_control(run: dict) -> dict | None:
    return next((c for c in run.get("controls", []) if c["kind"] in ("negative", "positive")), None)


def _fmt(value) -> str:
    if value is None:
        return "–"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def spreads(runs: list[dict]) -> list[float]:
    return [trial["release_spread_ms"] for run in runs for trial in run.get("trials", []) if trial.get("valid")]


def runs_table(runs: list[dict]) -> str:
    lines = [
        "| Engine | Scenario | Role | Sequential control | Role control | Violating trials | Magnitude (min / median / max) | Release spread p50 / max (ms) | Verdict | Run |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for run in runs:
        verdict = run["verdicts"][0]
        sequential = _control(run, "sequential")
        role = _role_control(run)
        magnitude = verdict.get("magnitude", {})
        run_spreads = [t["release_spread_ms"] for t in run.get("trials", []) if t.get("valid")]
        lines.append(
            "| {engine} | {scenario} | {role} | {seq} | {rolec} | {viol} of {valid} | {mmin} / {mmed} / {mmax} {unit} | {p50} / {pmax} | {status} | `{run_id}` |".format(
                engine=run["components"][0].get("name", run["target"]["name"]),
                scenario=run["scenario"]["id"],
                role=run.get("expectation", {}).get("role", "–"),
                seq="met" if sequential and sequential["met"] else "NOT met",
                rolec="met" if role and role["met"] else "NOT met",
                viol=verdict["trials_violating"],
                valid=verdict["trials_valid"],
                mmin=_fmt(magnitude.get("min")),
                mmed=_fmt(magnitude.get("median")),
                mmax=_fmt(magnitude.get("max")),
                unit=magnitude.get("unit", ""),
                p50=_fmt(percentile(run_spreads, 50)),
                pmax=_fmt(max(run_spreads) if run_spreads else None),
                status=verdict["status"],
                run_id=run["run_id"],
            )
        )
    return "\n".join(lines)


def _where(run: dict) -> tuple[str, str]:
    """(build, backend) of a memory run, from its target record and components."""
    sut = next((c for c in run.get("components", []) if c.get("role") == "sut"), {})
    config = sut.get("config", {})
    backend = config.get("backend", "?")
    if config.get("falkordb_pool") == "default":
        backend += " (default pool)"
    return run["target"].get("ref", "?"), backend


def _verdict_cell(verdict: dict) -> str:
    cell = f"{verdict['invariant']} {verdict['status']} {verdict['trials_violating']}/{verdict['trials_valid']}"
    magnitude = verdict.get("magnitude", {})
    if verdict["trials_violating"] and magnitude.get("max") is not None:
        cell += f" (max {_fmt(magnitude['max'])} {magnitude.get('unit', '')})"
    return cell


def race_table(runs: list[dict]) -> str:
    lines = ["| Build | Backend | Scenario | Sequential control | Overlap control | Verdicts | Run |",
             "|---|---|---|---|---|---|---|"]
    for run in runs:
        build, backend = _where(run)
        sequential = _control(run, "sequential") or {}
        overlap = _control(run, "overlap") or {}
        lines.append(f"| {build} | {backend} | {run['scenario']['id']} | {'met' if sequential.get('met') else 'NOT met'} "
                     f"| {overlap.get('observed', '–')} | {'; '.join(_verdict_cell(v) for v in run['verdicts'])} "
                     f"| `{run['run_id']}` |")
    return "\n".join(lines)


def cases_table(runs: list[dict]) -> str:
    """One row per case-suite run; each cell names the checks that failed for that case."""
    cases = []
    for run in runs:
        for trial in run["trials"]:
            if trial.get("case") and trial["case"] not in cases:
                cases.append(trial["case"])
    lines = ["| Build | Backend | Suite | " + " | ".join(cases) + " | Run |",
             "|---|---|---|" + "---|" * len(cases) + "---|"]
    for run in runs:
        build, backend = _where(run)
        cells = []
        for case in cases:
            trial = next((t for t in run["trials"] if t.get("case") == case), None)
            if trial is None:
                cells.append("–")
                continue
            failed = sorted({c["invariant"] for c in trial["checks"] if not c["held"]})
            cells.append("ok" if not failed else ("not valid" if not trial["valid"] else ", ".join(failed)))
        lines.append(f"| {build} | {backend} | {run['scenario']['id']} | " + " | ".join(cells)
                     + f" | `{run['run_id']}` |")
    return "\n".join(lines)


def visibility_table(runs: list[dict]) -> str:
    lines = ["| Build | Backend | Writes | Seen on the first search, same instance | Seen on the first search, second "
             "instance | Longest lag (ms) | Run |", "|---|---|---|---|---|---|---|"]
    for run in runs:
        build, backend = _where(run)
        same = [c for t in run["trials"] for c in t["checks"] if c["detail"].startswith("same instance")]
        other = [c for t in run["trials"] for c in t["checks"] if c["detail"].startswith("second instance")]
        longest = max((c["magnitude"] for c in same + other), default=None)
        lines.append(f"| {build} | {backend} | {len(run['trials'])} | {sum(c['held'] for c in same)} of {len(same)} "
                     f"| {sum(c['held'] for c in other)} of {len(other)} | {_fmt(longest)} | `{run['run_id']}` |")
    return "\n".join(lines)


# Columns of a target's invariants table (target blueprints, section 3): (heading, invariant, unit filter).
INVARIANT_COLUMNS = (
    ("Duplicate entities (I1B)", "I1B", "records per key"),
    ("Duplicate vector ids (I1B)", "I1B", "rows per vector id"),
    ("Artefacts in one store only (I4)", "I4", None),
    ("Lost acknowledged items (I2)", "I2", None),
    ("Deletion permanence (I5)", "I5", None),
)


def _column_cell(run: dict, invariant: str, unit: str | None) -> str:
    """k of T over valid trials that carry the check; "–" when the run has none."""
    carrying = violating = 0
    for trial in run.get("trials", []):
        if not trial.get("valid"):
            continue
        mine = [c for c in trial.get("checks", []) if c["invariant"] == invariant
                and (unit is None or c.get("unit") == unit)]
        if mine:
            carrying += 1
            violating += any(not c["held"] for c in mine)
    return f"{violating}/{carrying}" if carrying else "–"


def _ladder_cells(run: dict) -> tuple[str, str]:
    ladder = run.get("ladder")
    if not ladder:
        return "–", "–"
    crash = ladder.get("crash")
    ceiling = f"crash at {crash['documents_committed']} ({crash['kind']})" if crash \
        else f"none up to {ladder.get('documents')}"
    reopen = ladder.get("reopen") or {}
    parts = []
    for mode in ("read_only", "read_write"):
        value = reopen.get(mode)
        if isinstance(value, dict):
            parts.append(f"{mode.replace('_', '-')} {'yes' if value.get('opened') else 'no'}")
        elif value:
            parts.append(f"{mode.replace('_', '-')} {value}")
    return ceiling, "; ".join(parts) or "–"


def invariants_table(runs: list[dict]) -> str:
    """One row per run: each cell is k of T valid trials with a violation; the run id is in the last column."""
    heads = [h for h, _, _ in INVARIANT_COLUMNS] + ["Crash ceiling (documents)", "Store reopens after the run"]
    lines = ["| Build | Backend | Scenario | Valid trials | " + " | ".join(heads) + " | Run |",
             "|---|---|---|---|" + "---|" * len(heads) + "---|"]
    for run in runs:
        build, backend = _where(run)
        trials = run.get("trials", [])
        cells = [_column_cell(run, inv, unit) for _, inv, unit in INVARIANT_COLUMNS] + list(_ladder_cells(run))
        lines.append(f"| {build} | {backend} | {run['scenario']['id']} | "
                     f"{sum(1 for t in trials if t.get('valid'))}/{len(trials)} | " + " | ".join(cells)
                     + f" | `{run['run_id']}` |")
    return "\n".join(lines)


def extra_checks_table(runs: list[dict]) -> str | None:
    """Checks outside a run's invariants (error classes, writer conflicts, crashes), over all trials."""
    lines = ["| Backend | Scenario | Check | Trials where it did not hold | Details (first trials) | Run |",
             "|---|---|---|---|---|---|"]
    found = False
    for run in runs:
        _, backend = _where(run)
        own = set(run["scenario"].get("invariants", []))
        labels: dict[str, list] = {}
        for trial in run.get("trials", []):
            for check in trial.get("checks", []):
                if check["invariant"] not in own:
                    labels.setdefault(check["invariant"], []).append(check)
        for label, checks in sorted(labels.items()):
            found = True
            failed = [c for c in checks if not c["held"]]
            details = sorted({c["detail"][:90] for c in failed})[:3]
            lines.append(f"| {backend} | {run['scenario']['id']} | {label} | {len(failed)} of {len(checks)} | "
                         f"{'; '.join(details).replace('|', '/') or '–'} | `{run['run_id']}` |")
    return "\n".join(lines) if found else None


def support_boundaries_table(runs: list[dict]) -> str | None:
    lines = ["| Build | Backend | Scenario | Valid trials | Dominant ERR class | Run |",
             "|---|---|---|---|---|---|"]
    for run in runs:
        trials = run.get("trials", [])
        if run.get("expectation", {}).get("support") != "boundary" or not trials:
            continue
        sequential = _control(run, "sequential")
        if sequential is not None and sequential.get("met") is False:
            continue
        if any(trial.get("valid") for trial in trials):
            continue
        errors: Counter[str] = Counter()
        for trial in trials:
            for check in trial.get("checks", []):
                if check["invariant"] != "ERR" or check["held"]:
                    continue
                for entry in check["detail"].split("; "):
                    label, _, count = entry.rpartition(" x")
                    if label and count.isdecimal():
                        errors[label] += int(count)
        if not errors:
            continue
        dominant = errors.most_common(1)[0][0].replace("|", "/")
        build, backend = _where(run)
        lines.append(f"| {build} | {backend} | {run['scenario']['id']} | 0 of {len(trials)} | "
                     f"{dominant} | `{run['run_id']}` |")
    return "\n".join(lines) if len(lines) > 2 else None


def invalid_table(runs: list[dict]) -> str | None:
    lines = ["| Backend | Scenario | Invalid trials | Reasons (distinct, first three) | Run |", "|---|---|---|---|---|"]
    found = False
    for run in runs:
        bad = [t for t in run.get("trials", []) if not t.get("valid")]
        if not bad:
            continue
        found = True
        _, backend = _where(run)
        reasons = sorted({(t.get("invalid_reason") or "?")[:110] for t in bad})[:3]
        lines.append(f"| {backend} | {run['scenario']['id']} | {len(bad)} of {len(run['trials'])} | "
                     f"{'; '.join(reasons).replace('|', '/')} | `{run['run_id']}` |")
    return "\n".join(lines) if found else None


def omnigraph_cost_table(runs: list[dict]) -> str:
    lines = [
        "| Build | Storage | Nodes / edges | Siblings | Create median [IQR] (ms) | Stall median (ms) | Reader p99 before / during (ms) | Merge / delete median (ms) | Object requests / bytes, one create + delete | Run |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for run in runs:
        build, storage = _where(run)
        for trial in run.get("trials", []):
            samples = trial.get("samples", [])
            create = [s["create_ms"] for s in samples if s.get("create_ms") is not None]
            stalls = [s["stall_ms"] for s in samples if s.get("stall_ms") is not None]
            before = [s["reader_p99_before_ms"] for s in samples if s.get("reader_p99_before_ms") is not None]
            during = [s["reader_p99_during_ms"] for s in samples if s.get("reader_p99_during_ms") is not None]
            merges = [s["merge_unchanged_ms"] for s in samples if s.get("merge_unchanged_ms") is not None]
            deletes = [s["delete_ms"] for s in samples if s.get("delete_ms") is not None]
            timing = "–"
            if create and trial.get("timing_kind") == "timing":
                timing = f"{_fmt(percentile(create, 50))} [{_fmt(percentile(create, 25))}–{_fmt(percentile(create, 75))}]"
            counts = trial.get("object_store_counts") or {}
            methods = counts.get("methods", counts)
            requests = sum(v.get("requests", 0) for v in methods.values() if isinstance(v, dict))
            byte_count = sum(v.get("request_bytes", 0) + v.get("response_bytes", 0)
                             for v in methods.values() if isinstance(v, dict))
            count_cell = f"{requests} / {byte_count}" if counts else "–"
            lines.append(f"| {build} | {storage} | {trial.get('size')} / {trial.get('size')} | {trial.get('siblings')} | "
                         f"{timing} | {_fmt(percentile(stalls, 50))} | {_fmt(percentile(before, 50))} / "
                         f"{_fmt(percentile(during, 50))} | {_fmt(percentile(merges, 50))} / "
                         f"{_fmt(percentile(deletes, 50))} | {count_cell} | `{run['run_id']}` |")
    return "\n".join(lines)


def falkor_copy_table(runs: list[dict]) -> str | None:
    baseline = next(((run.get("controls") or {}).get("falkordb") for run in runs
                     if (run.get("controls") or {}).get("falkordb")), None)
    if not baseline:
        return None
    persistence = baseline.get("persistence_during_curve") or {}
    found = baseline.get("persistence_found") or {}
    lines = []
    if persistence:
        lines += ["Persistence during the curve: " + ", ".join(f"`{k} {v}`" for k, v in sorted(persistence.items())) +
                  "; found beforehand: " + ", ".join(f"`{k} {v}`" for k, v in sorted(found.items())) + ".", ""]
    lines += ["| Nodes / edges | Copy median [IQR] (ms) | S28 reference (ms) | Inside ±50% band | Delete median (ms) | "
              "Source reader stall median (ms) | Unrelated reader stall median (ms) | Unrelated writer stall median (ms) | "
              "RSS delta median (MB) | AOF bytes (last sample) |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for row in baseline.get("rows", []):
        value = row.get("copy_ms", {})
        samples = row.get("samples", [])

        def med(key):
            found_values = [s[key] for s in samples if s.get(key) is not None]
            return percentile(found_values, 50) if found_values else None

        deltas = [s["rss_after_mb"] - s["rss_before_mb"] for s in samples
                  if s.get("rss_after_mb") is not None and s.get("rss_before_mb") is not None]
        aof = [s["aof_bytes"] for s in samples if s.get("aof_bytes") is not None]
        lines.append(f"| {row.get('size')} / {row.get('size')} | {_fmt(value.get('median'))} "
                     f"[{_fmt(value.get('q1'))}–{_fmt(value.get('q3'))}] | {row.get('s28_reference_ms')} | "
                     f"{'yes' if row.get('inside_50_percent_band') else 'NO'} | {_fmt(med('delete_ms'))} | "
                     f"{_fmt(med('source_reader_stall_ms'))} | {_fmt(med('unrelated_reader_stall_ms'))} | "
                     f"{_fmt(med('unrelated_writer_stall_ms'))} | {_fmt(percentile(deltas, 50) if deltas else None)} | "
                     f"{aof[-1] if aof else '–'} |")
    return "\n".join(lines)


def i6_table(runs: list[dict]) -> str | None:
    lines = ["| Build | Storage | Source | I6a: branch prefix / main ledger | I6a gapless and non-empty | I6b isolation | Run |",
             "|---|---|---|---|---|---|---|"]
    for run in runs:
        build, storage = _where(run)
        if run["scenario"]["mode"] == "controls":
            controls = [(t, "controls only") for t in run.get("trials", []) if t.get("valid")]
        else:
            i6 = (run.get("controls") or {}).get("i6")
            controls = [(i6, "end of O1 curve")] if i6 else []
        for control, source in controls:
            prefix = control.get("i6a_prefix_length", len(control.get("branch_prefix_seq", [])))
            main = control.get("i6a_main_length", len(control.get("main_seq", [])))
            gapless = control.get("i6a_gapless_prefix") and prefix > 0
            lines.append(f"| {build} | {storage} | {source} | {prefix} / {main} | {'yes' if gapless else 'NO'}"
                         f"{' (empty prefix, not exercised)' if prefix == 0 else ''} | "
                         f"{'yes' if control.get('i6b_isolation') else 'NO'} | `{run['run_id']}` |")
    return "\n".join(lines) if len(lines) > 2 else None


def copy_weight_table(runs: list[dict]) -> str:
    lines = ["| Build | Storage | Nodes / edges | Create + claim + score + discard (ms) | Run |",
             "|---|---|---|---|---|"]
    for run in runs:
        build, storage = _where(run)
        for row in run.get("copy_weight", []):
            lines.append(f"| {build} | {storage} | {row.get('size')} / {row.get('size')} | "
                         f"{_fmt(row.get('cycle_ms'))} | `{run['run_id']}` |")
    return "\n".join(lines)


def omnigraph_failover_table(runs: list[dict]) -> str:
    lines = ["| Build | Storage | Phase | Variant | Successor ready | A result | B result | Fence | Scanned via | "
             "Integrity scan | Acknowledged writes missing | Classification | Run |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for run in runs:
        build, storage = _where(run)
        for trial in run.get("trials", []):
            a, b = trial.get("a_write") or {}, trial.get("b_write") or {}
            integrity = trial.get("integrity") or {}
            missing = integrity.get("acknowledged_missing")
            missing_cell = "–" if not integrity else ("unknown" if missing is None else (", ".join(missing) or "none"))
            lines.append(f"| {build} | {storage} | {trial.get('phase')} | {trial.get('variant')} | "
                         f"{'yes' if trial.get('successor_ready') else 'no'} | {a.get('kind') or a.get('outcome') or '–'} | "
                         f"{b.get('kind') or b.get('outcome') or '–'} | "
                         f"{'WriterFenced' if trial.get('writer_fenced_observed') else 'not engaged'} | "
                         f"{integrity.get('scanned_via', 'A (stale server)')} | "
                         f"{'ok' if trial.get('graph_open_and_scan') else 'NOT checked'} | {missing_cell} | "
                         f"{trial.get('status')} | `{run['run_id']}` |")
    return "\n".join(lines)


def omnigraph_visibility_table(runs: list[dict]) -> str:
    lines = ["| Build | Storage | Second process | Write acknowledged | Seen | Attempts | Staleness (ms) | Run |",
             "|---|---|---|---|---|---|---|---|"]
    for run in runs:
        build, storage = _where(run)
        for trial in run.get("trials", []):
            lines.append(f"| {build} | {storage} | {trial.get('second_process')} | "
                         f"{'yes' if trial.get('write_acknowledged') else 'no'} | {'yes' if trial.get('seen') else 'NO'} | "
                         f"{trial.get('attempts')} | {_fmt(trial.get('staleness_ms'))} | `{run['run_id']}` |")
    return "\n".join(lines)


def ladder_table(run: dict) -> str:
    build, backend = _where(run)
    lines = [f"**{build} {backend}**, run `{run['run_id']}`", "",
             "| Rung | Documents | Elapsed (s) | Batch p50 / max (s) | Peak memory, helper / workers (MB) | "
             "Graph store (MB) | Nodes | Entities | Stub calls (LLM / embed) | Crash |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for trial in run.get("trials", []):
        seconds, peak = trial.get("batch_seconds", {}), trial.get("resident_mb_peak", {})
        graph, store, stub, crash = trial.get("graph") or {}, trial.get("store") or {}, trial.get("stub_calls") or {}, \
            trial.get("crash")
        lines.append(
            f"| {trial.get('rung')} | {trial.get('documents')} | {_fmt(trial.get('elapsed_s'))} | "
            f"{_fmt(seconds.get('median'))} / {_fmt(seconds.get('max'))} | {_fmt(peak.get('helper'))} / "
            f"{_fmt(peak.get('children'))} | {_fmt(round(store.get('graph_bytes', 0) / 2**20, 1))} | "
            f"{_fmt(graph.get('nodes'))} | {_fmt(graph.get('entities'))} | {stub.get('llm', 0)} / "
            f"{stub.get('embed', 0)} | "
            f"{(crash['kind'] + ' after ' + str(crash['documents_committed'])) if crash else 'no'} |")
    reopen = (run.get("ladder") or {}).get("reopen") or {}
    lines += ["", "Reopened afterwards in a fresh process: " + "; ".join(
        f"{mode}: " + (("opened, " + str(v.get("nodes")) + " nodes") if isinstance(v, dict) and v.get("opened")
                       else (v.get("error", "?")[:160] if isinstance(v, dict) else str(v)))
        for mode, v in reopen.items() if mode != "store")]
    return "\n".join(lines)


def memory_markdown(runs: list[dict], batch: str | None, title: str) -> str:
    if not runs:
        return f"# {title}\n\nNo runs found for batch `{batch}`.\n"
    races = [run for run in runs if run["scenario"]["mode"] in ("asyncio", "queue", "process")]
    suites = [run for run in runs if run["scenario"]["mode"] == "sequential" and
              any(t.get("case") for t in run["trials"])]
    ladders = [run for run in runs if run.get("ladder")]
    visibility = [run for run in runs if run["scenario"]["mode"] == "sequential" and run not in suites
                  and run not in ladders]
    omnigraph_curves = [run for run in runs if run["scenario"]["mode"] == "curve"]
    omnigraph_failovers = [run for run in runs if run["scenario"]["mode"] == "matrix"]
    omnigraph_visibility = [run for run in runs if run["scenario"]["mode"] == "visibility"]
    omnigraph_controls = [run for run in runs if run["scenario"]["mode"] == "controls"]
    first = runs[0]
    host, harness = first.get("host", {}), first.get("harness", {})
    run_summary = f"- Runs: {len(runs)} ({len(races)} races, {len(suites)} case suites, {len(visibility)} visibility)"
    if omnigraph_curves or omnigraph_failovers or omnigraph_visibility or omnigraph_controls:
        run_summary = (f"- Runs: {len(runs)} ({len(races)} races, {len(suites)} case suites, "
                       f"{len(visibility) + len(omnigraph_visibility)} visibility, {len(omnigraph_curves)} cost curves, "
                       f"{len(omnigraph_failovers)} failover matrices, {len(omnigraph_controls)} I6 control runs)")
    lines = [
        f"# {title}: batch `{batch}`",
        "",
        "Regenerated from `evidence/` by `python wm.py report --memory`. Do not edit by hand.",
        "",
        f"- Harness commit: `{harness.get('commit')}` (dirty: {str(harness.get('dirty')).lower()})",
        f"- Host: {host.get('os')}; {host.get('cpu')}; {host.get('cores')} logical cores; {host.get('memory_gb')} GB",
        f"- Docker: {host.get('docker', 'unknown')}; VM limits {host.get('vm_cpus', '?')} CPUs, "
        f"{host.get('vm_memory_gb', '?')} GB",
        run_summary,
        "",
    ]
    boundaries = support_boundaries_table(runs)
    if boundaries:
        lines += ["## Support boundaries reached", "",
                  "[measured] These runs declared a support boundary, recorded ERR classes, and had no valid trials.",
                  "", boundaries, ""]
    if races:
        sequential = sum(1 for run in races if (_control(run, "sequential") or {}).get("met"))
        lines += ["## Races", "", race_table(races), "",
                  f"Sequential controls met: {sequential} of {len(races)} race runs.", ""]
        lines += ["### Release spread by mode (valid race trials)", "", "| Mode | Trials | p50 | p95 | p99 | max |",
                  "|---|---|---|---|---|---|"]
        for mode in ("asyncio", "queue", "process"):
            values = spreads([run for run in races if run["scenario"]["mode"] == mode])
            if values:
                lines.append(f"| {mode} | {len(values)} | {_fmt(percentile(values, 50))} | "
                             f"{_fmt(percentile(values, 95))} | {_fmt(percentile(values, 99))} | {_fmt(max(values))} |")
        lines.append("")
    if suites:
        lines += ["## Known-answer suites", "", "A cell lists the checks that failed for that case; `ok` means none did.",
                  "", cases_table(suites), ""]
    if visibility:
        lines += ["## Read your writes", "", visibility_table(visibility), ""]
    if omnigraph_curves or omnigraph_controls:
        i6 = i6_table(omnigraph_curves + omnigraph_controls)
        if i6:
            lines += ["## I6a and I6b controls", "", i6, ""]
    if omnigraph_curves:
        lines += ["## O1 branch-creation cost", "", omnigraph_cost_table(omnigraph_curves), ""]
        lines += ["### Copy weight", "", copy_weight_table(omnigraph_curves), ""]
        copy_table = falkor_copy_table(omnigraph_curves)
        if copy_table:
            lines += ["### FalkorDB `GRAPH.COPY` sanity curve", "", copy_table, ""]
    if omnigraph_failovers:
        lines += ["## O4 failover acceptance matrix", "", omnigraph_failover_table(omnigraph_failovers), "",
                  "BOUNDARY: a failover took place on the stable release, which predates the epoch fence; its documented deployment rule is its only protection. "
                  "NOT_EXERCISED: the harness did not perform a documented step (the epoch claim, an embedding-program call, or the local ownership transfer), "
                  "so the cell says nothing about the fence. No cell is a fence pass, and none is a fence failure.", ""]
    if omnigraph_visibility:
        lines += ["## O5 cross-process read your writes", "", omnigraph_visibility_table(omnigraph_visibility), ""]
    if ladders:
        lines += ["## Scale ladder", ""]
        for run in ladders:
            lines += [ladder_table(run), ""]
    if any(run["target"].get("name") == "cognee" for run in runs):
        lines += ["## Invariants by backend", "",
                  "Each cell: valid trials with a violation / valid trials that carry the check. "
                  "Trials a gate made invalid are counted in the next table, not here.", "",
                  invariants_table([run for run in runs if run in races or run in suites or run in ladders]), ""]
    extra = extra_checks_table(runs)
    if extra:
        lines += ["## Checks outside the invariants", "", extra, ""]
    invalid = invalid_table(runs)
    if invalid and any(run["target"].get("name") == "cognee" for run in runs):
        lines += ["## Invalid trials", "", invalid, ""]
    return "\n".join(lines)


def proposed_gate_ms(values: list[float]) -> float | None:
    """δ for thread mode: 1.5 × the 99th-percentile spread, rounded up to a whole millisecond."""
    p99 = percentile(values, 99)
    return None if p99 is None else float(max(1, math.ceil(1.5 * p99)))


def calibration_markdown(runs: list[dict], batch: str | None) -> str:
    if not runs:
        return f"# Calibration\n\nNo runs found for batch `{batch}`.\n"
    first = runs[0]
    host, harness = first.get("host", {}), first.get("harness", {})
    components = {run["components"][0]["name"]: run["components"][0] for run in runs}
    values = spreads(runs)
    sequential_met = sum(1 for run in runs if (_control(run, "sequential") or {}).get("met"))
    negatives = [run for run in runs if run.get("expectation", {}).get("role") == "negative"]
    positives = [run for run in runs if run.get("expectation", {}).get("role") == "positive"]
    negatives_met = sum(1 for run in negatives if (_role_control(run) or {}).get("met"))
    positives_met = sum(1 for run in positives if (_role_control(run) or {}).get("met"))
    invalid = sum(1 for run in runs if run["verdicts"][0]["status"] == "INVALID")
    gate = proposed_gate_ms(values)

    lines = [
        f"# M1 calibration: batch `{batch}`",
        "",
        "Regenerated from `evidence/` by `python wm.py report`. Do not edit by hand.",
        "",
        f"- Harness commit: `{harness.get('commit')}` (dirty: {str(harness.get('dirty')).lower()})",
        f"- Host: {host.get('os')}; {host.get('cpu')}; {host.get('cores')} logical cores; {host.get('memory_gb')} GB; "
        f"Python {host.get('python')}",
        f"- Docker: {host.get('docker', 'unknown')}; VM limits {host.get('vm_cpus', '?')} CPUs, "
        f"{host.get('vm_memory_gb', '?')} GB",
    ]
    for name, component in sorted(components.items()):
        lines.append(f"- {name}: {component.get('version')}; image `{component.get('image', 'unknown')}`; "
                     f"digest `{component.get('digest', 'unknown')}`")
    lines += [
        f"- Mode: thread; {first['scenario']['clients']} clients; {first['scenario']['trials']} trials per run",
        "",
        "## Runs",
        "",
        runs_table(runs),
        "",
        "## Release spread (thread mode, every valid race trial)",
        "",
        f"- Trials: {len(values)}",
        f"- p50 {_fmt(percentile(values, 50))} ms; p95 {_fmt(percentile(values, 95))} ms; "
        f"p99 {_fmt(percentile(values, 99))} ms; max {_fmt(max(values) if values else None)} ms",
        f"- Proposed gate δ for thread mode (1.5 × p99, rounded up): {_fmt(gate)} ms",
        "",
        "## M1 exit check (master blueprint section 12)",
        "",
        f"- Sequential controls met: {sequential_met} of {len(runs)} runs",
        f"- Negative controls met: {negatives_met} of {len(negatives)} runs",
        f"- Positive controls fired: {positives_met} of {len(positives)} runs",
        f"- INVALID verdicts: {invalid}",
        f"- Exit criterion {'MET' if sequential_met == len(runs) and negatives_met == len(negatives) and positives and positives_met == len(positives) and not invalid else 'NOT MET'}",
        "",
    ]
    return "\n".join(lines)
