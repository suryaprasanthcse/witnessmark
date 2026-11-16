"""G7: persistence across restarts (target blueprint section 5, G7; K11, K12, K26).

Each trial starts the variant's FalkorDB container on an empty volume, ingests K episodes through Graphiti,
dumps, applies the cell's container action, and dumps again. The control (k = 0) does everything but the action.
"""

from __future__ import annotations

import asyncio
import json

from witnessmark import SCHEMA_VERSION
from witnessmark.checkers import Check
from witnessmark.evidence import digest, make_run_id
from witnessmark.history import FAIL, OK, UNKNOWN, Op
from witnessmark.memory import MemoryRunConfig, _finish, _header, _ingest, _note_crash, _run_dir, _stub_ops, \
    _verdicts, stub_errors
from witnessmark.timing import stamp, utc_now

from .fixtures import G7_EPISODES
from .measure import lost_items
from .nemesis import (G7_APPENDONLY, G7_COMPOSE, G7_PROJECT, G7_VARIANTS, Nemesis, g7_action_steps, g7_fresh_steps,
                      run_command)
from .observe import FalkorProbe, wait_answers

GROUP = "wm_g7"
ACTIONS = ("compose_restart", "down_up", "kill_start")
ISSUE_2117 = "https://github.com/getzep/graphiti/issues/2117"


def mounts(container: str) -> list[dict]:
    code, output = run_command(["docker", "inspect", "--format", "{{json .Mounts}}", container], 30)
    if code != 0:
        return []
    try:
        return [{"type": m.get("Type"), "name": m.get("Name"), "destination": m.get("Destination")}
                for m in json.loads(output)]
    except ValueError:
        return []


def g7_check(before: dict, after: dict, ops: list[Op]) -> tuple[Check, dict]:
    lost = lost_items(before, after)
    held = lost["lost_total"] == 0
    detail = (f"everything survived: {lost['after']}" if held else
              f"lost {lost['lost']} of {lost['before']}; examples {lost['examples']}")
    witnesses = [op.op_id for op in ops if op.client == "nemesis"] if not held else []
    return Check("I2", held, lost["lost_total"], "items lost", detail, witnesses), lost


