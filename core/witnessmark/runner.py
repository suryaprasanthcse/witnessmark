"""The barrier-synchronised runner, thread mode (master blueprint section 6).

A run is one sequential control (trial k = 0) followed by T race trials. Each
race trial goes: reset, warm, arm, release, act, quiesce, observe, check.
Operations are kept in memory during the race and written afterwards, so no
file I/O falls inside the race window.
"""

from __future__ import annotations

import random
import shlex
import threading
import time
import traceback
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path

from . import SCHEMA_VERSION, env
from .adapters.base import Engine, EngineError, EngineUnavailable, Session
from .evidence import RunDir, crash_note, digest, make_run_id
from .history import FAIL, OK, UNKNOWN, Op
from .scenarios import EXPECTATIONS, Expectation, Scenario, client_name
from .timing import iso, stamp, utc_now
from .verdicts import role_control, verdict

UNKNOWN_LIMIT = 0.05  # at most 5% of a trial's operations may have an unknown outcome (section 6.3)
# δ for thread mode: 1.5 × the p99 release spread of the M1 calibration (section 6.3,
# evidence/M1_CALIBRATION.md). `calibrate` records the spread without gating on it.
THREAD_SPREAD_GATE_MS = 40.0
# δ for Omnigraph's thread-mode races (O2, O3): 1.5 × the p99 release spread over the 80 valid O2a and O2c
# trials of batch m5-20261115T222957Z, both builds (p50 8.671 ms, p99 36.365 ms, max 36.365 ms), rounded up.
OMNIGRAPH_THREAD_SPREAD_GATE_MS = 55.0


@dataclass
class RunConfig:
    engine: Engine
    scenario: Scenario
    shape: str
    clients: int = 50
    trials: int = 20
    seed: int = 0
    timeout_s: float = 60.0
    trial_timeout_s: float = 600.0
    spread_gate_ms: float | None = THREAD_SPREAD_GATE_MS  # None records the spread without gating on it
    evidence_root: Path = Path("evidence")
    evidence_dir: str | None = None
    additional_components: tuple[dict, ...] = ()
    repo_root: Path = Path(".")
    batch: str | None = None
    command: str = ""
    expectation: Expectation | None = None  # overrides the registry (used by tests)
    capture_environment: bool = True

    @property
    def scenario_id(self) -> str:
        return f"{self.scenario.id}.{self.shape}"


def _execute(session: Session, scenario: Scenario, query: str, params: dict, recorded: dict,
             run_id: str, k: int, phase: str, client: str) -> Op:
    op_id = f"{k}-{client}-0"
    inv = stamp()
    try:
        reply = session.run(query, params)
    except EngineError as exc:
        return Op(run_id, k, phase, op_id, client, scenario.kind, recorded, inv, stamp(), FAIL, None, exc.to_json())
    except EngineUnavailable as exc:
        return Op(run_id, k, phase, op_id, client, scenario.kind, recorded, inv, None, UNKNOWN, None, exc.to_json())
    ret = stamp()
    try:
        outcome, result = scenario.classify(reply)
    except (TypeError, ValueError, IndexError) as exc:
        error = {"type": "harness.classify", "message": f"{type(exc).__name__}: {exc}; rows {reply.rows!r}"[:500]}
        return Op(run_id, k, phase, op_id, client, scenario.kind, recorded, inv, None, UNKNOWN, None, error)
    return Op(run_id, k, phase, op_id, client, scenario.kind, recorded, inv, ret, outcome, result, None, reply.token)


