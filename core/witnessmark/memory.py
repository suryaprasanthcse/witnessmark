"""Memory-layer runs (master blueprint sections 4.2, 5 and 6).

Three run shapes share one evidence format:

- race: a sequential control (k = 0), then T trials whose ingest operations are
  released together, in ``asyncio``, ``queue`` or ``process`` mode;
- cases: known-answer cases, one after another (each case is one trial);
- visibility: ingest, then poll a search until the write shows up (I3).

Stub calls made inside the target are recorded as history operations too, so
the evidence shows what the model was shown and what it answered.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import multiprocessing
import os
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from . import SCHEMA_VERSION, env
from .checkers import Check
from .evidence import RunDir, crash_note, digest, make_run_id
from .history import FAIL, OK, UNKNOWN, Op
from .stubs import CURRENT_OP
from .timing import Stamp, iso, stamp, utc_now
from .verdicts import summarize

MODES = ("asyncio", "queue", "process")


class MemoryTarget(ABC):
    """The memory-layer adapter contract (master blueprint section 4.2)."""

    name: str
    repo: str

    async def open(self) -> None:
        """Connect and build the library instance."""

    async def close(self) -> None:
        """Release connections."""

    @abstractmethod
    def identity(self) -> dict:
        """The run.json target record: name, repo, ref, commit or digest, package_version."""

    @abstractmethod
    def components(self) -> list[dict]:
        """Component records: the library, its backend, the stubs."""

    @abstractmethod
    async def reset(self, group: str) -> None:
        """Empty one group and make it ready (indexes built and operational)."""

    @abstractmethod
    async def ingest(self, item: dict, group: str) -> dict: ...

    @abstractmethod
    async def search(self, query: str, group: str) -> list[str]:
        """The facts returned for ``query``."""

    @abstractmethod
    async def dump(self, group: str) -> dict:
        """The canonical state of one group."""

    async def quiesce(self) -> None:
        """Wait for background work the library started."""

    def drain_stub_calls(self) -> list[dict]:
        return []


@dataclass(frozen=True)
class TargetSpec:
    """How to build a target in any process: an importable module, a factory, its options."""

    module: str
    factory: str
    options: dict = field(default_factory=dict)

    def build(self) -> MemoryTarget:
        return getattr(importlib.import_module(self.module), self.factory)(**self.options)


class RaceScenario(ABC):
    id: str
    invariants: tuple[str, ...]
    support: str = "supported"  # supported | boundary | none: what the target says about this concurrency
    basis: str = "documented"
    basis_ref: str = ""

    @abstractmethod
    def clients(self) -> list[tuple[str, dict]]:
        """One (group, item) per client, in client order."""

    def groups(self) -> list[str]:
        return sorted({group for group, _ in self.clients()})

    async def setup(self, target: MemoryTarget, group: str) -> None:
        """Ingest anything a trial starts from (after reset)."""

    @abstractmethod
    def check(self, ops: list[Op], states: dict[str, dict]) -> list[Check]: ...

    @abstractmethod
    def sequential_expected(self, ops: list[Op], states: dict[str, dict]) -> tuple[bool, str, str]: ...


@dataclass(frozen=True)
class Case:
    id: str
    group: str
    setup: tuple[dict, ...]
    item: dict


class CaseSuite(ABC):
    id: str
    invariants: tuple[str, ...]

    @abstractmethod
    def cases(self) -> list[Case]: ...

    @abstractmethod
    def check(self, case: Case, ops: list[Op], state: dict) -> list[Check]: ...

    def suite_checks(self, states: dict[str, dict]) -> list[Check]:
        """Checks across cases, e.g. a metamorphic relation between two of them."""
        return []


class VisibilityScenario(ABC):
    id: str
    invariants: tuple[str, ...] = ("I3",)

    @abstractmethod
    def group(self) -> str: ...

    @abstractmethod
    def items(self) -> list[tuple[dict, str, str]]:
        """(item, query, the fact that must come back), in order."""


@dataclass
class MemoryRunConfig:
    spec: TargetSpec
    mode: str = "asyncio"
    trials: int = 20
    processes: int = 4
    seed: int = 0
    op_timeout_s: float = 300.0
    trial_timeout_s: float = 900.0
    poll_interval_s: float = 0.01
    poll_budget_s: float = 5.0
    evidence_root: Path = Path("evidence")
    repo_root: Path = Path(".")
    evidence_dir: str = "memory"  # under evidence_root, e.g. "graphiti/v0.31.2.falkordb"
    batch: str | None = None
    command: str = ""


# --- operations ----------------------------------------------------------------------------------------------


async def _ingest(target: MemoryTarget, run_id: str, k: int, phase: str, client: str, group: str, item: dict,
                  timeout_s: float, queue: asyncio.Lock | None = None) -> Op:
    op_id = f"{k}-{client}-0"
    token = CURRENT_OP.set({"client": client, "op_id": op_id})
    recorded = {"group": group, "tag": item.get("tag"), "entry": item.get("entry", "add_episode")}
    inv = stamp()  # the client's invocation: a request waiting in a queue is already in flight
    try:
        if queue is None:
            result = await asyncio.wait_for(target.ingest(item, group), timeout_s)
        else:
            async with queue:
                result = await asyncio.wait_for(target.ingest(item, group), timeout_s)
    except asyncio.TimeoutError:
        return Op(run_id, k, phase, op_id, client, "ingest", recorded, inv, None, UNKNOWN, None,
                  {"type": "unavailable.timeout", "message": f"no answer in {timeout_s} s"}, process=str(os.getpid()))
    except Exception as exc:  # noqa: BLE001 - a library error may leave partial writes, so the outcome is unknown
        return Op(run_id, k, phase, op_id, client, "ingest", recorded, inv, None, UNKNOWN, None,
                  {"type": f"target.{type(exc).__name__}", "message": str(exc)[:500]}, process=str(os.getpid()))
    finally:
        CURRENT_OP.reset(token)
    return Op(run_id, k, phase, op_id, client, "ingest", recorded, inv, stamp(), OK, result, process=str(os.getpid()))


def _as_stamp(value) -> Stamp:
    return value if isinstance(value, Stamp) else Stamp(value["mono_ns"], value["wall"], value.get("domain", "host"))


def _stub_ops(calls: list[dict], run_id: str, k: int, start: int = 0) -> list[Op]:
    ops = []
    for n, call in enumerate(calls, start):
        ops.append(Op(run_id, k, "stub", f"{k}-stub-{n:04d}", call.get("client") or "setup", "llm",
                      {"prompt": call["prompt"], "request_sha256": call["request_sha256"], "for": call.get("op_id")},
                      _as_stamp(call["inv"]), _as_stamp(call["ret"]), OK,
                      {"decision": call["decision"], "response_sha256": call["response_sha256"]},
                      process=call.get("process")))
    return ops


def release_spread_ms(ops: list[Op], mode: str) -> float:
    """Spread of the first invocation in each lane: each client, or in process mode each worker process."""
    firsts: dict[str, int] = {}
    for op in ops:
        lane = op.process if mode == "process" else op.client
        firsts[lane] = min(firsts.get(lane, op.inv.mono_ns), op.inv.mono_ns)
    values = list(firsts.values())
    return round((max(values) - min(values)) / 1e6, 3) if values else 0.0


def max_in_flight(ops: list[Op]) -> int:
    """The most operations in flight at once; an unknown outcome stays in flight to the end."""
    events = []
    for op in ops:
        events.append((op.inv.mono_ns, 1))
        events.append((op.ret.mono_ns if op.ret else float("inf"), -1))
    current = best = 0
    for _, delta in sorted(events, key=lambda event: (event[0], event[1])):
        current += delta
        best = max(best, current)
    return best


# --- process mode --------------------------------------------------------------------------------------------


def _process_child(spec: TargetSpec, assignments: list, barrier, conn, run_id: str, k: int,
                   timeout_s: float) -> None:
    async def main():
        target = spec.build()
        await target.open()
        try:
            barrier.wait(timeout_s)  # every process is connected and warm before release
            ops = [await _ingest(target, run_id, k, "race", client, group, item, timeout_s)
                   for client, group, item in assignments]  # one process works through its share in order
            calls = target.drain_stub_calls()
            for call in calls:
                call["process"] = str(os.getpid())
                call["inv"], call["ret"] = _as_stamp(call["inv"]).to_json(), _as_stamp(call["ret"]).to_json()
            return ops, calls
        finally:
            await target.close()

    try:
        ops, calls = asyncio.run(main())
        conn.send({"ops": [op.to_json() for op in ops], "calls": calls})
    except Exception:  # noqa: BLE001 - report the failure to the parent rather than dying silently
        conn.send({"error": traceback.format_exc()})
    finally:
        conn.close()


def _race_in_processes(spec: TargetSpec, clients: list, processes: int, run_id: str, k: int,
                       op_timeout_s: float, trial_timeout_s: float) -> tuple[list[Op], list[Op], list[str]]:
    count = max(1, min(processes, len(clients)))
    shares: list[list] = [[] for _ in range(count)]
    for index, (group, item) in enumerate(clients):
        shares[index % count].append((f"c{index:02d}", group, item))
    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(count + 1)
    receivers, workers = [], []
    for share in shares:
        receiver, sender = context.Pipe(duplex=False)
        worker = context.Process(target=_process_child, args=(spec, share, barrier, sender, run_id, k, op_timeout_s))
        worker.start()
        sender.close()
        receivers.append(receiver)
        workers.append(worker)
    faults: list[str] = []
    try:
        barrier.wait(trial_timeout_s)
    except Exception as exc:  # noqa: BLE001
        faults.append(f"the barrier broke: {type(exc).__name__}")
    ops: list[Op] = []
    calls: list[dict] = []
    for receiver in receivers:
        if receiver.poll(trial_timeout_s):
            message = receiver.recv()
            if "error" in message:
                faults.append("a worker failed: " + message["error"].strip().splitlines()[-1])
            else:
                ops.extend(Op.from_json(record) for record in message["ops"])
                calls.extend(message["calls"])
        else:
            faults.append("a worker sent nothing before the trial timeout")
    for worker in workers:
        worker.join(30)
        if worker.is_alive():
            worker.terminate()
            faults.append("a worker had to be terminated")
    ops.sort(key=lambda op: op.client)
    calls.sort(key=lambda call: call["inv"]["mono_ns"])
    return ops, _stub_ops(calls, run_id, k), faults


# --- shared run plumbing -------------------------------------------------------------------------------------


def _run_dir(config: MemoryRunConfig, scenario_id: str, run_id: str) -> RunDir:
    root = Path(config.evidence_root) / config.evidence_dir
    return RunDir(root.parent, root.name, scenario_id, run_id)


def _header(config: MemoryRunConfig, target: MemoryTarget, scenario_id: str, invariants, mode: str, clients: int,
            trials: int, started, params: dict) -> dict:
    return {
        "harness": env.harness_info(config.repo_root),
        "target": target.identity(),
        "components": target.components(),
        "host": env.host_info(),
        "scenario": {"id": scenario_id, "invariants": list(invariants), "mode": mode, "clients": clients,
                     "trials": trials, "params": params},
        "seed": config.seed,
        "started_at": iso(started),
    }


def _note_crash(scope: dict) -> None:
    """Called from an except block: leave ERROR.md, redacted, in the crashed run's directory."""
    if scope.get("run_dir") is not None:
        crash_note(scope["run_dir"].path, scope.get("run_id", "unknown"), traceback.format_exc())


