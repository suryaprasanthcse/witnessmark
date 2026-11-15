"""O2b: the cost curve of conditional claims on disjoint tasks.

N agents claim N different tasks. On Omnigraph each claim is conditioned on
the graph commit id the agent read, so any intervening commit, even one that
touches a different task, invalidates it (O-K3). The run measures what that
costs; it is not a correctness test. The FalkorDB side sends the naive guarded
claim (master 7.6, claim.state naive) on N WMTask nodes, with N clients.

The retry policy, the metrics and the holder check are plain functions over
recorded steps, so unit tests drive them with fakes and no containers.
"""

from __future__ import annotations

import random
import statistics
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from witnessmark import env as witnessmark_env
from witnessmark.adapters import make_engine
from witnessmark.adapters.base import EngineError, EngineUnavailable
from witnessmark.evidence import RunDir, digest, make_run_id
from witnessmark.history import FAIL, OK, UNKNOWN
from witnessmark.scenarios import ClaimState, client_name
from witnessmark.timing import Stamp, iso, stamp, utc_now

from .actors import describe as describe_actors
from .capture import OperationCapture, RunCapture, repro_command
from .client import OmnigraphClient, OperationResult, Outcome
from .engine import _token
from .part2 import Stack, _check, _error_note, _manifest, _percentile, _run_id, _summary, _utc
from .runner_scenarios import SKILL
from .workload import load_queries

AGENTS = (1, 2, 5, 10, 25, 50)
SMOKE_AGENTS = (1, 2)
WARMUPS = 3
REPETITIONS = 5
SMOKE_WARMUPS = 1
SMOKE_REPETITIONS = 1
MAX_ATTEMPTS = 200
UNKNOWN_LIMIT = 0.05  # at most 5% of a trial's operations may have an unknown outcome (master 6.3)
TRIAL_TIMEOUT_S = 600.0
OPEN_STATE = "open"
RETRY_ON = ("precondition_failure",)
UNTIL_MAX = 9_223_372_036_854_775_807
OMNIGRAPH_ID, OMNIGRAPH_MODE = "o2b.disjoint_claims", "sweep"
FALKOR_ID = "o2b.claim_state_disjoint.sweep"
POLICY = ("read the task and the graph commit id, submit m_claim_cond conditioned on that commit id; on "
          "precondition_failure read again and resubmit, until it succeeds or reaches the cap; any other "
          "refusal, a task no longer open, or an unknown outcome ends the agent")
INTERPRETATION = ("a cost of documented behaviour (any intervening commit invalidates a conditional claim, "
                  "O-K3), not a defect")


def task_name(i: int) -> str:
    return f"task-{i}"


# ---------------------------------------------------------------- the retry policy

@dataclass
class Step:
    """One operation an agent issued, in the form the history records."""

    kind: str  # "read" or "claim"
    inputs: dict
    inv: Stamp
    ret: Stamp | None
    outcome: str  # ok | fail | unknown
    result: dict | None = None
    error: dict | None = None
    token: str | None = None
    is_open: bool = True  # reads: the task still read as open

    @property
    def error_type(self) -> str | None:
        return (self.error or {}).get("type")


@dataclass
class AgentRun:
    client: str
    steps: list[Step] = field(default_factory=list)
    attempts: int = 0  # claim submissions
    status: str = "pending"  # claimed | capped | refused | unknown | read_failed | not_open | no_commit_id

    @property
    def claimed(self) -> bool:
        return self.status == "claimed"


def drive_agent(client: str, read: Callable[[int], Step] | None, claim: Callable[[str | None, int], Step], *,
                cap: int = MAX_ATTEMPTS, retry_on: tuple[str, ...] = RETRY_ON) -> AgentRun:
    """Re-read and decide again after a retryable refusal; never retry blindly.

    ``read`` is None for a claim that carries its own guard (the FalkorDB side).
    """
    run = AgentRun(client)
    while True:
        if run.attempts >= cap:
            run.status = "capped"
            return run
        commit = None
        if read is not None:
            seen = read(run.attempts + 1)
            run.steps.append(seen)
            if seen.outcome == UNKNOWN:
                run.status = "unknown"
                return run
            if seen.outcome != OK:
                run.status = "read_failed"
                return run
            if not seen.is_open:
                run.status = "not_open"
                return run
            commit = seen.token
            if commit is None:
                run.status = "no_commit_id"
                return run
        run.attempts += 1
        made = claim(commit, run.attempts)
        run.steps.append(made)
        if made.outcome == OK:
            run.status = "claimed"
            return run
        if made.outcome == UNKNOWN:
            run.status = "unknown"
            return run
        if made.error_type not in retry_on:
            run.status = "refused"
            return run


