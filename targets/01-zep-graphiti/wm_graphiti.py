#!/usr/bin/env python3
"""Witnessmark, target 01: Graphiti. Run with the pinned Graphiti environment's Python:

    .state/venvs/graphiti-v0.31.2/Scripts/python targets/01-zep-graphiti/wm_graphiti.py race \\
        --backend falkordb --scenario g1.same_group --mode asyncio

The core (core/witnessmark) stays standard-library only; this entry point adds
the Graphiti adapter, which imports graphiti_core.
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

RACES = ("g1.same_group", "g1.cross_group", "g2.contradictions")
FIXTURE_OF = {"g1.same_group": "g1", "g1.cross_group": "g1", "g2.contradictions": "g2", "g3": "g3", "g4": "g4",
              "g5": "g5"}
ENTRIES = ("add_episode", "add_episode_bulk", "add_triplet")


def _summary(manifest: dict) -> str:
    controls = "; ".join(f"{c['kind']} {'met' if c['met'] else 'NOT met'}" for c in manifest["controls"]) or "no controls"
    verdicts = "; ".join(f"{v['invariant']} {v['status']} ({v['trials_violating']} of {v['trials_valid']})"
                         for v in manifest["verdicts"])
    return f"{manifest['scenario']['id']}: {controls} | {verdicts}\nevidence: {manifest['path']}"


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass
    parser = argparse.ArgumentParser(prog="wm_graphiti", description="Witnessmark target 01: Graphiti")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("race", "G1/G2: concurrent ingest"), ("cases", "G3/G5: known-answer cases"),
                            ("visibility", "G4: read your writes")):
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument("--backend", choices=["falkordb", "neo4j"], required=True)
        sub.add_argument("--build", default="v0.31.2", help="the Graphiti build label recorded with the run")
        sub.add_argument("--commit", default="", help="the Graphiti commit, for builds installed from git")
        sub.add_argument("--evidence", default=str(REPO / "evidence"))
        sub.add_argument("--batch", default=None)
        sub.add_argument("--anchor", default=None, help="ISO time that relative fixture dates hang from")
        sub.add_argument("--falkordb-port", type=int, default=16380)
        sub.add_argument("--neo4j-bolt-port", type=int, default=17687)
        sub.add_argument("--seed", type=int, default=0)
        sub.add_argument("--falkordb-pool", choices=["blocking", "default"], default="blocking",
                         help="blocking: 100 connections, callers wait; default: Graphiti's own client, which fails "
                              "with 'Too many connections' when all 100 are busy")
        if name == "race":
            sub.add_argument("--scenario", choices=RACES, required=True)
            sub.add_argument("--mode", choices=MODES, default="asyncio")
            sub.add_argument("--trials", type=int, default=20)
            sub.add_argument("--processes", type=int, default=4)
        elif name == "cases":
            sub.add_argument("--suite", choices=["g3", "g5"], required=True)
            sub.add_argument("--entry", choices=ENTRIES, default="add_episode")
    args = parser.parse_args(argv)

    anchor = args.anchor or utc_now().replace(microsecond=0).isoformat().replace("+00:00", "Z")
    key = args.scenario if args.command == "race" else args.suite if args.command == "cases" else "g4"
    spec = TargetSpec("witnessmark_graphiti.target", "make_target", {
        "backend": args.backend, "fixture": FIXTURE_OF[key], "anchor": anchor, "build_ref": args.build,
        "commit": args.commit, "falkordb_port": args.falkordb_port, "neo4j_bolt_port": args.neo4j_bolt_port,
        "falkordb_pool": args.falkordb_pool})
    python = os.path.relpath(sys.executable, REPO) if sys.executable.startswith(str(REPO)) else "python"
    command = shlex.join([python.replace("\\", "/"), "targets/01-zep-graphiti/wm_graphiti.py",
                          *(argv if argv is not None else sys.argv[1:]), "--anchor", anchor])
    pool = f".{args.falkordb_pool}-pool" if args.backend == "falkordb" and args.falkordb_pool != "blocking" else ""
    config = MemoryRunConfig(spec=spec, trials=getattr(args, "trials", 1), processes=getattr(args, "processes", 4),
                             mode=getattr(args, "mode", "asyncio"), seed=args.seed, evidence_root=Path(args.evidence),
                             repo_root=REPO, evidence_dir=f"graphiti/{args.build}.{args.backend}{pool}",
                             batch=args.batch, command=command)

    from witnessmark_graphiti import scenarios

    if args.command == "race":
        scenario = {"g1.same_group": scenarios.G1SameGroup, "g1.cross_group": scenarios.G1CrossGroup,
                    "g2.contradictions": scenarios.G2Contradictions}[args.scenario](anchor)
        manifest = asyncio.run(run_race(config, scenario))
    elif args.command == "cases":
        suite = scenarios.G3Temporal(anchor, args.entry) if args.suite == "g3" else scenarios.G5SharedSearchLimit(anchor)
        manifest = asyncio.run(run_cases(config, suite))
    else:
        manifest = asyncio.run(run_visibility(config, scenarios.G4Visibility(anchor)))
    print(_summary(manifest))
    return 0


if __name__ == "__main__":
    sys.exit(main())
