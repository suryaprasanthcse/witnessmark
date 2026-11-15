#!/usr/bin/env python3
"""Witnessmark target 03: Omnigraph network runner and Part 1 controls."""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path[:0] = [str(REPO / "core"), str(HERE)]

import argparse  # noqa: E402
import json  # noqa: E402

from witnessmark.runner import RunConfig, run, run_sequential_control  # noqa: E402
from witnessmark.scenarios import Expectation  # noqa: E402

from witnessmark_omnigraph.controls import run_o3_sequential, run_o6_sequential, run_query_smoke  # noqa: E402
from witnessmark_omnigraph.capture import repro_command  # noqa: E402
from witnessmark_omnigraph.engine import OmnigraphEngine  # noqa: E402
from witnessmark_omnigraph.part2 import run_i6, run_o1, run_o4, run_o5  # noqa: E402
from witnessmark_omnigraph.runner_scenarios import ClaimScenario  # noqa: E402

BUILDS = {
    "v0.15.0": {
        "image": "witnessmark/omnigraph:v0.15.0",
        "digest": "sha256:97d4950250b20019a80b03c8fd52cf52aa6243a86058a54895ba2772f15a2159",
    },
    "edge-b2dbaff": {
        "image": "witnessmark/omnigraph:edge-b2dbaff",
        "digest": "sha256:b7b8edac24ff8915346cee19eb85ac89c7aeaea6a8069d68410dcbc90e266792",
    },
}


def _engine(args) -> OmnigraphEngine:
    build = BUILDS[args.build]
    return OmnigraphEngine(args.endpoint, args.build, build["image"], build["digest"], storage=args.storage)


def _write(path: str | None, value: dict) -> None:
    text = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    if path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8", newline="\n")
    print(text, end="")