# ---------------------------------------------------------------- steps from each engine

def _step_from_result(kind: str, inputs: dict, inv: Stamp, ret: Stamp, result: OperationResult) -> Step:
    token = _token(result)
    if result.outcome is Outcome.OK:
        return Step(kind, inputs, inv, ret, OK, token=token)
    error = {"type": result.kind or "http_error", "message": result.message or "request failed"}
    if result.status is not None:
        error["code"] = result.status
    if result.outcome is Outcome.UNKNOWN:
        return Step(kind, inputs, inv, None, UNKNOWN, error=error)
    return Step(kind, inputs, inv, ret, FAIL, error=error)


def omnigraph_agent(client: OmnigraphClient, queries: dict[str, str], i: int, *, cap: int = MAX_ATTEMPTS) -> AgentRun:
    task, agent = task_name(i), client_name(i)

    def read(attempt: int) -> Step:
        inputs = {"query": "q_task", "task": task, "attempt": attempt}
        inv = stamp()
        result = client.query(queries["q_task"], {"task_id": task}, name="q_task")
        step = _step_from_result("read", inputs, inv, stamp(), result)
        if step.outcome == OK:
            data = result.data if isinstance(result.data, dict) else {}
            rows = data.get("rows") or []
            state = rows[0].get("state") if rows and isinstance(rows[0], dict) else None
            step.is_open = state == OPEN_STATE
            step.result = {"state": state}
        return step

    def claim(commit: str | None, attempt: int) -> Step:
        params = {"task_id": task, "agent_id": agent, "from_seq": i + 1, "until_pt": UNTIL_MAX,
                  "rw": f"lease-{i:02d}"}
        inputs = {"mutation": "m_claim_cond", "task": task, "agent": agent, "attempt": attempt,
                  "if_graph_commit": commit}
        inv = stamp()
        result = client.mutate(queries["m_claim_cond"], params, name="m_claim_cond", commit_id=commit)
        step = _step_from_result("claim", inputs, inv, stamp(), result)
        if step.outcome == OK:
            step.result = {"won": 1, "commit": step.token}
        return step

    return drive_agent(agent, read, claim, cap=cap)


def falkordb_agent(session, i: int, *, cap: int = MAX_ATTEMPTS) -> AgentRun:
    task, agent = task_name(i), client_name(i)
    query = ClaimState.shapes["naive"]

    def claim(_commit: str | None, attempt: int) -> Step:
        inputs = {"mutation": "claim.state.naive", "task": task, "agent": agent, "attempt": attempt}
        inv = stamp()
        try:
            reply = session.run(query, {"task": task, "agent": agent})
        except EngineError as exc:
            return Step("claim", inputs, inv, stamp(), FAIL, error=exc.to_json())
        except EngineUnavailable as exc:
            return Step("claim", inputs, inv, None, UNKNOWN, error=exc.to_json())
        ret = stamp()
        won = int(reply.scalar(0) or 0)
        if won == 1:
            return Step("claim", inputs, inv, ret, OK, result={"won": 1})
        return Step("claim", inputs, inv, ret, FAIL, result={"won": won},
                    error={"type": "guard_false", "message": "the task was not open"})

    return drive_agent(agent, None, claim, cap=cap)


# ---------------------------------------------------------------- metrics

def _latencies(runs: list[AgentRun], kind: str) -> list[float]:
    return [(step.ret.mono_ns - step.inv.mono_ns) / 1e6
            for run in runs for step in run.steps if step.kind == kind and step.ret is not None]


def _latency_summary(values: list[float]) -> dict:
    return {"n": len(values), "p50": _percentile(values, 50), "p99": _percentile(values, 99)}


