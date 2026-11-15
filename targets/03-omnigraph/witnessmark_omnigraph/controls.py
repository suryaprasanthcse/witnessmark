"""Sequential controls and syntax smoke for the two pinned Omnigraph builds."""

from __future__ import annotations

from witnessmark.adapters import make_engine
from witnessmark.adapters.base import EngineError, EngineUnavailable
from witnessmark.checkers import check_equivalent_rows

from .client import OperationResult, Outcome
from .engine import OmnigraphEngine, OmnigraphSession
from .runner_scenarios import MERGE_REFUSALS, SKILL, TASK, merge_branches, prepare_merge_fixture


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
        run("m_o1_fixture", {"task_id": TASK, "skill_id": SKILL})
        run("q_ledger", {"rule": "absent"}, write=False)
        OmnigraphSession._raise(session.client.load_ndjson(
            b'{"type":"Entry","id":"raw-smoke","data":{"id":"raw-smoke","seq":1,'
            b'"rule":"smoke","hash":"1","prev":"","ts":1}}\n'))
        executed.append("load_ndjson")
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
    try:
        engine.reset(admin)
        creates = prepare_merge_fixture(admin, clients)
        merges = [admin.client.merge(branch, target="main") for branch in merge_branches(clients)]
        kinds = [result.kind for result in merges[1:]]
        state = admin.dump_task(TASK)
        met = (merges[0].outcome is Outcome.OK and
               all(result.outcome is Outcome.REFUSAL and result.kind in MERGE_REFUSALS for result in merges[1:]) and
               state["holders"].get(TASK) == ["c00"] and len(state["lease_records"]) == 1)
        return {"met": met, "branches": clients, "create_outcomes": [r.outcome.value for r in creates],
                "merge_outcomes": [r.outcome.value for r in merges], "merge_kinds": kinds, "state": state}
    finally:
        admin.close()


def _rows(reply) -> list[dict]:
    return [dict(zip(reply.columns, row)) for row in reply.rows]


def run_o6_sequential(engine: OmnigraphEngine, *, falkordb_port: int = 16380, neo4j_port: int = 17474,
                      execute=None, include_open: bool = False, components: list | None = None) -> dict:
    agents = ["c00", "c01", "c02"]
    tasks = [TASK, "task-1"]
    results: dict[str, dict[str, list[dict]]] = {}
    errors: dict[str, dict[str, dict]] = {}
    eligible_cypher = ("MATCH (agent:Agent)-[:HasSkill]->(:Skill)<-[:Needs]-(task:Task) "
                       "RETURN DISTINCT agent.id AS agent, task.id AS task ORDER BY agent, task")
    live_cypher = ("MATCH (task:Task {id: $task_id}) OPTIONAL MATCH (task)-[:HeldBy]->(holder:Agent) "
                   "RETURN count(holder) AS live")

    def call(name, session, query, params, *, write=True):
        if execute is not None:
            return execute(name, session, query, params, write=write)
        return session.run(query, params, write=write)

    def read(name, session, eligible, live):
        checks = [("q_eligible", eligible, {}), ("q_live", live, {"task_id": TASK})]
        if include_open:
            checks.append(("q_live_open", live, {"task_id": "task-1"}))
        results[name], errors[name] = {}, {}
        for key, query, params in checks:
            try:
                results[name][key] = _rows(call(name, session, query, params, write=False))
            except (EngineError, EngineUnavailable) as exc:
                if execute is None:
                    raise
                errors[name][key] = exc.to_json() | {"outcome": "rejected" if isinstance(exc, EngineError) else "unknown"}

    omni = engine.session()
    try:
        def setup(query, params):
            return call("omnigraph", omni, query, params)

        setup("m_reset", {})
        setup("m_fixture_base", {"task_id": TASK, "skill_id": SKILL})
        setup("m_fixture_task", {"task_id": "task-1", "skill_id": SKILL})
        for agent in agents:
            setup("m_fixture_agent", {"agent_id": agent, "skill_id": SKILL})
        setup("m_claim_card", {"task_id": TASK, "agent_id": "c00", "from_seq": 1,
                               "until_pt": 9_223_372_036_854_775_807, "rw": "parity-lease"})
        read("omnigraph", omni, "q_eligible", "q_live")
    finally:
        omni.close()

    for name, port in (("neo4j", neo4j_port), ("falkordb", falkordb_port)):
        adapter = make_engine(name, host="127.0.0.1", port=port)
        if components is not None:
            components.append(adapter.describe())
        session = adapter.session()
        try:
            def setup(query, params=None):
                return call(name, session, query, params or {})

            setup("MATCH (n) DETACH DELETE n")
            setup("CREATE (:Skill {id: $skill})", {"skill": SKILL})
            setup("UNWIND $agents AS id CREATE (:Agent {id: id})", {"agents": agents})
            setup("UNWIND $tasks AS id CREATE (:Task {id: id, state: 'open'})", {"tasks": tasks})
            setup("MATCH (a:Agent), (s:Skill) CREATE (a)-[:HasSkill]->(s)")
            setup("MATCH (t:Task), (s:Skill) CREATE (t)-[:Needs]->(s)")
            setup("MATCH (t:Task {id: $task}), (a:Agent {id: $agent}) "
                  "CREATE (t)-[:HeldBy]->(a)", {"task": TASK, "agent": "c00"})
            read(name, session, eligible_cypher, live_cypher)
        finally:
            session.close()

    comparison = _o6_compare(results, errors, include_open)
    if execute is None:
        return {key: comparison[key] for key in ("met", "checks", "rows")}
    return comparison


def _o6_compare(results: dict, errors: dict, include_open: bool) -> dict:
    references = ("neo4j", "falkordb")
    checks, classifications = [], {}
    for key in ("q_eligible", "q_live", "q_live_open") if include_open else ("q_eligible", "q_live"):
        if any(key in errors[name] for name in references):
            classifications[key] = "reference unavailable"
            continue
        refs = {name: results[name][key] for name in references}
        if not check_equivalent_rows(refs, ordered=key == "q_eligible").held:
            classifications[key] = "reference disagreement"
            continue
        if key in errors["omnigraph"]:
            classifications[key] = errors["omnigraph"][key]["outcome"]
            continue
        check = check_equivalent_rows({**refs, "omnigraph": results["omnigraph"][key]},
                                      ordered=key == "q_eligible")
        classifications[key] = "identical" if check.held else "silently different"
        checks.append(check.to_json())
    return {"met": all(value == "identical" for value in classifications.values()),
            "checks": checks, "rows": results, "errors": errors, "classifications": classifications}
