"""The reporter: every table is rebuilt from evidence/ alone (master blueprint sections 9.6 and 10)."""

from __future__ import annotations

import json
import math
from pathlib import Path

from .verdicts import percentile


def load_runs(evidence_root: Path) -> list[dict]:
    runs = []
    for path in sorted(Path(evidence_root).glob("*/*/*/run.json")):
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