def trial_metrics(runs: list[AgentRun]) -> dict:
    """What one trial cost. Wasted attempts are claim submissions that did not claim."""
    attempts = [run.attempts for run in runs]
    claimed = sum(1 for run in runs if run.claimed)
    steps = [step for run in runs for step in run.steps]
    firsts = [run.steps[0].inv.mono_ns for run in runs if run.steps]
    origin = min(firsts) if firsts else None
    claim_returns = [step.ret.mono_ns for run in runs for step in run.steps
                     if step.kind == "claim" and step.outcome == OK and step.ret is not None]
    last = [step.ret.mono_ns for step in steps if step.ret is not None]
    statuses: dict[str, int] = {}
    for run in runs:
        statuses[run.status] = statuses.get(run.status, 0) + 1
    all_claimed = bool(runs) and claimed == len(runs)
    return {
        "attempts_total": sum(attempts),
        "claimed": claimed,
        "wasted_attempts": sum(attempts) - claimed,
        "agent_attempts": attempts,
        "agent_attempts_median": statistics.median(attempts) if attempts else None,
        "agent_attempts_max": max(attempts) if attempts else None,
        "agent_status": statuses,
        "release_spread_ms": round((max(firsts) - origin) / 1e6, 3) if firsts else 0.0,
        "time_to_all_claimed_ms": round((max(claim_returns) - origin) / 1e6, 3)
        if all_claimed and origin is not None else None,
        "time_to_last_event_ms": round((max(last) - origin) / 1e6, 3) if last and origin is not None else None,
        "claim_latency_ms": _latency_summary(_latencies(runs, "claim")),
        "read_latency_ms": _latency_summary(_latencies(runs, "read")),
        "operations": len(steps),
        "unknown_operations": sum(1 for step in steps if step.outcome == UNKNOWN),
    }


def agent_index(run: AgentRun) -> int:
    return int(run.client[1:])


def check_holders(runs: list[AgentRun], observed: dict) -> dict:
    """After a trial every task has exactly one holder, its own agent.

    An agent that did not finish its claim holds nothing, except that one whose
    outcome was unknown may or may not hold its task. Nobody else may hold it.
    """
    held = {row["task"]: list(row.get("holders") or []) for row in observed.get("tasks", [])}
    violations = []
    for run in runs:
        i = agent_index(run)
        task, agent = task_name(i), run.client
        holders = held.get(task)
        if holders is None:
            violations.append(f"{task}: not found")
        elif run.claimed:
            if holders != [agent]:
                violations.append(f"{task}: acknowledged to {agent}, holders {holders}")
        elif holders not in ([[], [agent]] if run.status == "unknown" else [[]]):
            violations.append(f"{task}: {agent} ended {run.status}, holders {holders}")
    extra = sorted(set(held) - {task_name(agent_index(run)) for run in runs})
    if extra and len(runs) == len(held):
        violations.append(f"unexpected tasks {extra}")
    return {"held": not violations, "violations": violations}


def spread_gate(gate_ms: float | None) -> dict:
    if gate_ms is None:
        return {"state": "off", "gate_ms": None,
                "note": "release spread recorded without gating; Omnigraph's delta is set in Phase B (master 12.1)"}
    return {"state": "on", "gate_ms": gate_ms}


def evaluate_trial(k: int, n: int, round_index: int, warmup: bool, runs: list[AgentRun], *,
                   faults: list[str], hung: bool, healthy_before: bool, healthy_after: bool,
                   precondition_ok: bool, observed: dict, gate_ms: float | None) -> dict:
    """The manifest entry for one trial: metrics, the holder check and the validity gates (master 6.3)."""
    reasons: list[str] = []
    if not healthy_before:
        reasons.append("the engine was unhealthy before the trial")
    if not healthy_after:
        reasons.append("the engine was unhealthy after the trial")
    if not precondition_ok:
        reasons.append("the precondition digest did not match")
    if hung:
        reasons.append("clients were still running at the trial timeout")
    if faults:
        reasons.append(f"{len(faults)} client fault(s), first: {faults[0]}")
    if len(runs) != n:
        reasons.append(f"{n - len(runs)} client(s) recorded no run")
    metrics = trial_metrics(runs)
    if gate_ms is not None and metrics["release_spread_ms"] > gate_ms:
        reasons.append(f"the release spread of {metrics['release_spread_ms']} ms exceeds the gate of {gate_ms} ms")
    if metrics["unknown_operations"] > UNKNOWN_LIMIT * max(1, metrics["operations"]):
        reasons.append(f"{metrics['unknown_operations']} unknown outcomes exceed 5% of {metrics['operations']} operations")
    holders = check_holders(runs, observed)
    trial = {"k": k, "n": n, "round": round_index, "warmup": warmup, "valid": not reasons, **metrics,
             "holders_ok": holders["held"], "violations": holders["violations"]}
    if reasons:
        trial["invalid_reason"] = "; ".join(reasons)
    return trial


