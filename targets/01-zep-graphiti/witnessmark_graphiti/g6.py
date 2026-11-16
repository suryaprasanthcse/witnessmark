"""G6: index readiness at startup (target blueprint section 5, G6; K9, K21-K24; master KD-F4 and section 13).

- run_startup("fresh")      G6a: drop every index, construct a new Graphiti and search at once.
- run_startup("populated")  G6b: restart the test container, construct a new Graphiti and search at once.
- run_many_groups()         G6c: eight add_episode calls into eight new FalkorDB graphs, released together.

Each trial searches again once every expected index is ready, and compares both answers with the control.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from witnessmark import SCHEMA_VERSION
from witnessmark.checkers import Check, check_present, check_unique_keys
from witnessmark.evidence import digest, make_run_id, redact
from witnessmark.history import FAIL, OK, UNKNOWN, Op
from witnessmark.memory import (SPREAD_GATE_MS, MemoryRunConfig, _finish, _header, _ingest, _note_crash,
                                _race_in_loop, _run_dir, _stub_ops, _verdicts, max_in_flight, release_spread_ms,
                                stub_errors)
from witnessmark.timing import stamp, utc_now

from .fixtures import G6_EPISODES, G6_FACTS, G6_PROBE_TERM, G6C_FACTS, G6C_GROUPS, G6C_PROBE_TERM, g6_queries, g6c_query
from .measure import classify, index_keys, leftover_transactions, state_before, suite_summary, uc_report
from .nemesis import Nemesis
from .observe import (BuildTracker, IndexMonitor, LoopWatch, build_measures, build_ops, items_digest, make_probe,
                      wait_answers, watch_ops, watch_summary)

GROUP = "wm_g6"
STARTUP_INVARIANTS = ("I4.at_once", "I4.ready", "I2")
ISSUE_1643 = "https://github.com/getzep/graphiti/issues/1643"
CROSS_GROUP_FIX = "https://github.com/getzep/graphiti/blob/v0.31.2/graphiti_core/graphiti.py#L1427-L1429"
CONTAINERS = {"falkordb": "wm-falkordb", "neo4j": "wm-neo4j"}


#: Per-operation timeout for a search (master blueprint section 6.6, tau_op).
SEARCH_TIMEOUT_S = 60.0


class SearchStalled(Exception):
    """A search gave no answer within its timeout; the trial stops there (it cannot finish its measurements)."""

    def __init__(self, answers: list[dict], ops: list[Op], timeout_s: float):
        super().__init__(f"a search did not return within {timeout_s:.0f} s")
        self.answers, self.ops = answers, ops


async def run_suite(target, queries: list[tuple[str, str]], group: str, run_id: str, k: int, phase: str,
                    label: str, timeout_s: float = SEARCH_TIMEOUT_S) -> tuple[list[dict], list[Op]]:
    """Graphiti searches, one after another: (answers, operation records). A search that raises is a definite
    failure of a read, recorded with its error; it is a measurement, not a harness fault. A search with no answer
    within ``timeout_s`` is recorded with an unknown outcome and raises SearchStalled."""
    answers, ops = [], []
    for n, (query, _fact) in enumerate(queries):
        record = {"group": group, "query": query, "pass": label}
        inv = stamp()
        try:
            facts = await asyncio.wait_for(target.search(query, group), timeout_s)
        except asyncio.TimeoutError:
            error = {"type": "unavailable.timeout", "message": f"no answer in {timeout_s:.0f} s"}
            ops.append(Op(run_id, k, phase, f"{k}-c00-{label}-{n:02d}", "c00", "search", record, inv, None, UNKNOWN,
                          None, error))
            answers.append({"query": query, "facts": None, "error": error, "inv_ns": inv.mono_ns})
            raise SearchStalled(answers, ops, timeout_s)
        except Exception as exc:  # noqa: BLE001
            error = {"type": f"target.{type(exc).__name__}", "message": redact(str(exc))[:500]}
            ops.append(Op(run_id, k, phase, f"{k}-c00-{label}-{n:02d}", "c00", "search", record, inv, stamp(), FAIL,
                          None, error))
            answers.append({"query": query, "facts": None, "error": error, "inv_ns": inv.mono_ns})
            continue
        ops.append(Op(run_id, k, phase, f"{k}-c00-{label}-{n:02d}", "c00", "search", record, inv, stamp(), OK,
                      {"facts": facts}))
        answers.append({"query": query, "facts": facts, "error": None, "inv_ns": inv.mono_ns})
    return answers, ops


async def wait_ready_rows(probe, graph, timeout_s: float) -> list[dict] | None:
    """The index rows once every listed index is ready (used before the expected set is known)."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    ready = {"falkordb": "OPERATIONAL", "neo4j": "ONLINE"}[probe.backend]
    field = "status" if probe.backend == "falkordb" else "state"
    while loop.time() < deadline:
        rows = await probe.index_rows(graph)
        if rows and all(str(row.get(field)).upper() == ready for row in rows):
            return rows
        await asyncio.sleep(0.05)
    return None