def _finish(config: MemoryRunConfig, run_dir: RunDir, manifest: dict, history: list[Op]) -> dict:
    manifest["finished_at"] = iso(utc_now())
    run_dir.write_history(history)
    run_dir.write_manifest(manifest)
    run_dir.write_repro(
        f"# Reproduce run {manifest['run_id']}\n\n"
        "Start the pinned baselines, use the target's pinned environment, then run:\n\n"
        f"```bash\n{config.command}\n```\n\n"
        f"- Harness commit: `{manifest['harness']['commit']}` (dirty: {str(manifest['harness']['dirty']).lower()})\n"
        f"- Target: `{json.dumps(manifest['target'], sort_keys=True)}`\n"
    )
    manifest["path"] = run_dir.path.as_posix()
    return manifest


def _status(violating: int, valid: int, sequential_met: bool, support: str, raced_all: bool = True) -> str:
    if not sequential_met or not valid:
        return "INVALID"
    if violating:
        return {"supported": "FAIL", "boundary": "BOUNDARY"}.get(support, "OBSERVED")
    return "PASS" if raced_all else "INCONCLUSIVE"


def _verdicts(invariants, trials: list[dict], sequential_met: bool, support: str, basis: str, basis_ref: str,
              raced_all: bool = True) -> list[dict]:
    valid = [trial for trial in trials if trial["valid"]]
    records = []
    for invariant in invariants:
        mine = [[check for check in trial["checks"] if check["invariant"] == invariant] for trial in valid]
        mine = [checks for checks in mine if checks]
        violating = [checks for checks in mine if any(not check["held"] for check in checks)]
        magnitudes = [max(check["magnitude"] for check in checks) for checks in mine]
        unit = next((check["unit"] for checks in mine for check in checks), "")
        records.append({
            "invariant": invariant,
            "status": _status(len(violating), len(mine), sequential_met, support, raced_all),
            "trials_violating": len(violating),
            "trials_valid": len(mine),
            "magnitude": {**summarize(magnitudes), "unit": unit},
            "basis": basis,
            "basis_ref": basis_ref,
            "witnesses": [w for checks in violating[:3] for check in checks for w in check["witnesses"][:10]],
            "note": f"support: {support}",
        })
    return records