def _race_trial(config: RunConfig, k: int, admin: Session, sessions: list[Session], expected_digest: str,
                rng: random.Random, run_id: str, run_dir: RunDir) -> tuple[dict, list[Op], bool]:
    engine, scenario, n = config.engine, config.scenario, config.clients
    reasons: list[str] = []

    # 1. Reset, and check the precondition.
    if not engine.health().get("ok"):
        reasons.append("the engine was unhealthy before the trial")
    engine.reset(admin)
    scenario.setup(admin, n)
    precondition_digest = digest(scenario.precondition(scenario.observe(admin, n)))
    if precondition_digest != expected_digest:
        reasons.append("the precondition digest did not match")

    # 3. Arm: every payload is rendered before anyone is released.
    payloads = [scenario.payload(config.shape, i, n) for i in range(n)]
    barrier = threading.Barrier(n + 1)
    ops: list[Op | None] = [None] * n
    faults: list[str | None] = [None] * n

    def client_main(i: int) -> None:
        client = client_name(i)
        try:
            sessions[i].ping()  # 2. Warm.
        except Exception as exc:  # noqa: BLE001 - any warm-up failure invalidates the trial
            faults[i] = f"{client} could not warm up: {exc}"
            barrier.abort()
            return
        try:
            barrier.wait(timeout=config.trial_timeout_s)  # 4. Release.
        except threading.BrokenBarrierError:
            faults[i] = faults[i] or f"{client}: the barrier broke"
            return
        query, params, recorded = payloads[i]
        try:
            ops[i] = _execute(sessions[i], scenario, query, params, recorded, run_id, k, "race", client)  # 5. Act.
        except Exception as exc:  # noqa: BLE001 - a harness defect, never an engine answer
            faults[i] = f"{client} raised {type(exc).__name__}: {exc}"

    order = list(range(n))
    rng.shuffle(order)
    threads = [threading.Thread(target=client_main, args=(i,), name=f"wm-{client_name(i)}", daemon=True)
               for i in order]
    for thread in threads:
        thread.start()
    try:
        barrier.wait(timeout=config.trial_timeout_s)  # the coordinator is the last party
    except threading.BrokenBarrierError:
        reasons.append("the barrier broke before release")
    deadline = time.monotonic() + config.trial_timeout_s
    for thread in threads:
        thread.join(max(0.0, deadline - time.monotonic()))
    hung = any(thread.is_alive() for thread in threads)
    if hung:
        reasons.append("clients were still running at the trial timeout")

    race_ops = [op for op in ops if op is not None]
    found_faults = [fault for fault in faults if fault]
    if found_faults:
        reasons.append(f"{len(found_faults)} client fault(s), first: {found_faults[0]}")
    if len(race_ops) != n:
        reasons.append(f"{n - len(race_ops)} client(s) recorded no operation")

    # 6. Quiesce: a single engine has no background work to wait for. 7. Observe.
    if not engine.health().get("ok"):
        reasons.append("the engine was unhealthy after the trial")
    final = scenario.observe(admin, n)
    state_file = run_dir.write_state(k, final)

    # 8. Check.
    check = scenario.check(race_ops, final, n)
    invocations = [op.inv.mono_ns for op in race_ops]
    spread_ms = (max(invocations) - min(invocations)) / 1e6 if invocations else 0.0
    if config.spread_gate_ms is not None and spread_ms > config.spread_gate_ms:
        reasons.append(f"the release spread of {spread_ms:.3f} ms exceeds the gate of {config.spread_gate_ms} ms")
    unknown = sum(1 for op in race_ops if op.outcome == UNKNOWN)
    if unknown > UNKNOWN_LIMIT * n:
        reasons.append(f"{unknown} unknown outcomes exceed 5% of {n} operations")

    trial = {
        "k": k,
        "valid": not reasons,
        "precondition_digest": precondition_digest,
        "release_spread_ms": round(spread_ms, 3),
        "outcomes": {outcome: sum(1 for op in race_ops if op.outcome == outcome) for outcome in (OK, FAIL, UNKNOWN)},
        "quiesce_ms": 0.0,
        "final_state_digest": digest(final),
        "state_file": state_file,
        "checks": [check.to_json()],
    }
    if reasons:
        trial["invalid_reason"] = "; ".join(reasons)
    return trial, race_ops, hung


def _repro(config: RunConfig, run_id: str, component: dict, harness: dict) -> str:
    additional = "".join(f"- {item['name']}: `{item['image']}` (digest: `{item['digest']}`)\n"
                         for item in config.additional_components)
    return (
        f"# Reproduce run {run_id}\n\n"
        "Start the pinned baselines, then run the same configuration:\n\n"
        "```bash\n"
        "docker compose -f baselines/docker-compose.yml up -d\n"
        f"{config.command}\n"
        "```\n\n"
        f"- Harness commit: `{harness['commit']}` (dirty: {str(harness['dirty']).lower()})\n"
        f"- Engine: {component.get('name')} {component.get('version')}\n"
        f"- Image: `{component.get('image', 'unknown')}`\n"
        f"- Digest: `{component.get('digest', 'unknown')}`\n"
        f"{additional}"
        f"- Clients: {config.clients}; trials: {config.trials}; seed: {config.seed}\n"
    )


def default_command(config: RunConfig) -> str:
    args = ["python", "wm.py", "run", "--engine", config.engine.name, "--scenario", config.scenario.id,
            "--shape", config.shape, "--clients", str(config.clients), "--trials", str(config.trials),
            "--seed", str(config.seed)]
    if config.spread_gate_ms is None:
        args.append("--no-spread-gate")
    else:
        args += ["--spread-gate-ms", str(config.spread_gate_ms)]
    return shlex.join(args)