async def wait_no_indexes(probe, graph, timeout_s: float) -> bool:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    while loop.time() < deadline:
        try:
            if not await asyncio.wait_for(probe.index_rows(graph), 30):
                return True
        except asyncio.TimeoutError:
            return False
        await asyncio.sleep(0.05)
    return False


def _harness_op(run_id: str, k: int, phase: str, op_id: str, kind: str, inv, ok: bool, result=None, error=None,
                **inputs) -> Op:
    if ok:
        return Op(run_id, k, phase, op_id, "harness", kind, inputs, inv, stamp(), OK, result)
    return Op(run_id, k, phase, op_id, "harness", kind, inputs, inv, stamp(), FAIL, result,
              error or {"type": "harness.check", "message": f"{kind} did not complete"})


def _answer_check(invariant: str, summary: dict, label: str, ops: list[Op]) -> Check:
    bad = summary["different"] + summary["errors"]
    detail = (f"{label}: {summary['identical']} of {summary['queries']} identical, {summary['different']} silently "
              f"different, {summary['errors']} error(s)")
    if summary["error_types"]:
        detail += f" {summary['error_types']}"
    witnesses = [op.op_id for op in ops if op.kind == "search" and (op.outcome != OK)] if bad else []
    return Check(invariant, not bad, bad, "queries not identical", detail, witnesses[:10])


def _trial_record(k: int, reasons: list[str], pre_digest: str, ops: list[Op], state_digest: str, state_file: str,
                  checks: list[Check], extra: dict, spread: float = 0.0) -> dict:
    trial = {"k": k, "valid": not reasons, "precondition_digest": pre_digest, "release_spread_ms": spread,
             "max_in_flight": max_in_flight(ops) if ops else 0,
             "outcomes": {o: sum(1 for op in ops if op.outcome == o) for o in (OK, FAIL, UNKNOWN)},
             "quiesce_ms": 0.0, "final_state_digest": state_digest, "state_file": state_file,
             "checks": [check.to_json() for check in checks], **extra}
    if reasons:
        trial["invalid_reason"] = "; ".join(reasons)
    return trial


def _watch_checks(watch: dict) -> list[Check]:
    return [
        Check("TASK", watch["unretrieved"] == 0, watch["unretrieved"], "never-retrieved task exceptions",
              f"{watch['unretrieved']} task exception(s) never retrieved {watch['unretrieved_types']}"
              if watch["unretrieved"] else "no task exception went unretrieved"),
        Check("ERR", watch["log_errors"] == 0, watch["log_errors"], "error log records",
              f"{watch['log_errors']} log record(s) at ERROR, {watch['log_warnings']} at WARNING"),
    ]


class ProbeStalled(Exception):
    """A read on the harness's own connection gave no answer in time; the trial cannot be measured."""


async def _bounded(awaitable, what: str, timeout_s: float = SEARCH_TIMEOUT_S):
    try:
        return await asyncio.wait_for(awaitable, timeout_s)
    except asyncio.TimeoutError:
        raise ProbeStalled(f"the harness's {what} gave no answer within {timeout_s:.0f} s") from None