# --- race runs -----------------------------------------------------------------------------------------------


async def _reset_and_setup(target: MemoryTarget, scenario: RaceScenario) -> dict:
    for group in scenario.groups():
        await target.reset(group)
    for group in scenario.groups():
        await scenario.setup(target, group)
    await target.quiesce()
    return {group: await target.dump(group) for group in scenario.groups()}


async def _race_in_loop(target: MemoryTarget, scenario: RaceScenario, mode: str, run_id: str, k: int,
                        op_timeout_s: float, trial_timeout_s: float) -> list[Op]:
    clients = scenario.clients()
    barrier = asyncio.Barrier(len(clients) + 1)
    locks = {group: asyncio.Lock() for group in scenario.groups()}

    async def client_main(index: int, group: str, item: dict) -> Op:
        await barrier.wait()
        # In queue mode each group gets one FIFO, as Graphiti's MCP server queues episodes per group_id.
        return await _ingest(target, run_id, k, "race", f"c{index:02d}", group, item, op_timeout_s,
                             queue=locks[group] if mode == "queue" else None)

    tasks = [asyncio.create_task(client_main(index, group, item)) for index, (group, item) in enumerate(clients)]
    await barrier.wait()
    return list(await asyncio.wait_for(asyncio.gather(*tasks), trial_timeout_s))