SUMMARY_FIELDS = (
    ("attempts_total", lambda t: t["attempts_total"]),
    ("wasted_attempts", lambda t: t["wasted_attempts"]),
    ("agent_attempts_median", lambda t: t["agent_attempts_median"]),
    ("agent_attempts_max", lambda t: t["agent_attempts_max"]),
    ("time_to_all_claimed_ms", lambda t: t["time_to_all_claimed_ms"]),
    ("claim_latency_p50_ms", lambda t: t["claim_latency_ms"]["p50"]),
    ("claim_latency_p99_ms", lambda t: t["claim_latency_ms"]["p99"]),
    ("release_spread_ms", lambda t: t["release_spread_ms"]),
)


def summarize_sweep(trials: list[dict], agents: tuple[int, ...]) -> list[dict]:
    """Medians and interquartile ranges per N over the measured, valid repetitions."""
    rows = []
    for n in agents:
        measured = [t for t in trials if t["n"] == n and not t["warmup"]]
        valid = [t for t in measured if t["valid"]]
        row = {"n": n, "measured_repetitions": len(measured), "valid_repetitions": len(valid),
               "invalid_repetitions": len(measured) - len(valid)}
        for name, pick in SUMMARY_FIELDS:
            values = [pick(t) for t in valid if pick(t) is not None]
            row[name] = _summary(values)
        rows.append(row)
    return rows


def findings_for(run_id: str, trials: list[dict]) -> list[dict]:
    return [{"run_id": run_id, "k": t["k"], "n": t["n"], "kind": "holder_violation", "detail": t["violations"]}
            for t in trials if t["violations"]]


# ---------------------------------------------------------------- the barrier

def race_agents(n: int, warm: Callable[[int], None], work: Callable[[int], AgentRun], *,
                rng: random.Random, timeout_s: float = TRIAL_TIMEOUT_S) -> tuple[list[AgentRun], list[str], bool]:
    """Release n agent threads together, as the core thread runner does (core/witnessmark/runner.py)."""
    barrier = threading.Barrier(n + 1)
    runs: list[AgentRun | None] = [None] * n
    faults: list[str | None] = [None] * n

    def main(i: int) -> None:
        try:
            warm(i)
        except Exception as exc:  # noqa: BLE001 - any warm-up failure invalidates the trial
            faults[i] = f"{client_name(i)} could not warm up: {exc}"
            barrier.abort()
            return
        try:
            barrier.wait(timeout=timeout_s)
        except threading.BrokenBarrierError:
            faults[i] = faults[i] or f"{client_name(i)}: the barrier broke"
            return
        try:
            runs[i] = work(i)
        except Exception as exc:  # noqa: BLE001 - a harness defect, never an engine answer
            faults[i] = f"{client_name(i)} raised {type(exc).__name__}: {exc}"

    order = list(range(n))
    rng.shuffle(order)
    threads = [threading.Thread(target=main, args=(i,), name=f"wm-o2b-{client_name(i)}", daemon=True)
               for i in order]
    for thread in threads:
        thread.start()
    problems: list[str] = []
    try:
        barrier.wait(timeout=timeout_s)
    except threading.BrokenBarrierError:
        problems.append("the barrier broke before release")
    deadline = time.monotonic() + timeout_s
    for thread in threads:
        thread.join(max(0.0, deadline - time.monotonic()))
    hung = any(thread.is_alive() for thread in threads)
    found = [fault for fault in faults if fault] + problems
    return [run for run in runs if run is not None], found, hung


def emit_runs(capture: OperationCapture, runs: list[AgentRun]) -> None:
    """Write every step after the race, so no file I/O falls inside it."""
    steps = [(run.client, step) for run in runs for step in run.steps]
    for client, step in sorted(steps, key=lambda item: item[1].inv.mono_ns):
        capture.record(client, step.kind, step.inputs, step.inv, step.ret, step.outcome, result=step.result,
                       error=step.error, token=step.token, phase="race")


# ---------------------------------------------------------------- the sweep