async def recover_server(probe, nemesis, container: str, target, run_id: str, k: int,
                         ready_timeout_s: float) -> tuple[list[Op], object]:
    """End what a stalled instance left on the server, so the next trial starts clean.

    Closing the stalled instance in this process did not end its server transactions (batch m5g-20261116T051149Z,
    row 11), so the harness ends them: Neo4j TERMINATE TRANSACTIONS for every open transaction but its own lookup,
    then checks that none is left. If that fails, it restarts the test container. Returns (records, the probe to use).
    """
    ops: list[Op] = []
    inv = stamp()
    try:
        ids = leftover_transactions(await _bounded(probe.open_transactions(), "transaction list", 30))
        ended = await _bounded(probe.terminate(ids), "TERMINATE TRANSACTIONS", 30) if ids else []
        left = leftover_transactions(await _bounded(probe.open_transactions(), "transaction list", 30))
        for _ in range(100):  # Neo4j ends a terminated transaction asynchronously: allow it up to 10 s
            if not left:
                break
            await asyncio.sleep(0.1)
            left = leftover_transactions(await _bounded(probe.open_transactions(), "transaction list", 30))
        ops.append(_harness_op(run_id, k, "setup", f"{k}-harness-terminate", "terminate_transactions", inv, not left,
                               {"terminated": [r["transactionId"] for r in ended], "left": left}, ids=ids))
    except Exception as exc:  # noqa: BLE001 - fall through to the restart
        left = ["unknown"]
        ops.append(_harness_op(run_id, k, "setup", f"{k}-harness-terminate", "terminate_transactions", inv, False,
                               None, {"type": f"harness.{type(exc).__name__}", "message": redact(str(exc))[:300]}))
    if left:
        await probe.close()
        nemesis.act(k, "restart", ["docker", "restart", container], container=container, reason="recovery after a stall")
        ops += nemesis.drain()
        probe = make_probe(target)
        ops.append(await wait_answers(probe, run_id, k, ready_timeout_s, f"{k}-harness-ping-recovery"))
    return ops, probe


async def _stalled_trial(target, monitor, monitor_task, tracker, watch, run_id: str, k: int, ops: list[Op],
                         trials: list[dict], stalled: SearchStalled, construct: Op, reasons: list[str],
                         probe, nemesis, container: str, ready_timeout_s: float) -> tuple[list[Op], object]:
    """Record a trial that a stalled search stopped, close the instance, and end what it left on the server so the
    next trial starts clean. Returns (the trial's history records, the probe to use)."""
    monitor.stop()
    await monitor_task
    try:
        await asyncio.wait_for(target.close(), SEARCH_TIMEOUT_S)
    except Exception:  # noqa: BLE001 - the stall is the observation; closing is best effort
        target.graphiti = None
    recovery, probe = await recover_server(probe, nemesis, container, target, run_id, k, ready_timeout_s)
    await watch.settle()
    builds = tracker.drain()
    loop_events, logs = watch.drain()
    stub_ops = _stub_ops(target.drain_stub_calls(), run_id, k)
    last = stalled.ops[-1]
    why = f"{stalled} (query {last.input['query']}, pass {last.input['pass']}); the trial stopped there"
    g6 = {"stalled": {"op_id": last.op_id, "query": last.input["query"], "pass": last.input["pass"],
                      "answered_before": len(stalled.answers) - 1},
          "builds": {"count": len(builds), "unfinished": sum(1 for b in builds if b["outcome"] == "running")},
          "watch": watch_summary(loop_events, logs), "monitor_samples": len(monitor.samples)}
    g6["recovery"] = [{"kind": op.kind, "outcome": op.outcome, "input": op.input} for op in recovery]
    trials.append(_trial_record(k, reasons + [why], "", [construct] + stalled.ops, "", "", [], {"g6": g6}))
    return (ops + monitor.ops(run_id, k) + build_ops(builds, run_id, k) + watch_ops(loop_events, logs, run_id, k)
            + stub_ops + recovery), probe


# --- G6a and G6b ----------------------------------------------------------------------------------------------