def _control_result(result: dict) -> dict:
    return {
        "met": result["met"],
        "expected": result["expected"],
        "observed": result["observed"],
        "operations": [op.to_json() for op in result["operations"]],
        "state": result["state"],
        "checks": [check.to_json() for check in result["checks"]],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wm_omnigraph", description="Witnessmark target 03: Omnigraph")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("smoke", "run every checked-in GQ declaration"),
                            ("cases", "run Part 1 sequential controls"),
                            ("race", "run O2 through the core thread runner")):
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument("--build", choices=sorted(BUILDS), required=True)
        sub.add_argument("--endpoint", default="http://127.0.0.1:18080")
        sub.add_argument("--storage", choices=["local", "minio", "proxy"], default="local")
        if name != "race":
            sub.add_argument("--write", default=None)
            sub.add_argument("--run-id", default=None)
        if name == "cases":
            sub.add_argument("--scenario", choices=["all", "o2a", "o2c", "o3", "o6"], default="all")
            sub.add_argument("--clients", type=int, default=50)
            sub.add_argument("--falkordb-port", type=int, default=16380)
            sub.add_argument("--neo4j-port", type=int, default=17474)
        if name == "race":
            sub.add_argument("--scenario", choices=["o2a", "o2c"], required=True)
            sub.add_argument("--clients", type=int, default=50)
            sub.add_argument("--trials", type=int, default=20)
            sub.add_argument("--seed", type=int, default=0)
            sub.add_argument("--batch", default=None)
            sub.add_argument("--evidence", default=str(REPO / "evidence"))
    for name, help_text, storages in (
        ("curve", "run the declared O1 cost curve", ["local", "minio", "proxy"]),
        ("failover", "run the O4 phase/variant matrix", ["local", "minio"]),
        ("visibility", "run O5 across two server processes", ["local", "minio"]),
        ("i6", "run the I6a and I6b controls alone", ["local", "minio", "proxy"]),
    ):
        sub = commands.add_parser(name, help=help_text)
        sub.add_argument("--build", choices=sorted(BUILDS), required=True)
        sub.add_argument("--storage", choices=storages, default="local")
        sub.add_argument("--batch", required=True)
        sub.add_argument("--evidence", default=str(REPO / "evidence"))
        if name == "curve":
            sub.add_argument("--include-falkor", action="store_true")
            sub.add_argument("--smoke", action="store_true", help="one tiny curve cell without a baseline benchmark")
        if name == "failover":
            sub.add_argument("--seed", type=int, default=20261115)
            sub.add_argument("--smoke", action="store_true", help="one pause/resume cell")
    args = parser.parse_args(argv)
    command = repro_command(REPO, argv if argv is not None else sys.argv[1:])

    if args.command in ("curve", "failover", "visibility", "i6"):
        build = BUILDS[args.build]
        evidence = Path(args.evidence)
        if args.command == "curve":
            if args.smoke and args.include_falkor:
                parser.error("the smoke curve cannot run the FalkorDB benchmark")
            manifest, path = run_o1(REPO, evidence, args.batch, args.build, build, args.storage,
                                    include_falkor=args.include_falkor, command=command, smoke=args.smoke)
            baseline = (manifest.get("controls", {}).get("falkordb") or {})
            if baseline and not baseline.get("sanity_band_met"):
                print("FalkorDB S28 sanity band NOT MET; stop the batch before other findings")
                print(f"evidence: {path}")
                return 2
        elif args.command == "i6":
            manifest, path = run_i6(REPO, evidence, args.batch, args.build, build, args.storage, command=command)
        elif args.command == "failover":
            manifest, path = run_o4(REPO, evidence, args.batch, args.build, build, args.storage, args.seed,
                                    command=command, smoke=args.smoke)
        else:
            manifest, path = run_o5(REPO, evidence, args.batch, args.build, build, args.storage, command=command)
        print(f"{manifest['scenario']['id']}: {len(manifest['trials'])} trial(s)")
        print(f"evidence: {path}")
        return 0

    engine = _engine(args)

    if args.command == "smoke":
        run_id = args.run_id or f"part1-{args.build}-{args.storage}-smoke"
        result = {"run_id": run_id, "build": args.build, "storage": args.storage,
                  "smoke": run_query_smoke(engine)}
        _write(args.write, result)
        return 0 if result["smoke"]["met"] else 1

    if args.command == "cases":
        run_id = args.run_id or f"part1-{args.build}-{args.storage}-controls"
        selected = [args.scenario] if args.scenario != "all" else ["o2a", "o2c", "o3", "o6"]
        results = {}
        if "o2a" in selected:
            results["o2a"] = _control_result(run_sequential_control(
                engine, ClaimScenario(True), "thread", args.clients, run_id=f"{run_id}-o2a"))
        if "o2c" in selected:
            results["o2c"] = _control_result(run_sequential_control(
                engine, ClaimScenario(False), "thread", args.clients, run_id=f"{run_id}-o2c"))
        if "o3" in selected:
            results["o3"] = run_o3_sequential(engine, args.clients)
        if "o6" in selected:
            results["o6"] = run_o6_sequential(engine, falkordb_port=args.falkordb_port,
                                                neo4j_port=args.neo4j_port)
        output = {"run_id": run_id, "build": args.build, "storage": args.storage, "controls": results,
                  "met": all(result["met"] for result in results.values())}
        _write(args.write, output)
        return 0 if output["met"] else 1

    scenario = ClaimScenario(args.scenario == "o2a")
    expectation = Expectation("negative", "documented", scenario.basis_ref)
    config = RunConfig(engine=engine, scenario=scenario, shape="thread", clients=args.clients,
                       trials=args.trials, seed=args.seed, evidence_root=Path(args.evidence), repo_root=REPO,
                       evidence_dir=f"omnigraph/{args.build}.{args.storage}", batch=args.batch,
                       command=command, expectation=expectation)
    manifest = run(config)
    print(f"{manifest['scenario']['id']}: {manifest['verdicts'][0]['status']}")
    print(f"evidence: {manifest['path']}")
    return 0 if manifest["verdicts"][0]["status"] != "INVALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())