def sweep_plan(smoke: bool) -> dict:
    agents, warmups, repetitions = (SMOKE_AGENTS, SMOKE_WARMUPS, SMOKE_REPETITIONS) if smoke else \
        (AGENTS, WARMUPS, REPETITIONS)
    return {"agents": list(agents), "warmups": warmups, "measured_repetitions": repetitions,
            "max_attempts": MAX_ATTEMPTS, "policy": POLICY, "interleaving": "rounds over N"}


def rounds(plan: dict):
    """Interleave the configurations: every round runs each N once (master 6.5)."""
    for index in range(plan["warmups"] + plan["measured_repetitions"]):
        for n in plan["agents"]:
            yield index, n, index < plan["warmups"]


def observe_omnigraph(client: OmnigraphClient, queries: dict[str, str], n: int, *, holders: bool) -> dict:
    tasks = []
    for i in range(n):
        task = task_name(i)
        read = _check(client.query(queries["q_task"], {"task_id": task}, name="q_task"), f"read {task}")
        data = read.data if isinstance(read.data, dict) else {}
        rows = data.get("rows") or []
        row = {"task": task, "state": rows[0].get("state") if rows else None}
        if holders:
            snapshot = data.get("graph_commit_id")
            found = _check(client.query(queries["q_task_holder"], {"task_id": task}, name="q_task_holder",
                                        snapshot=snapshot), f"read the holder of {task}")
            held = found.data.get("rows") if isinstance(found.data, dict) else []
            row["holders"] = [str(item["holder"]) for item in held or []]
        tasks.append(row)
    return {"tasks": tasks}


def _setup_omnigraph(admin: OmnigraphClient, queries: dict[str, str], n: int) -> None:
    _check(admin.mutate(queries["m_reset"], {}, name="m_reset"), "reset the O2b graph")
    _check(admin.mutate(queries["m_fixture_base"], {"task_id": task_name(0), "skill_id": SKILL},
                        name="m_fixture_base"), "create the first task")
    for i in range(1, n):
        _check(admin.mutate(queries["m_fixture_task"], {"task_id": task_name(i), "skill_id": SKILL},
                            name="m_fixture_task"), f"create {task_name(i)}")
    for i in range(n):
        _check(admin.mutate(queries["m_fixture_agent"], {"agent_id": client_name(i), "skill_id": SKILL},
                            name="m_fixture_agent"), f"create {client_name(i)}")


def _finish_sweep(manifest_fields: dict, trials: list[dict], plan: dict, run_id: str) -> dict:
    manifest_fields.update(trials=trials, summary=summarize_sweep(trials, tuple(plan["agents"])),
                           findings=findings_for(run_id, trials), status="complete")
    return manifest_fields


def run_o2b(repo: Path, evidence: Path, batch: str, build_name: str, build: dict, storage: str, *,
            command: str, smoke: bool = False, gate_ms: float | None = None, seed: int = 0,
            endpoint: str = "http://127.0.0.1:18080",
            actor_tokens: list[tuple[str, str]] | None = None) -> tuple[dict, Path]:
    """actor_tokens: (actor, token) pairs, the admin first, then agent i at index i + 1 (actors.py)."""
    started = _utc()
    run_id = _run_id(started)
    project = f"wm-m5-o2b-{build_name.replace('.', '-')}-{storage}".lower()
    plan = sweep_plan(smoke)
    extra = {"sweep": plan, "spread_gate": spread_gate(gate_ms), "smoke": smoke, "seed": seed,
             "interpretation": INTERPRETATION, "invariants_note": "I1A is a sanity check here, not the purpose",
             "expected": {"omnigraph": "[unmeasured]; hypothesis [inference from O-K3]: wasted attempts grow with N"},
             "actors": describe_actors(actor_tokens)}
    planned = _manifest(repo, batch, build, build_name, storage, OMNIGRAPH_ID, OMNIGRAPH_MODE, started, [],
                        run_id=run_id, invariants=["I1A"], status="planned-before-execution", **extra)
    capture = RunCapture(repo, evidence, planned, command)
    stack = Stack(repo, project, build, storage, capture=capture, actor_tokens=actor_tokens)
    tokens = [token for _, token in actor_tokens] if actor_tokens else []
    queries = load_queries()
    rng = random.Random(seed)
    trials: list[dict] = []
    expected_pre: dict[int, str] = {}
    hung = False
    try:
        stack.provision()
        admin = capture.client(endpoint, timeout=180, label="admin", bearer_token=tokens[0] if tokens else None)
        for k, (round_index, n, warmup) in enumerate(rounds(plan), 1):
            capture.trial(k, "setup")
            healthy_before = admin.health().ok
            _setup_omnigraph(admin, queries, n)
            before = digest(observe_omnigraph(admin, queries, n, holders=False))
            precondition_ok = expected_pre.setdefault(n, before) == before
            clients = [OmnigraphClient(endpoint, timeout=60, bearer_token=tokens[i + 1] if tokens else None)
                       for i in range(n)]
            runs, faults, hung = race_agents(
                n, lambda i: clients[i].health(),
                lambda i: omnigraph_agent(clients[i], queries, i, cap=MAX_ATTEMPTS), rng=rng)
            capture.trial(k, "race")
            emit_runs(capture, runs)
            capture.trial(k, "observe")
            healthy_after = admin.health().ok
            observed = observe_omnigraph(admin, queries, n, holders=True)
            trial = evaluate_trial(k, n, round_index, warmup, runs, faults=faults, hung=hung,
                                   healthy_before=healthy_before, healthy_after=healthy_after,
                                   precondition_ok=precondition_ok, observed=observed, gate_ms=gate_ms)
            capture.final_state(trial, observed)
            trials.append(trial)
            if hung:
                break  # a hung client may still be writing; later trials would not be independent
        fields = _finish_sweep({}, trials, plan, run_id)
        if hung:
            fields["status"] = "incomplete"
        manifest = _manifest(repo, batch, build, build_name, storage, OMNIGRAPH_ID, OMNIGRAPH_MODE, started,
                             trials, run_id=run_id, invariants=["I1A"], cluster_lease_seconds=stack.lease_seconds,
                             **{**extra, **{key: value for key, value in fields.items() if key != "trials"}})
        capture.write_manifest(manifest)
        return manifest, capture.path
    except Exception as exc:
        _error_note(capture.path, repo, exc)
        raise
    finally:
        capture.close()
        stack.down()