def run(config: RunConfig, *, prepare=None) -> dict:
    engine, scenario, n = config.engine, config.scenario, config.clients
    expectation = config.expectation or EXPECTATIONS.get((engine.name, config.scenario_id))
    if expectation is None:
        raise ValueError(f"no expectation is recorded for {engine.name} {config.scenario_id} (scenarios.EXPECTATIONS)")
    if not config.command:
        config.command = default_command(config)

    started = utc_now()
    component = engine.describe()
    harness = env.harness_info(config.repo_root)
    host = env.host_info() if config.capture_environment else {"os": "test", "cpu": "test", "cores": 0, "memory_gb": 0}
    target = {"name": engine.name, "repo": engine.repo, "ref": component.get("version", "unknown")}
    if component.get("digest"):
        target["digest"] = component["digest"]
    header = {
        "harness": harness,
        "target": target,
        "components": [component, *config.additional_components],
        "host": host,
        "scenario": {
            "id": config.scenario_id,
            "invariants": [scenario.invariant],
            "mode": "thread",
            "clients": n,
            "trials": config.trials,
            "params": {
                "shape": config.shape,
                "query": scenario.shapes[config.shape],
                "timeout_s": config.timeout_s,
                "spread_gate_ms": config.spread_gate_ms,
            },
        },
        "seed": config.seed,
        "started_at": iso(started),
    }
    run_id = make_run_id(started, header)
    run_dir = RunDir(config.evidence_root, config.evidence_dir or engine.name, config.scenario_id, run_id)
    history: list[Op] = []
    try:
        with prepare(run_id, history) if prepare else nullcontext():
            return _run_body(config, expectation, header, run_id, run_dir, component, harness, history)
    except Exception:
        if prepare and history:
            run_dir.write_history(history)
        crash_note(run_dir.path, run_id, traceback.format_exc())
        raise


def _run_body(config: RunConfig, expectation: Expectation, header: dict, run_id: str, run_dir: RunDir,
              component: dict, harness: dict, history: list[Op]) -> dict:
    engine, scenario, n = config.engine, config.scenario, config.clients
    trials: list[dict] = []
    admin = engine.session(config.timeout_s)
    sessions: list[Session] = []
    try:
        sessions = [engine.session(config.timeout_s) for _ in range(n)]

        # Sequential control (k = 0): the same operations, one at a time, from the same reset.
        engine.reset(admin)
        scenario.setup(admin, n)
        expected_digest = digest(scenario.precondition(scenario.observe(admin, n)))
        control_ops = []
        for i in range(n):
            sessions[i].ping()
            query, params, recorded = scenario.payload(config.shape, i, n)
            control_ops.append(_execute(sessions[i], scenario, query, params, recorded, run_id, 0, "control",
                                        client_name(i)))
        control_state = scenario.observe(admin, n)
        run_dir.write_state(0, control_state)
        sequential_met, sequential_expected, sequential_observed = scenario.sequential_expected(
            control_ops, control_state, n)
        history.extend(control_ops)

        rng = random.Random(config.seed)
        for k in range(1, config.trials + 1):
            trial, race_ops, hung = _race_trial(config, k, admin, sessions, expected_digest, rng, run_id, run_dir)
            trials.append(trial)
            history.extend(race_ops)
            if hung:
                break  # a hung client may still hold its session; later trials would not be independent
    finally:
        for session in sessions:
            session.close()
        admin.close()

    configuration = f"{engine.name} {config.scenario_id}: {n} clients x {len(trials)} trials"
    controls = [
        {
            "kind": "sequential",
            "configuration": f"{engine.name} {config.scenario_id}: {n} clients, one at a time",
            "expected": sequential_expected,
            "observed": sequential_observed,
            "met": sequential_met,
        },
        role_control(expectation.role, configuration, trials),
    ]
    unit = trials[0]["checks"][0]["unit"] if trials else ""
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "batch": config.batch,
        **header,
        "finished_at": iso(utc_now()),
        "expectation": {
            "role": expectation.role,
            "basis": expectation.basis,
            "basis_ref": expectation.basis_ref,
            "known_deviation": expectation.known_deviation,
        },
        "controls": controls,
        "trials": trials,
        "verdicts": [verdict(scenario.invariant, trials, sequential_met, expectation, unit)],
    }
    run_dir.write_history(history)
    run_dir.write_manifest(manifest)
    run_dir.write_repro(_repro(config, run_id, component, harness))
    manifest["path"] = run_dir.path.as_posix()
    return manifest


def run_sequential_control(engine: Engine, scenario: Scenario, shape: str, clients: int, *,
                           timeout_s: float = 60.0, run_id: str = "sequential-control") -> dict:
    """Run only the runner's sequential control, without creating evidence.

    Target smoke suites use this to exercise the exact adapter, classifier and
    history mapping that a later race uses while keeping their provisional
    output under ``.state/scratch``.
    """
    admin = engine.session(timeout_s)
    sessions: list[Session] = []
    try:
        sessions = [engine.session(timeout_s) for _ in range(clients)]
        engine.reset(admin)
        scenario.setup(admin, clients)
        ops = []
        for i in range(clients):
            sessions[i].ping()
            query, params, recorded = scenario.payload(shape, i, clients)
            ops.append(_execute(sessions[i], scenario, query, params, recorded, run_id, 0, "control",
                                client_name(i)))
        state = scenario.observe(admin, clients)
        met, expected, observed = scenario.sequential_expected(ops, state, clients)
        return {"met": met, "expected": expected, "observed": observed,
                "operations": ops, "state": state, "checks": [scenario.check(ops, state, clients)]}
    finally:
        for session in sessions:
            session.close()
        admin.close()