async def run_startup(config: MemoryRunConfig, variant: str, ready_timeout_s: float = 180.0,
                      interval_s: float = 0.002) -> dict:
    if variant not in ("fresh", "populated"):
        raise ValueError("variant must be fresh or populated")
    name = "g6a.fresh" if variant == "fresh" else "g6b.populated"
    tracker, watch = BuildTracker(), LoopWatch()
    tracker.install()
    watch.install(asyncio.get_running_loop())
    target = config.spec.build()
    backend = target.backend
    graph = GROUP if backend == "falkordb" else None
    build_db = GROUP if backend == "falkordb" else "neo4j"
    container = CONTAINERS[backend]
    probe = make_probe(target)
    episodes = len(target.fixture.episodes)
    facts_per = len(target.fixture.episodes[0].facts)
    await target.open()
    try:
        started = utc_now()
        queries = g6_queries(episodes, facts_per)
        scenario_id = f"{name}.startup"
        params = {
            "support": "none", "group": GROUP, "episodes": episodes, "facts_per_episode": facts_per,
            "facts": episodes * facts_per, "declared_size": episodes == G6_EPISODES and facts_per == G6_FACTS,
            "queries": [q for q, _ in queries], "probe_term": G6_PROBE_TERM,
            "monitor_interval_ms": interval_s * 1000, "ready_timeout_s": ready_timeout_s,
            "search_timeout_s": SEARCH_TIMEOUT_S,
            "action": "drop every index, then construct" if variant == "fresh" else f"docker restart {container}",
            "container": container, "op_timeout_s": config.op_timeout_s,
        }
        header = _header(config, target, scenario_id, STARTUP_INVARIANTS, "startup", 1, config.trials, started, params)
        run_id = make_run_id(started, header)
        run_dir = _run_dir(config, scenario_id, run_id)
        nemesis = Nemesis(run_id)
        history: list[Op] = []

        # --- k = 0: load, wait for every index, then the control answers ---------------------------------------
        await target.reset(GROUP)
        tracker.drain()
        watch.drain()
        load = [await _ingest(target, run_id, 0, "setup", f"load{n:03d}", GROUP, {"tag": episode.tag},
                              config.op_timeout_s) for n, episode in enumerate(target.fixture.episodes)]
        await target.quiesce()
        rows = await wait_ready_rows(probe, graph, ready_timeout_s)
        expected = index_keys(backend, rows or [])
        control_answers, control_ops = await run_suite(target, queries, GROUP, run_id, 0, "control", "control")
        control_probe = await probe.probe(graph, GROUP, G6_PROBE_TERM)
        control_items = await probe.items(graph, GROUP)
        control_digest = items_digest(control_items)
        state0 = await target.dump(GROUP)
        run_dir.write_state(0, {GROUP: state0})
        control = {a["query"]: a["facts"] or [] for a in control_answers}
        wrong = [q for q, fact in queries if control.get(q) != [fact]]
        stub0 = _stub_ops(target.drain_stub_calls(), run_id, 0)
        counts = (len(state0["entities"]), len(state0["facts"]), len(state0["episodes"]))
        want = (2 * episodes, episodes * facts_per, episodes)
        met = (all(op.outcome == OK for op in load) and rows is not None and counts == want and not wrong
               and control_probe == episodes * facts_per and not stub_errors(stub0))
        observed = (f"{sum(op.outcome == OK for op in load)} of {len(load)} ingests ok; {counts[0]} entities, "
                    f"{counts[1]} facts, {counts[2]} episodes; indexes ready: {rows is not None} "
                    f"({len(expected)} index keys); {len(queries) - len(wrong)} of {len(queries)} queries returned "
                    f"exactly their fact; probe {control_probe}")
        if stub_errors(stub0):
            observed += f"; the stub could not answer: {stub_errors(stub0)[:2]}"
        setup_ops: list[Op] = []
        settings = await probe.settings()
        if variant == "populated" and backend == "falkordb":
            inv = stamp()
            saved = await probe.save()
            setup_ops.append(_harness_op(run_id, 0, "setup", "0-harness-save", "save", inv, saved,
                                         {"saved": saved}, reason="appendonly no: persist the load before restarts"))
        builds0 = tracker.drain()
        loop0, logs0 = watch.drain()
        history += (load + control_ops + setup_ops + stub0 + build_ops(builds0, run_id, 0, "setup")
                    + watch_ops(loop0, logs0, run_id, 0))

        # --- trials -------------------------------------------------------------------------------------------
        trials = []
        for k in range(1, config.trials + 1):
            reasons: list[str] = []
            ops: list[Op] = []
            try:
                pre_items = await _bounded(probe.items(graph, GROUP), "data read before the trial")
            except ProbeStalled as stalled:
                recovery, probe = await recover_server(probe, nemesis, container, target, run_id, k, ready_timeout_s)
                history += recovery
                trials.append(_trial_record(k, [str(stalled)], "", [], "", "", [],
                                            {"g6": {"probe_stalled": str(stalled),
                                                    "recovery": [{"kind": op.kind, "outcome": op.outcome}
                                                                 for op in recovery]}}))
                continue
            pre_digest = items_digest(pre_items)
            if pre_digest != control_digest:
                reasons.append("the group's data before the trial differs from the control's")
            await target.close()
            for _ in (tracker.drain(), watch.drain(), target.drain_stub_calls()):
                pass
            if variant == "fresh":
                inv = stamp()
                try:
                    dropped = await _bounded(probe.drop_indexes(graph), "index drop")
                    gone = await wait_no_indexes(probe, graph, ready_timeout_s)
                except ProbeStalled:
                    dropped, gone = None, False
                ops.append(_harness_op(run_id, k, "setup", f"{k}-harness-drop", "drop_indexes", inv, gone,
                                       {"dropped": dropped}, graph=graph))
                if not gone:
                    reasons.append("the indexes were not all dropped in time")
            else:
                # The harness's own connection must not outlive the restart: a pooled connection the restart killed
                # would log a client error under the same logger names Graphiti's driver uses.
                await probe.close()
                nemesis.act(k, "restart", ["docker", "restart", container], container=container)
                probe = make_probe(target)
                ops += nemesis.drain()
                if ops[-1].outcome != OK:
                    reasons.append(f"docker restart {container} failed")
                answered = await wait_answers(probe, run_id, k, ready_timeout_s, f"{k}-harness-ping")
                ops.append(answered)
                if answered.outcome != OK:
                    reasons.append("the server did not answer after the restart")
            monitor = IndexMonitor(probe, [(graph, GROUP, expected, G6_PROBE_TERM)], interval_s)
            monitor_task = asyncio.create_task(monitor.run())
            await monitor.first_sample.wait()
            inv = stamp()
            target.graphiti = target.make_graphiti()
            construct = Op(run_id, k, "race", f"{k}-c00-construct", "c00", "construct",
                           {"backend": backend, "what": "a new Graphiti with a new driver"}, inv, stamp(), OK)
            try:
                at_once, at_once_ops = await run_suite(target, queries, GROUP, run_id, k, "race", "at_once")
                try:
                    await asyncio.wait_for(monitor.all_ready.wait(), ready_timeout_s)
                    ready_seen = True
                except asyncio.TimeoutError:
                    ready_seen = False
                    reasons.append(f"the expected indexes were not all ready within {ready_timeout_s} s")
                ready_answers, ready_ops = (await run_suite(target, queries, GROUP, run_id, k, "race", "ready")
                                            if ready_seen else ([], []))
            except SearchStalled as stalled:
                records, probe = await _stalled_trial(target, monitor, monitor_task, tracker, watch, run_id, k,
                                                      ops + [construct] + stalled.ops, trials, stalled, construct,
                                                      reasons, probe, nemesis, container, ready_timeout_s)
                history += records
                continue
            monitor.stop()
            await monitor_task
            await target.quiesce()
            await watch.settle()
            builds = tracker.drain()
            loop_events, logs = watch.drain()
            try:
                post_items = await _bounded(probe.items(graph, GROUP), "data read after the trial")
            except ProbeStalled as stalled:
                post_items = {"graph": None, "facts": [], "entities": [], "episodes": []}
                reasons.append(str(stalled))
            state = await target.dump(GROUP)
            state_file = run_dir.write_state(k, {GROUP: state})
            dump_builds = tracker.drain()

            first_query_ns = at_once[0]["inv_ns"] if at_once else None
            before = state_before(monitor.samples, first_query_ns, graph) if first_query_ns else None
            uc = uc_report(monitor.samples, build_measures(builds), graph, build_db)
            watched = watch_summary(loop_events, logs)
            s_at_once = suite_summary(at_once, control)
            s_ready = suite_summary(ready_answers, control) if ready_seen else None
            data_kept = items_digest(post_items) == control_digest
            checks = [_answer_check("I4.at_once", s_at_once, "at once", at_once_ops)]
            if s_ready is not None:
                checks.append(_answer_check("I4.ready", s_ready, "after every index was ready", ready_ops))
            checks.append(Check("I2", data_kept, 0 if data_kept else 1, "data changes",
                                "the group's facts, entities and episodes match the control" if data_kept else
                                f"the group's data changed: {len(post_items['facts'])} facts, "
                                f"{len(post_items['entities'])} entities, {len(post_items['episodes'])} episodes",
                                [] if data_kept else [construct.op_id]))
            checks += _watch_checks(watched)
            stub_ops = _stub_ops(target.drain_stub_calls(), run_id, k)
            if stub_errors(stub_ops):
                reasons.append(f"the stub could not answer {len(stub_errors(stub_ops))} call(s)")
            g6 = {
                "variant": variant,
                "at_once": s_at_once,
                "ready": s_ready,
                "first_query_index_state": (before or {}).get("summary") if before else None,
                "first_query_met_unready_index": None if before is None else not (before.get("summary") or {}).get("ready"),
                "first_query_offset_ms": round((first_query_ns - construct.inv.mono_ns) / 1e6, 3) if first_query_ns else None,
                "index_ready_after_ms": (round((next(s["inv_ns"] for s in monitor.samples if (s.get("summary") or {}).get("ready")) - monitor.samples[0]["inv_ns"]) / 1e6, 3)
                                         if ready_seen else None),
                "uc": uc,
                "builds": {"count": len(builds), "on_group": sum(1 for b in builds if b["database"] == build_db),
                           "failed": sum(1 for b in builds if b["outcome"] == "error"),
                           "cancelled": sum(1 for b in builds if b["outcome"] == "cancelled")},
                "watch": watched,
                "monitor_samples": len(monitor.samples),
            }
            ops += [construct] + at_once_ops + ready_ops
            history += (ops + monitor.ops(run_id, k) + build_ops(builds, run_id, k)
                        + build_ops(dump_builds, run_id, k, "observe", len(builds), during="dump")
                        + watch_ops(loop_events, logs, run_id, k) + stub_ops)
            trials.append(_trial_record(k, reasons, pre_digest, [construct] + at_once_ops + ready_ops,
                                        digest(state), state_file, checks, {"g6": g6}))

        valid = [t for t in trials if t["valid"]]
        met_unready = sum(1 for t in valid if t["g6"].get("first_query_met_unready_index"))
        manifest = {
            "schema_version": SCHEMA_VERSION, "run_id": run_id, "batch": config.batch, **header,
            "expectation": {"role": "target", "support": "none", "basis": "issue", "basis_ref": ISSUE_1643,
                            "known_deviation": "KD-F4" if backend == "falkordb" else None},
            "engine_settings": settings,
            "expected_indexes": sorted("/".join(key) for key in expected),
            "controls": [
                {"kind": "sequential", "configuration": f"{scenario_id}: load, every index ready, then the suite",
                 "expected": f"{episodes} ingests ok; {2 * episodes} entities, {episodes * facts_per} facts, "
                             f"{episodes} episodes; every query returns exactly its fact; probe "
                             f"{episodes * facts_per}",
                 "observed": observed, "met": met},
            ],
            "unready_at_first_query": {"trials": met_unready, "valid": len(valid)},
            "trials": trials,
            "verdicts": _verdicts(STARTUP_INVARIANTS, trials, met, "none", "issue", ISSUE_1643),
        }
        return _finish(config, run_dir, manifest, history)
    except Exception:
        _note_crash(locals())
        raise
    finally:
        await target.close()
        await probe.close()
        tracker.uninstall()
        watch.uninstall()


