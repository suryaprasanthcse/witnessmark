"""Sequential controls and syntax smoke for the two pinned Omnigraph builds."""

from __future__ import annotations

from witnessmark.adapters import make_engine
from witnessmark.checkers import check_equivalent_rows

from .client import OperationResult, Outcome
from .engine import OmnigraphEngine, OmnigraphSession
from .runner_scenarios import SKILL, TASK


def _result(result: OperationResult) -> dict:
    return {"outcome": result.outcome.value, "status": result.status, "kind": result.kind,
            "data": result.data, "message": result.message}


def run_query_smoke(engine: OmnigraphEngine) -> dict:
    """Execute every declaration in queries.gq in a dependency-safe order."""
    session = engine.session()
    executed: list[str] = []

    def run(name: str, params: dict | None = None, *, write: bool = True):
        reply = session.run(name, params or {}, write=write)
        executed.append(name)
        return reply

    try:
        run("m_reset")
        run("m_fixture_base", {"task_id": TASK, "skill_id": SKILL})
        run("m_fixture_agent", {"agent_id": "c00", "skill_id": SKILL})
        run("m_fixture_task", {"task_id": "task-1", "skill_id": SKILL})
        task = run("q_task", {"task_id": TASK}, write=False)
        snapshot = task.token
        run("q_task_holder", {"task_id": TASK, "_snapshot": snapshot}, write=False)
        run("q_live", {"task_id": TASK}, write=False)
        eligible = run("q_eligible", {}, write=False)
        run("m_claim_cond", {"task_id": TASK, "agent_id": "c00", "from_seq": 1,
                             "until_pt": 9_223_372_036_854_775_807, "rw": "smoke-cond",
                             "_commit_id": snapshot})
        run("m_reset")
        run("m_fixture_base", {"task_id": TASK, "skill_id": SKILL})
        run("m_fixture_agent", {"agent_id": "c00", "skill_id": SKILL})
        run("m_claim_card", {"task_id": TASK, "agent_id": "c00", "from_seq": 3,
                             "until_pt": 9_223_372_036_854_775_807, "rw": "smoke-card"})
        run("m_ledger", {"id": "entry-1", "seq": 1, "rule": "smoke", "hash": "1",
                         "prev": "entry-0", "ts": 1})
        missing = sorted(set(engine.queries) - set(executed))
        return {"met": not missing, "executed": executed, "missing": missing,
                "eligible_rows": [dict(zip(eligible.columns, row)) for row in eligible.rows],
                "state": session.dump_task(TASK)}
    finally:
        session.close()


def run_o3_sequential(engine: OmnigraphEngine, clients: int = 50) -> dict:
    admin = engine.session()
    branches = [f"agent/c{i:02d}" for i in range(clients)]
    try:
        # A control may be repeated against the same disposable graph while we
        # diagnose a pin.  Remove only the exact fixture branches owned by this
        # control; branch creation below remains the authoritative check that
        # cleanup succeeded.
        for branch in branches:
            admin.client.branch_delete(branch)
        engine.reset(admin)
        admin.run("m_fixture_base", {"task_id": TASK, "skill_id": SKILL})
        for i in range(clients):
            admin.run("m_fixture_agent", {"agent_id": f"c{i:02d}", "skill_id": SKILL})
        creates = [admin.client.branch_create(branch, from_branch="main") for branch in branches]
        for result in creates:
            OmnigraphSession._raise(result)
        claims = []
        for i, branch in enumerate(branches):
            claims.append(admin.run("m_claim_card", {"task_id": TASK, "agent_id": f"c{i:02d}",
                                                      "from_seq": i + 1,
                                                      "until_pt": 9_223_372_036_854_775_807,
                                                      "rw": f"branch-lease-{i:02d}",
                                                      "_branch": branch}))
        merges = [admin.client.merge(branch, target="main") for branch in branches]
        kinds = [result.kind for result in merges[1:]]
        allowed = {"CardinalityViolation", "DivergentInsert", "DivergentUpdate", "DeleteVsUpdate"}
        state = admin.dump_task(TASK)
        met = (merges[0].outcome is Outcome.OK and
               all(result.outcome is Outcome.REFUSAL and result.kind in allowed for result in merges[1:]) and
               state["holders"].get(TASK) == ["c00"] and len(state["lease_records"]) == 1)
        return {"met": met, "branches": clients, "create_outcomes": [r.outcome.value for r in creates],
                "merge_outcomes": [r.outcome.value for r in merges], "merge_kinds": kinds, "state": state}
    finally:
        admin.close()


