#!/usr/bin/env python3
"""Witnessmark, target 02: Cognee. Run with the pinned Cognee environment's Python:

    .state/venvs/cognee-v1.6.8/Scripts/python targets/02-cognee/wm_cognee.py race \\
        --row R1 --scenario c1.k4 --mode process

The core (core/witnessmark) stays standard-library only. This entry point starts
the shared stub endpoint on 127.0.0.1 and drives Cognee through helper and
worker processes; the coordinator itself never imports cognee.
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path[:0] = [str(REPO / "core"), str(HERE)]

import argparse  # noqa: E402
import asyncio  # noqa: E402
import os  # noqa: E402
import shlex  # noqa: E402

from witnessmark.memory import MODES, MemoryRunConfig, TargetSpec, run_cases, run_race, run_visibility  # noqa: E402
from witnessmark.timing import utc_now  # noqa: E402

RACES = ("c1.k2", "c1.k4", "c1.k8", "c1.disjoint.k4", "c2.writers", "c2.improve", "c3.cross_process")
SUITES = ("c0.single_call", "c3.in_process", "c6.deletion")
ROWS = ("R1", "R1i", "R2", "R3")


def _summary(manifest: dict) -> str:
    controls = "; ".join(f"{c['kind']} {'met' if c['met'] else 'NOT met'}" for c in manifest["controls"]) or "no controls"
    verdicts = "; ".join(f"{v['invariant']} {v['status']} ({v['trials_violating']} of {v['trials_valid']})"
                         for v in manifest["verdicts"])
    return f"{manifest['scenario']['id']}: {controls} | {verdicts}\nevidence: {manifest['path']}"


def _scenario(name: str):
    from witnessmark_cognee import scenarios

    if name.startswith("c1.disjoint.k"):
        return scenarios.C1Disjoint(int(name.rsplit("k", 1)[1]))
    if name.startswith("c1.k"):
        return scenarios.C1OneDataset(int(name[4:]))
    return {"c2.writers": scenarios.C2Writers, "c2.improve": scenarios.C2Improve,
            "c3.cross_process": scenarios.C3CrossProcess}[name]()


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass
    parser = argparse.ArgumentParser(prog="wm_cognee", description="Witnessmark target 02: Cognee")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("race", "C1-C3: concurrent workers"), ("cases", "C3 in one process, C6"),
                            ("visibility", "C5: read your writes"), ("ladder", "C4: the scale ladder")):
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument("--row", choices=ROWS, required=True)
        sub.add_argument("--build", default="v1.6.8", help="the Cognee build label recorded with the run")
        sub.add_argument("--commit", default="", help="the Cognee commit, when it is not a known tag")
        sub.add_argument("--access-control", choices=["default", "off"], default="default",
                         help="default: Cognee's own (on for Ladybug + LanceDB); off: ENABLE_BACKEND_ACCESS_CONTROL=false")
        sub.add_argument("--evidence", default=str(REPO / "evidence"))
        sub.add_argument("--runs", default=str(REPO / ".state" / "runs"), help="where the stores of each run live")
        sub.add_argument("--batch", default=None)
        sub.add_argument("--seed", type=int, default=0)
        sub.add_argument("--dim", type=int, default=256)
        if name == "race":
            sub.add_argument("--scenario", choices=RACES, required=True)
            sub.add_argument("--mode", choices=MODES, default="process")
            sub.add_argument("--trials", type=int, default=20)
        elif name == "cases":
            sub.add_argument("--suite", choices=SUITES, required=True)
        elif name == "ladder":
            sub.add_argument("--sizes", default="448,1000,1650,2500,5401")
            sub.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args(argv)

    from witnessmark_cognee import stub

    if args.command == "race" and args.scenario.startswith("c2.") and args.access_control != "off":
        parser.error(f"{args.scenario} needs --access-control off: only then do datasets share one store (#5254's shape)")
    if args.row in ("R2", "R3") and args.access_control != "off":
        parser.error(f"{args.row} needs --access-control off: Cognee's per-dataset handler for it needs a "
                     "multi-database server (CREATE DATABASE) or is not registered")
    label = {"race": getattr(args, "scenario", ""), "cases": getattr(args, "suite", ""), "visibility": "c5",
             "ladder": "c4"}[args.command]
    started = utc_now().strftime("%Y%m%dT%H%M%S%fZ")
    root = Path(args.runs) / f"{started}-{args.row}-{label}"
    server = stub.start(args.dim)
    try:
        spec = TargetSpec("witnessmark_cognee.target", "make_target", {
            "row": args.row, "root": str(root), "stub_url": server.url, "dim": args.dim,
            "access_control": args.access_control, "build_ref": args.build, "commit": args.commit})
        python = os.path.relpath(sys.executable, REPO) if sys.executable.startswith(str(REPO)) else "python"
        command = shlex.join([python.replace("\\", "/"), "targets/02-cognee/wm_cognee.py",
                              *(argv if argv is not None else sys.argv[1:])])
        suffix = "-acoff" if args.access_control == "off" else ""
        scenario = _scenario(args.scenario) if args.command == "race" else None
        processes = (getattr(scenario, "workers", None) or len(scenario.clients())) if scenario is not None else 1
        config = MemoryRunConfig(spec=spec, trials=getattr(args, "trials", 1), processes=processes,
                                 mode=getattr(args, "mode", "process"), seed=args.seed,
                                 evidence_root=Path(args.evidence), repo_root=REPO,
                                 evidence_dir=f"cognee/{args.build}.{args.row}{suffix}", batch=args.batch,
                                 command=command, op_timeout_s=900.0, trial_timeout_s=1800.0, poll_budget_s=30.0)
        from witnessmark_cognee import scenarios

        if args.command == "race":
            manifest = asyncio.run(run_race(config, scenario))
        elif args.command == "cases":
            suite = {"c0.single_call": scenarios.C0SingleCall, "c3.in_process": scenarios.C3InProcess,
                     "c6.deletion": scenarios.C6Deletion}[args.suite]()
            manifest = asyncio.run(run_cases(config, suite))
        elif args.command == "visibility":
            manifest = asyncio.run(run_visibility(config, scenarios.C5Visibility()))
        else:
            from witnessmark_cognee import ladder

            manifest = asyncio.run(ladder.run_ladder(config, [int(s) for s in args.sizes.split(",")],
                                                     args.batch_size))
        print(_summary(manifest))
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