# --- G6c ------------------------------------------------------------------------------------------------------

G6C_INVARIANTS = ("I2", "I1B", "I4")


def g6c_groups() -> list[str]:
    return [f"wm_g6c_{g}" for g in range(G6C_GROUPS)]


def g6c_queries() -> dict[str, tuple[str, str]]:
    return {group: g6c_query(g) for g, group in enumerate(g6c_groups())}


def g6c_checks(fixture, ops: list[Op], states: dict[str, dict], answers: dict[str, dict],
               control: dict[str, list[str]]) -> list[Check]:
    checks = []
    for op in ops:
        group = op.input["group"]
        state = states[group]
        if op.outcome == OK:
            episode = fixture.episode(op.input["tag"])
            checks.append(check_present(sorted(f.fact for f in episode.facts), {f["fact"] for f in state["facts"]},
                                        f"facts in {group}"))
            answer = answers.get(group) or {"facts": None, "error": {"type": "missing"}}
            kind = classify(answer, control.get(group, []))
            checks.append(Check("I4", kind == "identical", int(kind != "identical"), "groups not identical",
                                f"{group}: answer {kind}" + (f" ({answer['error']['type']})" if answer.get("error") else ""),
                                [] if kind == "identical" else [op.op_id]))
        keys = {}
        for entity in state["entities"]:
            keys[entity["key"]] = keys.get(entity["key"], 0) + 1
        checks.append(check_unique_keys(keys, f"entities in {group}"))
    return checks