async def run_persistence(config: MemoryRunConfig, variant: str, action: str, ready_timeout_s: float = 120.0,
                          appendonly: bool = False) -> dict:
    """``appendonly``: the explanatory control (maintainer ruling 4): the same layouts with appendonly yes and
    appendfsync everysec, from compose-g7-appendonly.yml layered over compose-g7.yml."""
    if variant not in G7_VARIANTS or action not in ACTIONS:
        raise ValueError("unknown G7 variant or action")
    v = G7_VARIANTS[variant]
    files = (G7_COMPOSE, G7_APPENDONLY) if appendonly else (G7_COMPOSE,)
    started = utc_now()
    scenario_id = f"g7.{variant}.{action}{'.appendonly' if appendonly else ''}.persistence"
    first = config.spec.build()
    params = {"support": "none", "variant": variant, "action": action, "episodes": G7_EPISODES, "group": GROUP,
              "compose_file": G7_COMPOSE, "compose_files": list(files),
              "redis_args": "--appendonly yes --appendfsync everysec" if appendonly else None,
              "project": G7_PROJECT, "service": v["service"], "container": v["container"],
              "port": v["port"], "volume": f"{G7_PROJECT}_{v['volume']}", "volume_mount": v["mount"],
              "steps": [{"kind": kind, "command": " ".join(args)}
                        for kind, args, _ in g7_action_steps(action, variant, files)],
              "op_timeout_s": config.op_timeout_s}
    header = _header(config, first, scenario_id, ("I2",), "persistence", 1, config.trials, started, params)
    run_id = make_run_id(started, header)
    run_dir = _run_dir(config, scenario_id, run_id)
    nemesis = Nemesis(run_id)
    probe = FalkorProbe(first.host, v["port"])
    history: list[Op] = []
    trials: list[dict] = []
    control_digest = None
    met, observed = False, "not run"
    try:
        for k in range(0, config.trials + 1):
            reasons: list[str] = []
            for kind, args, inputs in g7_fresh_steps(variant, files):
                nemesis.act(k, kind, args, phase="setup", client="compose", **inputs)
            setup = nemesis.drain()
            if any(op.outcome != OK for op in setup if op.kind != "delete_volume"):
                reasons.append("the container did not start fresh")
            answered = await wait_answers(probe, run_id, k, ready_timeout_s, f"{k}-harness-ping-before")
            if answered.outcome != OK:
                reasons.append("the server did not answer after the fresh start")
            settings_before = await probe.settings() if answered.outcome == OK else None
            target = config.spec.build()
            await target.open()
            phase = "control" if k == 0 else "race"
            ingests: list[Op] = []
            try:
                await target.reset(GROUP)
                target.drain_stub_calls()
                ingests = [await _ingest(target, run_id, k, phase, f"c{n:02d}", GROUP, {"tag": episode.tag},
                                         config.op_timeout_s)
                           for n, episode in enumerate(target.fixture.episodes)]
                await target.quiesce()
                before = await target.dump(GROUP)
                stub_ops = _stub_ops(target.drain_stub_calls(), run_id, k)
            finally:
                await target.close()
            if any(op.outcome != OK for op in ingests):
                reasons.append("an ingest did not succeed")
            if stub_errors(stub_ops):
                reasons.append(f"the stub could not answer {len(stub_errors(stub_ops))} call(s)")
            action_ops: list[Op] = []
            if k > 0:
                for kind, args, inputs in g7_action_steps(action, variant, files):
                    nemesis.act(k, kind, args, **inputs)
                action_ops = nemesis.drain()
                if any(op.outcome != OK for op in action_ops):
                    reasons.append("a container action failed")
            answered_after = await wait_answers(probe, run_id, k, ready_timeout_s, f"{k}-harness-ping-after")
            if answered_after.outcome != OK:
                reasons.append("the server did not answer after the action")
            settings_after = await probe.settings() if answered_after.outcome == OK else None
            raw_after = await probe.items(GROUP, GROUP) if answered_after.outcome == OK else None
            reader = config.spec.build()
            await reader.open()
            try:
                after = await reader.dump(GROUP)
            finally:
                await reader.close()
            reader.drain_stub_calls()
            state_file = run_dir.write_state(k, {"before": before, "after": after})
            check, lost = g7_check(before, after, action_ops)
            pre_digest = digest(before)
            if k == 0:
                shape = (len(before["episodes"]), len(before["entities"]), len(before["facts"]))
                met = (not reasons and shape == (G7_EPISODES, 2, G7_EPISODES) and lost["lost_total"] == 0)
                observed = (f"{shape[0]} episodes, {shape[1]} entities, {shape[2]} facts before; "
                            f"{lost['lost_total']} lost on close and reopen" + (f"; {'; '.join(reasons)}" if reasons else ""))
                control_digest = pre_digest
            elif pre_digest != control_digest:
                reasons.append("the state before the action differs from the control's")
            history += setup + [answered] + ingests + stub_ops + action_ops + [answered_after]
            trial = {"k": k, "valid": not reasons, "precondition_digest": pre_digest, "release_spread_ms": 0.0,
                     "max_in_flight": 1, "outcomes": {o: sum(1 for op in ingests if op.outcome == o)
                                                      for o in (OK, FAIL, UNKNOWN)},
                     "quiesce_ms": 0.0, "final_state_digest": digest(after), "state_file": state_file,
                     "checks": [check.to_json()],
                     "g7": {"variant": variant, "action": action if k else None, "lost": lost,
                            "graph_after": (raw_after or {}).get("graph"), "settings_before": settings_before,
                            "settings_after": settings_after, "mounts": mounts(v["container"])}}
            if reasons:
                trial["invalid_reason"] = "; ".join(reasons)
            if k > 0:
                trials.append(trial)
            else:
                run_dir.write_state("control", trial["g7"])
        for kind, args, inputs in g7_fresh_steps(variant, files)[:2]:  # leave nothing running and no volume behind
            nemesis.act(config.trials, kind, args, phase="setup", client="compose", cleanup=True, **inputs)
        history += nemesis.drain()
        manifest = {
            "schema_version": SCHEMA_VERSION, "run_id": run_id, "batch": config.batch, **header,
            "expectation": {"role": "target", "support": "none", "basis": "issue", "basis_ref": ISSUE_2117,
                            "known_deviation": None},
            "controls": [{"kind": "sequential",
                          "configuration": f"{scenario_id}: fresh volume, {G7_EPISODES} ingests, no action",
                          "expected": f"{G7_EPISODES} episodes, 2 entities, {G7_EPISODES} facts; nothing lost on "
                                      "close and reopen", "observed": observed, "met": met}],
            "trials": trials,
            "verdicts": _verdicts(("I2",), trials, met, "none", "issue", ISSUE_2117),
        }
        return _finish(config, run_dir, manifest, history)
    except Exception:
        _note_crash(locals())
        raise
    finally:
        await probe.close()