async def run_race(config: MemoryRunConfig, scenario: RaceScenario) -> dict:
    if config.mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    target = config.spec.build()
    await target.open()
    try:
        started = utc_now()
        clients = scenario.clients()
        scenario_id = f"{scenario.id}.{config.mode}"
        params = {"support": scenario.support, "op_timeout_s": config.op_timeout_s,
                  "processes": config.processes if config.mode == "process" else None}
        header = _header(config, target, scenario_id, scenario.invariants, config.mode, len(clients), config.trials,
                         started, params)
        run_id = make_run_id(started, header)
        run_dir = _run_dir(config, scenario_id, run_id)
        history: list[Op] = []

        # Sequential control (k = 0): the same items, one at a time, from the same starting state.
        expected_digest = digest(await _reset_and_setup(target, scenario))
        setup_calls = _stub_ops(target.drain_stub_calls(), run_id, 0)
        control_ops = [await _ingest(target, run_id, 0, "control", f"c{index:02d}", group, item, config.op_timeout_s)
                       for index, (group, item) in enumerate(clients)]
        await target.quiesce()
        control_states = {group: await target.dump(group) for group in scenario.groups()}
        run_dir.write_state(0, control_states)
        sequential_met, sequential_expected, sequential_observed = scenario.sequential_expected(
            control_ops, control_states)
        history += setup_calls + control_ops + _stub_ops(target.drain_stub_calls(), run_id, 0, len(setup_calls))

        trials = []
        for k in range(1, config.trials + 1):
            pre = await _reset_and_setup(target, scenario)
            target.drain_stub_calls()
            faults: list[str] = []
            if config.mode == "process":
                ops, stub_ops, faults = await asyncio.to_thread(
                    _race_in_processes, config.spec, clients, config.processes, run_id, k, config.op_timeout_s,
                    config.trial_timeout_s)
            else:
                ops = await _race_in_loop(target, scenario, config.mode, run_id, k, config.op_timeout_s,
                                          config.trial_timeout_s)
                stub_ops = _stub_ops(target.drain_stub_calls(), run_id, k)
            await target.quiesce()
            states = {group: await target.dump(group) for group in scenario.groups()}
            state_file = run_dir.write_state(k, states)
            checks = scenario.check(ops, states)
            reasons = list(faults)
            if digest(pre) != expected_digest:
                reasons.append("the precondition digest did not match")
            unknown = sum(1 for op in ops if op.outcome == UNKNOWN)
            if ops and unknown > 0.05 * len(ops):
                reasons.append(f"{unknown} of {len(ops)} operations had an unknown outcome")
            if len(ops) != len(clients):
                reasons.append(f"{len(clients) - len(ops)} client(s) recorded no operation")
            trial = {
                "k": k,
                "valid": not reasons,
                "precondition_digest": digest(pre),
                "release_spread_ms": release_spread_ms(ops, config.mode),
                "max_in_flight": max_in_flight(ops),
                "outcomes": {o: sum(1 for op in ops if op.outcome == o) for o in (OK, FAIL, UNKNOWN)},
                "quiesce_ms": 0.0,
                "final_state_digest": digest(states),
                "state_file": state_file,
                "checks": [check.to_json() for check in checks],
            }
            if reasons:
                trial["invalid_reason"] = "; ".join(reasons)
            trials.append(trial)
            history += ops + stub_ops

        valid = [trial for trial in trials if trial["valid"]]
        raced = sum(1 for trial in valid if trial["max_in_flight"] >= 2)
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "batch": config.batch,
            **header,
            "expectation": {"role": "target", "support": scenario.support, "basis": scenario.basis,
                            "basis_ref": scenario.basis_ref, "known_deviation": None},
            "controls": [
                {"kind": "sequential", "configuration": f"{scenario_id}: {len(clients)} clients, one at a time",
                 "expected": sequential_expected, "observed": sequential_observed, "met": sequential_met},
                {"kind": "overlap", "configuration": f"{scenario_id}: {len(clients)} clients x {len(trials)} trials",
                 "expected": "two or more ingests in flight at once in every valid trial",
                 "observed": f"{raced} of {len(valid)} valid trials had two or more in flight",
                 "met": bool(valid) and raced == len(valid)},
            ],
            "trials": trials,
            "verdicts": _verdicts(scenario.invariants, trials, sequential_met, scenario.support, scenario.basis,
                                  scenario.basis_ref, raced_all=bool(valid) and raced == len(valid)),
        }
        return _finish(config, run_dir, manifest, history)
    except Exception:
        _note_crash(locals())
        raise
    finally:
        await target.close()