def _rows(reply) -> list[dict]:
    return [dict(zip(reply.columns, row)) for row in reply.rows]


def run_o6_sequential(engine: OmnigraphEngine, *, falkordb_port: int = 16380, neo4j_port: int = 17474) -> dict:
    agents = ["c00", "c01", "c02"]
    tasks = [TASK, "task-1"]
    omni = engine.session()
    baseline_rows: dict[str, dict[str, list[dict]]] = {}
    try:
        engine.reset(omni)
        omni.run("m_fixture_base", {"task_id": TASK, "skill_id": SKILL})
        omni.run("m_fixture_task", {"task_id": "task-1", "skill_id": SKILL})
        for agent in agents:
            omni.run("m_fixture_agent", {"agent_id": agent, "skill_id": SKILL})
        omni.run("m_claim_card", {"task_id": TASK, "agent_id": "c00", "from_seq": 1,
                                  "until_pt": 9_223_372_036_854_775_807, "rw": "parity-lease"})
        baseline_rows["omnigraph"] = {
            "q_eligible": _rows(omni.run("q_eligible", {}, write=False)),
            "q_live": _rows(omni.run("q_live", {"task_id": TASK}, write=False)),
        }
    finally:
        omni.close()

    eligible_cypher = ("MATCH (agent:Agent)-[:HasSkill]->(:Skill)<-[:Needs]-(task:Task) "
                       "RETURN DISTINCT agent.id AS agent, task.id AS task ORDER BY agent, task")
    live_cypher = ("MATCH (task:Task {id: $task_id}) OPTIONAL MATCH (task)-[:HeldBy]->(holder:Agent) "
                   "RETURN count(holder) AS live")
    for name, adapter in (("falkordb", make_engine("falkordb", host="127.0.0.1", port=falkordb_port)),
                          ("neo4j", make_engine("neo4j", host="127.0.0.1", port=neo4j_port))):
        session = adapter.session()
        try:
            session.run("MATCH (n) DETACH DELETE n", {})
            session.run("CREATE (:Skill {id: $skill})", {"skill": SKILL})
            session.run("UNWIND $agents AS id CREATE (:Agent {id: id})", {"agents": agents})
            session.run("UNWIND $tasks AS id CREATE (:Task {id: id, state: 'open'})", {"tasks": tasks})
            session.run("MATCH (a:Agent), (s:Skill) CREATE (a)-[:HasSkill]->(s)", {})
            session.run("MATCH (t:Task), (s:Skill) CREATE (t)-[:Needs]->(s)", {})
            session.run("MATCH (t:Task {id: $task}), (a:Agent {id: $agent}) "
                        "CREATE (t)-[:HeldBy]->(a)", {"task": TASK, "agent": "c00"})
            baseline_rows[name] = {
                "q_eligible": _rows(session.run(eligible_cypher, {}, write=False)),
                "q_live": _rows(session.run(live_cypher, {"task_id": TASK}, write=False)),
            }
        finally:
            session.close()

    eligible = check_equivalent_rows({name: rows["q_eligible"] for name, rows in baseline_rows.items()}, ordered=True)
    live = check_equivalent_rows({name: rows["q_live"] for name, rows in baseline_rows.items()})
    return {"met": eligible.held and live.held, "checks": [eligible.to_json(), live.to_json()],
            "rows": baseline_rows}
