"""Command line: python wm.py <command> (master blueprint section 12, milestone M1)."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
import unittest
from pathlib import Path

from . import __version__, env
from .adapters import make_engine
from .report import calibration_markdown, in_batch, latest_batch, load_runs, runs_table
from .runner import RunConfig, run
from .scenarios import CALIBRATION, SCENARIOS, resolve
from .timing import utc_now

REPO_ROOT = Path(__file__).resolve().parents[2]


def _engine(name: str, args) -> object:
    if name == "falkordb":
        return make_engine("falkordb", host=args.falkordb_host, port=args.falkordb_port)
    return make_engine("neo4j", host=args.neo4j_host, port=args.neo4j_port,
                       user=os.environ.get("WM_NEO4J_USER"), password=os.environ.get("WM_NEO4J_PASSWORD"))


def _connection_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--falkordb-host", default="127.0.0.1")
    parser.add_argument("--falkordb-port", type=int, default=16380)
    parser.add_argument("--neo4j-host", default="127.0.0.1")
    parser.add_argument("--neo4j-port", type=int, default=17474)


def _summary_line(manifest: dict) -> str:
    verdict = manifest["verdicts"][0]
    role = next(c for c in manifest["controls"] if c["kind"] in ("negative", "positive"))
    sequential = next(c for c in manifest["controls"] if c["kind"] == "sequential")
    return (f"{manifest['target']['name']:8} {manifest['scenario']['id']:24} {role['kind']:8} "
            f"sequential {'met' if sequential['met'] else 'NOT met':7} {role['kind']} {'met' if role['met'] else 'NOT met':7} "
            f"{verdict['trials_violating']:2} of {verdict['trials_valid']:2} violating  {verdict['status']:15} {manifest['run_id']}")


def cmd_env(args) -> int:
    print(json.dumps({"harness": env.harness_info(REPO_ROOT), "host": env.host_info()}, indent=2))
    for name in ("falkordb", "neo4j"):
        print(f"{name}: {_engine(name, args).health()}")
    return 0


def cmd_run(args) -> int:
    scenario = resolve(args.scenario, args.shape)
    engine = _engine(args.engine, args)
    config = RunConfig(engine=engine, scenario=scenario, shape=args.shape, clients=args.clients, trials=args.trials,
                       seed=args.seed, timeout_s=args.timeout, spread_gate_ms=args.spread_gate_ms,
                       evidence_root=Path(args.evidence), repo_root=REPO_ROOT, batch=args.batch,
                       command=shlex.join(["python", "wm.py", *sys.argv[1:]]))
    manifest = run(config)
    print(_summary_line(manifest))
    print(f"evidence: {manifest['path']}")
    return 0 if manifest["verdicts"][0]["status"] != "INVALID" else 1


def cmd_calibrate(args) -> int:
    batch = f"m1-{utc_now():%Y%m%dT%H%M%SZ}"
    selected = [(engine, sid) for engine, sid in CALIBRATION if not args.only or engine in args.only.split(",")]
    for engine_name in sorted({engine for engine, _ in selected}):
        health = _engine(engine_name, args).health()
        if not health.get("ok"):
            print(f"{engine_name} is not reachable: {health}. Start the baselines: "
                  "docker compose -f baselines/docker-compose.yml up -d", file=sys.stderr)
            return 2
    print(f"batch {batch}: {len(selected)} runs, {args.clients} clients x {args.trials} trials each")
    for index, (engine_name, scenario_id) in enumerate(selected):
        base, shape = scenario_id.rsplit(".", 1)
        scenario = resolve(base, shape)
        seed = args.seed + index
        command = shlex.join(["python", "wm.py", "run", "--engine", engine_name, "--scenario", base, "--shape", shape,
                              "--clients", str(args.clients), "--trials", str(args.trials), "--seed", str(seed)])
        config = RunConfig(engine=_engine(engine_name, args), scenario=scenario, shape=shape, clients=args.clients,
                           trials=args.trials, seed=seed, timeout_s=args.timeout, spread_gate_ms=None,
                           evidence_root=Path(args.evidence), repo_root=REPO_ROOT, batch=batch, command=command)
        print(_summary_line(run(config)), flush=True)
    runs = in_batch(load_runs(Path(args.evidence)), batch)
    text = calibration_markdown(runs, batch)
    if args.write:
        Path(args.write).write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {args.write}")
    print()
    print(text)
    return 0


def cmd_report(args) -> int:
    runs = load_runs(Path(args.evidence))
    batch = args.batch or latest_batch(runs)
    selected = in_batch(runs, batch)
    text = calibration_markdown(selected, batch) if args.calibration else runs_table(selected) + "\n"
    if args.write:
        Path(args.write).write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {args.write}")
    else:
        print(text)
    return 0


def cmd_selftest(args) -> int:
    suite = unittest.defaultTestLoader.discover(str(REPO_ROOT / "core" / "tests"), top_level_dir=str(REPO_ROOT / "core"))
    result = unittest.TextTestRunner(verbosity=2 if args.verbose else 1).run(suite)
    return 0 if result.wasSuccessful() else 1


def main(argv: list[str] | None = None) -> int:
    # Reports use characters such as δ and ×; a Windows console defaults to a code page without them.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass
    parser = argparse.ArgumentParser(prog="wm", description=f"Witnessmark {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    p_env = commands.add_parser("env", help="print the environment and baseline health")
    _connection_options(p_env)
    p_env.set_defaults(func=cmd_env)

    p_run = commands.add_parser("run", help="run one scenario on one engine")
    _connection_options(p_run)
    p_run.add_argument("--engine", choices=["falkordb", "neo4j"], required=True)
    p_run.add_argument("--scenario", choices=sorted(SCENARIOS), required=True)
    p_run.add_argument("--shape", required=True)
    p_run.add_argument("--clients", type=int, default=50)
    p_run.add_argument("--trials", type=int, default=20)
    p_run.add_argument("--seed", type=int, default=0)
    p_run.add_argument("--timeout", type=float, default=60.0, help="per-operation timeout, seconds")
    p_run.add_argument("--spread-gate-ms", type=float, default=None,
                       help="mark trials whose release spread exceeds this many ms as invalid")
    p_run.add_argument("--evidence", default=str(REPO_ROOT / "evidence"))
    p_run.add_argument("--batch", default=None)
    p_run.set_defaults(func=cmd_run)

    p_cal = commands.add_parser("calibrate", help="run the M1 control matrix on both baselines")
    _connection_options(p_cal)
    p_cal.add_argument("--clients", type=int, default=50)
    p_cal.add_argument("--trials", type=int, default=20)
    p_cal.add_argument("--seed", type=int, default=20261113)
    p_cal.add_argument("--timeout", type=float, default=60.0)
    p_cal.add_argument("--only", default=None, help="comma-separated engines, e.g. neo4j")
    p_cal.add_argument("--evidence", default=str(REPO_ROOT / "evidence"))
    p_cal.add_argument("--write", default=None, help="also write the calibration report to this file")
    p_cal.set_defaults(func=cmd_calibrate)

    p_rep = commands.add_parser("report", help="rebuild tables from evidence/")
    p_rep.add_argument("--evidence", default=str(REPO_ROOT / "evidence"))
    p_rep.add_argument("--batch", default=None, help="defaults to the latest batch")
    p_rep.add_argument("--calibration", action="store_true", help="the full calibration report")
    p_rep.add_argument("--write", default=None)
    p_rep.set_defaults(func=cmd_report)

    p_test = commands.add_parser("selftest", help="run the unit tests (no engines needed)")
    p_test.add_argument("-v", "--verbose", action="store_true")
    p_test.set_defaults(func=cmd_selftest)

    args = parser.parse_args(argv)
    return args.func(args)