# --- known-answer cases --------------------------------------------------------------------------------------


async def run_cases(config: MemoryRunConfig, suite: CaseSuite) -> dict:
    target = config.spec.build()
    await target.open()
    try:
        started = utc_now()
        cases = suite.cases()
        header = _header(config, target, suite.id, suite.invariants, "sequential", 1, len(cases), started,
                         {"cases": [case.id for case in cases]})
        run_id = make_run_id(started, header)
        run_dir = _run_dir(config, suite.id, run_id)
        history: list[Op] = []
        trials: list[dict] = []
        states: dict[str, dict] = {}
        for k, case in enumerate(cases, 1):
            await target.reset(case.group)
            ops = []
            for n, item in enumerate(case.setup):
                ops.append(await _ingest(target, run_id, k, "setup", f"setup{n}", case.group, item,
                                         config.op_timeout_s))
            ops.append(await _ingest(target, run_id, k, "race", "c00", case.group, case.item, config.op_timeout_s))
            await target.quiesce()
            state = await target.dump(case.group)
            states[case.id] = state
            state_file = run_dir.write_state(k, {case.group: state})
            checks = suite.check(case, ops, state)
            failed = [op for op in ops if op.outcome != OK]
            trial = {
                "k": k,
                "case": case.id,
                "valid": not failed,
                "precondition_digest": "",
                "release_spread_ms": 0.0,
                "max_in_flight": 1,
                "outcomes": {o: sum(1 for op in ops if op.outcome == o) for o in (OK, FAIL, UNKNOWN)},
                "quiesce_ms": 0.0,
                "final_state_digest": digest(state),
                "state_file": state_file,
                "checks": [check.to_json() for check in checks],
            }
            if failed:
                trial["invalid_reason"] = f"{len(failed)} ingest(s) did not succeed: {failed[0].error}"
            trials.append(trial)
            history += ops + _stub_ops(target.drain_stub_calls(), run_id, k)
        suite_trial_checks = [check.to_json() for check in suite.suite_checks(states)]
        if suite_trial_checks:
            trials.append({"k": len(cases) + 1, "case": "suite", "valid": True, "precondition_digest": "",
                           "release_spread_ms": 0.0, "max_in_flight": 1,
                           "outcomes": {OK: 0, FAIL: 0, UNKNOWN: 0}, "quiesce_ms": 0.0,
                           "final_state_digest": digest(states), "state_file": "", "checks": suite_trial_checks})
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "batch": config.batch,
            **header,
            "expectation": {"role": "target", "support": "none", "basis": "issue", "basis_ref": "",
                            "known_deviation": None},
            "controls": [],
            "trials": trials,
            "verdicts": _verdicts(suite.invariants, trials, True, "none", "issue", ""),
        }
        return _finish(config, run_dir, manifest, history)
    except Exception:
        _note_crash(locals())
        raise
    finally:
        await target.close()