async def run_many_groups(config: MemoryRunConfig, ready_timeout_s: float = 120.0, interval_s: float = 0.005) -> dict:
    tracker, watch = BuildTracker(), LoopWatch()
    tracker.install()
    watch.install(asyncio.get_running_loop())
    target = config.spec.build()
    if target.backend != "falkordb":
        raise ValueError("G6c runs on FalkorDB only (Neo4j's clone returns the same driver, K23)")
    probe = make_probe(target)
    groups = g6c_groups()
    clients = [(group, {"tag": episode.tag}) for group, episode in zip(groups, target.fixture.episodes)]
    queries = g6c_queries()
    await target.open()
    try:
        started = utc_now()
        scenario_id = "g6c.many_groups.asyncio"
        params = {"support": "supported", "groups": groups, "facts_per_episode": G6C_FACTS,
                  "queries": {g: q for g, (q, _) in queries.items()}, "probe_term": G6C_PROBE_TERM,
                  "spread_gate_ms": SPREAD_GATE_MS["asyncio"], "op_timeout_s": config.op_timeout_s,
                  "monitor_interval_ms": interval_s * 1000, "ready_timeout_s": ready_timeout_s,
                  "reset": "GRAPH.DELETE of every group's graph, so no index exists"}
        header = _header(config, target, scenario_id, G6C_INVARIANTS, "asyncio", len(clients), config.trials,
                         started, params)
        run_id = make_run_id(started, header)
        run_dir = _run_dir(config, scenario_id, run_id)
        history: list[Op] = []

        async def fresh() -> dict:
            for group in groups:
                await target.drop_group(group)
            return {"graphs_present": sorted([g for g in groups if await probe.exists(g)])}

        async def observe(k: int, phase: str) -> tuple[dict, dict, dict, list[Op], dict | None]:
            rows = {}
            for group in groups:
                rows[group] = await wait_ready_rows(probe, group, ready_timeout_s)
            answers, answer_ops = {}, []
            for n, group in enumerate(groups):
                query, _ = queries[group]
                try:
                    got, got_ops = await run_suite(target, [queries[group]], group, run_id, k, phase, f"answer{n}")
                except SearchStalled as stalled:  # an unanswered search is an error answer for that group
                    got, got_ops = stalled.answers, stalled.ops
                answers[group] = got[0]
                answer_ops += got_ops
            probes = {group: await probe.probe(group, group, G6C_PROBE_TERM) for group in groups}
            states = {group: await target.dump(group) for group in groups}
            return rows, answers, states, answer_ops, probes

        # --- k = 0: the same ingests one at a time, from the same reset ------------------------------------
        pre0 = await fresh()
        tracker.drain()
        watch.drain()
        control_ops = [await _ingest(target, run_id, 0, "control", f"c{n:02d}", group, item, config.op_timeout_s)
                       for n, (group, item) in enumerate(clients)]
        await target.quiesce()
        rows0, answers0, states0, answer_ops0, probes0 = await observe(0, "control")
        expected = index_keys("falkordb", rows0[groups[0]] or [])
        run_dir.write_state(0, states0)
        control = {group: answers0[group]["facts"] or [] for group in groups}
        problems = []
        for group in groups:
            state = states0[group]
            shape = (len(state["entities"]), len(state["facts"]), len(state["episodes"]))
            if shape != (2, G6C_FACTS, 1) or control[group] != [queries[group][1]] or probes0[group] != G6C_FACTS \
                    or rows0[group] is None or index_keys("falkordb", rows0[group]) != expected:
                problems.append(f"{group}: {shape[0]} entities, {shape[1]} facts, {shape[2]} episodes, answer "
                                f"{control[group]}, probe {probes0[group]}")
        stub0 = _stub_ops(target.drain_stub_calls(), run_id, 0)
        met = not problems and all(op.outcome == OK for op in control_ops) and not stub_errors(stub0) \
            and not pre0["graphs_present"]
        observed = "; ".join(problems) or (f"each of {len(groups)} groups: 2 entities, {G6C_FACTS} facts, 1 episode, "
                                           "its fact found, every index ready")
        builds0 = tracker.drain()
        loop0, logs0 = watch.drain()
        history += control_ops + answer_ops0 + stub0 + build_ops(builds0, run_id, 0, "control") + \
            watch_ops(loop0, logs0, run_id, 0)
        pre_digest0 = digest(pre0)

        trials = []
        scenario = SimpleNamespace(clients=lambda: clients, groups=lambda: groups)
        for k in range(1, config.trials + 1):
            reasons: list[str] = []
            pre = await fresh()
            for _ in (tracker.drain(), watch.drain(), target.drain_stub_calls()):
                pass
            if digest(pre) != pre_digest0:
                reasons.append("the precondition digest did not match")
            monitor = IndexMonitor(probe, [(group, group, expected, None) for group in groups], interval_s)
            monitor_task = asyncio.create_task(monitor.run())
            await monitor.first_sample.wait()
            ops = await _race_in_loop(target, scenario, "asyncio", run_id, k, config.op_timeout_s,
                                      config.trial_timeout_s)
            try:
                await asyncio.wait_for(monitor.all_ready.wait(), ready_timeout_s)
            except asyncio.TimeoutError:
                reasons.append(f"not every group's indexes were ready within {ready_timeout_s} s")
            monitor.stop()
            await monitor_task
            await target.quiesce()
            await watch.settle()
            builds = tracker.drain()
            loop_events, logs = watch.drain()
            _rows, answers, states, answer_ops, probes = await observe(k, "observe")
            dump_builds = tracker.drain()
            state_file = run_dir.write_state(k, states)
            stub_ops = _stub_ops(target.drain_stub_calls(), run_id, k)
            watched = watch_summary(loop_events, logs)
            checks = g6c_checks(target.fixture, ops, states, answers, control) + _watch_checks(watched)
            unknown = sum(1 for op in ops if op.outcome == UNKNOWN)
            if ops and unknown > 0.05 * len(ops):
                reasons.append(f"{unknown} of {len(ops)} operations had an unknown outcome")
            if len(ops) != len(clients):
                reasons.append(f"{len(clients) - len(ops)} client(s) recorded no operation")
            spread = release_spread_ms(ops, "asyncio")
            if spread > SPREAD_GATE_MS["asyncio"]:
                reasons.append(f"release spread {spread} ms exceeds the asyncio gate {SPREAD_GATE_MS['asyncio']} ms")
            if stub_errors(stub_ops):
                reasons.append(f"the stub could not answer {len(stub_errors(stub_ops))} call(s)")
            measures = build_measures(builds)
            per_graph = {group: uc_report(monitor.samples, measures, group, group) for group in groups}
            g6 = {
                "variant": "many_groups",
                "uc": per_graph,
                "builds": {"count": len(builds), "on_groups": sum(1 for b in builds if b["database"] in groups),
                           "failed": sum(1 for b in builds if b["outcome"] == "error"),
                           "cancelled": sum(1 for b in builds if b["outcome"] == "cancelled")},
                "watch": watched,
                "probe_rows": probes,
                "unknown_errors": sorted({op.error["type"] for op in ops if op.outcome == UNKNOWN and op.error}),
                "monitor_samples": len(monitor.samples),
            }
            history += (ops + answer_ops + monitor.ops(run_id, k) + build_ops(builds, run_id, k)
                        + build_ops(dump_builds, run_id, k, "observe", len(builds), during="dump")
                        + watch_ops(loop_events, logs, run_id, k) + stub_ops)
            trials.append(_trial_record(k, reasons, digest(pre), ops, digest(states), state_file, checks,
                                        {"g6": g6}, spread))

        valid = [t for t in trials if t["valid"]]
        raced = sum(1 for t in valid if t["max_in_flight"] >= 2)
        manifest = {
            "schema_version": SCHEMA_VERSION, "run_id": run_id, "batch": config.batch, **header,
            "expectation": {"role": "target", "support": "supported", "basis": "documented",
                            "basis_ref": CROSS_GROUP_FIX, "known_deviation": None},
            "expected_indexes": sorted("/".join(key) for key in expected),
            "controls": [
                {"kind": "sequential", "configuration": f"{scenario_id}: {len(clients)} ingests, one at a time, "
                                                        "into new graphs",
                 "expected": f"each group: 2 entities, {G6C_FACTS} facts, 1 episode; its fact found; every index "
                             "ready", "observed": observed, "met": met},
                {"kind": "overlap", "configuration": f"{scenario_id}: {len(clients)} clients x {len(trials)} trials",
                 "expected": "two or more ingests in flight at once in every valid trial",
                 "observed": f"{raced} of {len(valid)} valid trials had two or more in flight",
                 "met": bool(valid) and raced == len(valid)},
            ],
            "trials": trials,
            "verdicts": _verdicts(G6C_INVARIANTS, trials, met, "supported", "documented", CROSS_GROUP_FIX,
                                  raced_all=bool(valid) and raced == len(valid)),
        }
        return _finish(config, run_dir, manifest, history)
    except Exception:
        _note_crash(locals())
        raise
    finally:
        await target.close()
        await probe.close()
        tracker.uninstall()
        watch.uninstall()