# ---------------------------------------------------------------- the FalkorDB side

def _falkor_admin(capture: OperationCapture, session, kind: str, query: str, params: dict, *, write: bool):
    inv = stamp()
    try:
        reply = session.run(query, params, write=write)
    except EngineError as exc:
        capture.record("admin", kind, {"query": query, "params": params}, inv, stamp(), FAIL, error=exc.to_json())
        raise
    except EngineUnavailable as exc:
        capture.record("admin", kind, {"query": query, "params": params}, inv, None, UNKNOWN, error=exc.to_json())
        raise
    capture.record("admin", kind, {"query": query, "params": params}, inv, stamp(), OK,
                   result={"rows": len(reply.rows)})
    return reply


FALKOR_SETUP = "UNWIND range(0, $n - 1) AS i CREATE (:WMTask {id: 'task-' + toString(i), state: 'open', holder: ''})"
FALKOR_OBSERVE = "MATCH (t:WMTask) RETURN t.id AS id, t.state AS state, t.holder AS holder ORDER BY id"


def observe_falkordb(capture: OperationCapture, session, n: int) -> dict:
    reply = _falkor_admin(capture, session, "observe", FALKOR_OBSERVE, {}, write=False)
    rows = {row[0]: row for row in reply.rows}
    tasks = []
    for i in range(n):
        row = rows.get(task_name(i))
        holder = row[2] if row else None
        tasks.append({"task": task_name(i), "state": row[1] if row else None,
                      "holders": [holder] if holder else []})
    for name in sorted(set(rows) - {task_name(i) for i in range(n)}):
        tasks.append({"task": name, "state": rows[name][1], "holders": [rows[name][2]] if rows[name][2] else []})
    return {"tasks": tasks}