# --- visibility ----------------------------------------------------------------------------------------------


async def _poll(target: MemoryTarget, query: str, group: str, fact: str, since_ns: int, interval_s: float,
                budget_s: float) -> tuple[bool, float | None, int]:
    """(found on the first search, lag in ms or None if never seen, searches made)."""
    attempts = 0
    while True:
        attempts += 1
        found = fact in await target.search(query, group)
        lag_ms = (stamp().mono_ns - since_ns) / 1e6
        if found:
            return attempts == 1, (0.0 if attempts == 1 else lag_ms), attempts
        if lag_ms >= budget_s * 1000:
            return False, None, attempts
        await asyncio.sleep(interval_s)


async def run_visibility(config: MemoryRunConfig, scenario: VisibilityScenario) -> dict:
    writer, reader = config.spec.build(), config.spec.build()
    await writer.open()
    await reader.open()
    try:
        started = utc_now()
        items = scenario.items()
        header = _header(config, writer, scenario.id, scenario.invariants, "sequential", 2, len(items), started,
                         {"poll_interval_s": config.poll_interval_s, "poll_budget_s": config.poll_budget_s,
                          "readers": ["the writing instance", "a second instance with its own connections"]})
        run_id = make_run_id(started, header)
        run_dir = _run_dir(config, scenario.id, run_id)
        group = scenario.group()
        await writer.reset(group)
        history: list[Op] = []
        trials: list[dict] = []
        for k, (item, query, fact) in enumerate(items, 1):
            op = await _ingest(writer, run_id, k, "race", "c00", group, item, config.op_timeout_s)
            history.append(op)
            checks = []
            if op.outcome == OK:
                for label, target in (("same instance", writer), ("second instance", reader)):
                    first, lag, attempts = await _poll(target, query, group, fact, op.ret.mono_ns,
                                                       config.poll_interval_s, config.poll_budget_s)
                    checks.append(Check(
                        "I3", first, lag if lag is not None else config.poll_budget_s * 1000, "ms",
                        f"{label}: {'seen on the first search' if first else f'seen after {lag:.1f} ms and {attempts} searches' if lag is not None else 'never seen within the budget'}",
                        [] if first else [op.op_id]))
            history += _stub_ops(writer.drain_stub_calls(), run_id, k)
            trials.append({
                "k": k, "valid": op.outcome == OK, "precondition_digest": "", "release_spread_ms": 0.0,
                "max_in_flight": 1, "outcomes": {o: int(op.outcome == o) for o in (OK, FAIL, UNKNOWN)},
                "quiesce_ms": 0.0, "final_state_digest": "", "state_file": "",
                "checks": [check.to_json() for check in checks],
            })
        await writer.quiesce()
        run_dir.write_state(0, {group: await writer.dump(group)})
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "batch": config.batch,
            **header,
            "expectation": {"role": "target", "support": "none", "basis": "inferred", "basis_ref": "",
                            "known_deviation": None},
            "controls": [],
            "trials": trials,
            "verdicts": _verdicts(scenario.invariants, trials, True, "none", "inferred", ""),
        }
        return _finish(config, run_dir, manifest, history)
    except Exception:
        _note_crash(locals())
        raise
    finally:
        await writer.close()
        await reader.close()