def run_o2b_falkordb(repo: Path, evidence: Path, batch: str, *, command: str, smoke: bool = False,
                     gate_ms: float | None = None, seed: int = 0, host: str = "127.0.0.1",
                     port: int = 16380) -> tuple[dict, Path]:
    started = utc_now()
    plan = sweep_plan(smoke)
    engine = make_engine("falkordb", host=host, port=port)
    component = engine.describe()
    header = {
        "harness": witnessmark_env.harness_info(repo),
        "target": {"name": engine.name, "repo": engine.repo, "ref": component.get("version", "unknown"),
                   **({"digest": component["digest"]} if component.get("digest") else {})},
        "components": [component],
        "host": witnessmark_env.host_info(),
        "scenario": {"id": FALKOR_ID, "invariants": ["I1A"], "mode": "sweep",
                     "params": {"claim": ClaimState.shapes["naive"], "agents": plan["agents"]}},
        "seed": seed,
        "started_at": iso(started),
    }
    run_id = make_run_id(started, header)
    run_dir = RunDir(evidence, "falkordb", FALKOR_ID, run_id)
    history: list = []
    capture = OperationCapture(repo, run_id, history.append)
    extra = {"sweep": plan, "spread_gate": spread_gate(gate_ms), "smoke": smoke, "interpretation": INTERPRETATION,
             "expected": {"falkordb": "every claim succeeds on its first attempt, serialised [ours: GNOMON S3]"}}
    rng = random.Random(seed)
    trials: list[dict] = []
    expected_pre: dict[int, str] = {}
    admin = engine.session(300)
    sessions: list = []
    hung = False
    try:
        for k, (round_index, n, warmup) in enumerate(rounds(plan), 1):
            capture.trial(k, "setup")
            healthy_before = engine.health().get("ok", False)
            engine.reset(admin)
            _falkor_admin(capture, admin, "fixture", FALKOR_SETUP, {"n": n}, write=True)
            before = digest(observe_falkordb(capture, admin, n))
            precondition_ok = expected_pre.setdefault(n, before) == before
            sessions = [engine.session(60) for _ in range(n)]
            runs, faults, hung = race_agents(n, lambda i: sessions[i].ping(),
                                             lambda i: falkordb_agent(sessions[i], i, cap=MAX_ATTEMPTS), rng=rng)
            capture.trial(k, "race")
            emit_runs(capture, runs)
            capture.trial(k, "observe")
            for session in sessions:
                session.close()
            sessions = []
            healthy_after = engine.health().get("ok", False)
            observed = observe_falkordb(capture, admin, n)
            trial = evaluate_trial(k, n, round_index, warmup, runs, faults=faults, hung=hung,
                                   healthy_before=healthy_before, healthy_after=healthy_after,
                                   precondition_ok=precondition_ok, observed=observed, gate_ms=gate_ms)
            trial["state_file"] = run_dir.write_state(k, observed)
            trials.append(trial)
            if hung:
                break
        fields = _finish_sweep({}, trials, plan, run_id)
        if hung:
            fields["status"] = "incomplete"
        manifest = {"schema_version": 1, "run_id": run_id, "batch": batch, **header, **extra,
                    "finished_at": iso(utc_now()), **fields}
        run_dir.write_history(history)
        run_dir.write_manifest(manifest)
        run_dir.write_repro(falkordb_repro(run_id, command, header, component))
        return manifest, run_dir.path
    except Exception as exc:
        run_dir.write_history(history)
        _error_note(run_dir.path, repo, exc)
        raise
    finally:
        for session in sessions:
            session.close()
        admin.close()


def falkordb_repro(run_id: str, command: str, header: dict, component: dict) -> str:
    harness = header["harness"]
    return (f"# Reproduce run {run_id}\n\n"
            "Start the pinned baseline, then run the same configuration from the repository root:\n\n"
            f"```bash\ndocker compose -f baselines/docker-compose.yml up -d falkordb\n{command}\n```\n\n"
            f"- Harness commit: `{harness['commit']}` (dirty: {str(harness['dirty']).lower()})\n"
            f"- Engine: {component.get('name')} {component.get('version')}\n"
            f"- Image: `{component.get('image', 'unknown')}`\n"
            f"- Digest: `{component.get('digest', 'unknown')}`\n")


def print_table(manifest: dict) -> None:
    print(f"{'N':>3} {'valid':>5} {'attempts':>9} {'wasted':>7} {'agent med':>9} {'agent max':>9} "
          f"{'all claimed ms':>14} {'claim p50':>9} {'claim p99':>9}")
    for row in manifest["summary"]:
        def med(name):
            value = row[name]["median"]
            return "-" if value is None else f"{value:.1f}"
        print(f"{row['n']:>3} {row['valid_repetitions']:>2}/{row['measured_repetitions']:<2} "
              f"{med('attempts_total'):>9} {med('wasted_attempts'):>7} {med('agent_attempts_median'):>9} "
              f"{med('agent_attempts_max'):>9} {med('time_to_all_claimed_ms'):>14} "
              f"{med('claim_latency_p50_ms'):>9} {med('claim_latency_p99_ms'):>9}")
