"""Engine-neutral race scenarios for the baselines (master blueprint sections 6 and 7).

Every shape is plain Cypher that FalkorDB and Neo4j both accept. Labels carry a
``WM`` prefix so harness data is easy to tell apart.
"""

from __future__ import annotations

from dataclasses import dataclass

from .adapters.base import Reply, Session
from .checkers import Check, check_claim_lease, check_claim_state, check_counter, check_disjoint
from .history import FAIL, OK, Op

NEO4J_LOCKING = "https://neo4j.com/docs/operations-manual/5/database-internals/concurrent-data-access/"
GNOMON_S3 = "https://github.com/suryaprasanthcse/gnomon/blob/acffec2/.agent/FACTS.md"


def client_name(i: int) -> str:
    return f"c{i:02d}"


class Scenario:
    id: str
    invariant: str
    kind: str
    shapes: dict[str, str]

    def setup(self, session: Session, n: int) -> None:
        raise NotImplementedError

    def payload(self, shape: str, i: int, n: int) -> tuple[str, dict, dict]:
        """(query, parameters, the input recorded in the history)."""
        raise NotImplementedError

    def classify(self, reply: Reply) -> tuple[str, dict]:
        raise NotImplementedError

    def observe(self, session: Session, n: int) -> dict:
        raise NotImplementedError

    def check(self, ops: list[Op], state: dict, n: int) -> Check:
        raise NotImplementedError

    def sequential_expected(self, ops: list[Op], state: dict, n: int) -> tuple[bool, str, str]:
        """For the sequential control: (met, expected, observed)."""
        raise NotImplementedError


class ClaimState(Scenario):
    """Agents race to claim one task by flipping its state."""

    id = "claim.state"
    invariant = "I1A"
    kind = "claim"
    TASK = 1
    shapes = {
        "naive": (
            "MATCH (t:WMTask {id: $task}) WHERE t.state = 'open' "
            "SET t.state = 'claimed', t.holder = $agent RETURN count(t) AS won"
        ),
        # Writing a dummy property first takes the node's write lock before the guard is read.
        "lock_first": (
            "MATCH (t:WMTask {id: $task}) SET t._wm_lock = true REMOVE t._wm_lock "
            "WITH t WHERE t.state = 'open' "
            "SET t.state = 'claimed', t.holder = $agent RETURN count(t) AS won"
        ),
    }

    def setup(self, session, n):
        session.run("CREATE (:WMTask {id: $task, state: 'open', holder: ''})", {"task": self.TASK})

    def payload(self, shape, i, n):
        params = {"task": self.TASK, "agent": client_name(i)}
        return self.shapes[shape], params, dict(params)

    def classify(self, reply):
        won = int(reply.scalar(0) or 0)
        return (OK if won == 1 else FAIL), {"won": won}

    def observe(self, session, n):
        reply = session.run(
            "MATCH (t:WMTask) RETURN t.id AS id, t.state AS state, t.holder AS holder ORDER BY id", {}, write=False
        )
        return {"tasks": [dict(zip(["id", "state", "holder"], row)) for row in reply.rows]}

    def check(self, ops, state, n):
        return check_claim_state(ops, state["tasks"][0] if state["tasks"] else {})

    def sequential_expected(self, ops, state, n):
        winners = [op.input["agent"] for op in ops if op.outcome == OK]
        task = state["tasks"][0] if state["tasks"] else {}
        met = winners == [client_name(0)] and task.get("state") == "claimed" and task.get("holder") == client_name(0)
        return met, f"only {client_name(0)} wins and holds the task", f"winners {winners}; holder {task.get('holder')!r}"


class ClaimLease(Scenario):
    """Agents race to create the one lease edge on a task (the shape of GNOMON's ClaimTask guard)."""

    id = "claim.lease"
    invariant = "I1A"
    kind = "claim"
    TASK = 1
    _GUARDED_CREATE = (
        "OPTIONAL MATCH (t)<-[l:WM_HOLDS]-(:WMAgent) "
        "WITH a, t, count(l) AS live WHERE live = 0 "
        "CREATE (a)-[:WM_HOLDS]->(t) RETURN count(*) AS won"
    )
    shapes = {
        "naive": "MATCH (a:WMAgent {id: $agent}), (t:WMTask {id: $task}) " + _GUARDED_CREATE,
        "lock_first": (
            "MATCH (t:WMTask {id: $task}) SET t._wm_lock = true REMOVE t._wm_lock "
            "WITH t MATCH (a:WMAgent {id: $agent}) " + _GUARDED_CREATE
        ),
    }

    def setup(self, session, n):
        session.run("CREATE (:WMTask {id: $task})", {"task": self.TASK})
        session.run("UNWIND $agents AS agent CREATE (:WMAgent {id: agent})",
                    {"agents": [client_name(i) for i in range(n)]})

    def payload(self, shape, i, n):
        params = {"task": self.TASK, "agent": client_name(i)}
        return self.shapes[shape], params, dict(params)

    def classify(self, reply):
        won = int(reply.scalar(0) or 0)
        return (OK if won == 1 else FAIL), {"won": won}

    def observe(self, session, n):
        reply = session.run(
            "MATCH (a:WMAgent)-[:WM_HOLDS]->(t:WMTask {id: $task}) RETURN a.id AS agent ORDER BY agent",
            {"task": self.TASK}, write=False,
        )
        return {"holders": [row[0] for row in reply.rows]}

    def check(self, ops, state, n):
        return check_claim_lease(ops, state["holders"])

    def sequential_expected(self, ops, state, n):
        winners = [op.input["agent"] for op in ops if op.outcome == OK]
        met = winners == [client_name(0)] and state["holders"] == [client_name(0)]
        return met, f"only {client_name(0)} wins and holds the lease", f"winners {winners}; holders {state['holders']}"


class Counter(Scenario):
    """Concurrent increments of one property."""

    id = "counter"
    invariant = "I2"
    kind = "incr"
    COUNTER = 1
    shapes = {
        # The right-hand side reads the property it writes, so Neo4j locks before reading.
        "direct": "MATCH (c:WMCounter {id: $counter}) SET c.v = c.v + 1 RETURN c.v AS v",
        # The value travels through WITH, so Neo4j takes no lock before reading.
        "via_with": "MATCH (c:WMCounter {id: $counter}) WITH c, c.v AS p SET c.v = p + 1 RETURN p + 1 AS v",
    }

    def setup(self, session, n):
        session.run("CREATE (:WMCounter {id: $counter, v: 0})", {"counter": self.COUNTER})

    def payload(self, shape, i, n):
        params = {"counter": self.COUNTER}
        return self.shapes[shape], params, dict(params)

    def classify(self, reply):
        return OK, {"v": int(reply.scalar(0))}

    def observe(self, session, n):
        reply = session.run("MATCH (c:WMCounter {id: $counter}) RETURN c.v AS v", {"counter": self.COUNTER},
                            write=False)
        return {"v": int(reply.scalar(0))}

    def check(self, ops, state, n):
        return check_counter(ops, state["v"])

    def sequential_expected(self, ops, state, n):
        acknowledged = sum(1 for op in ops if op.outcome == OK)
        met = acknowledged == n and state["v"] == n
        return met, f"{n} acknowledged increments and a final value of {n}", f"{acknowledged} acknowledged; value {state['v']}"


class Disjoint(Scenario):
    """Each client sets its own property on one shared node."""

    id = "disjoint"
    invariant = "I2"
    kind = "write"
    DOC = 1
    # <prop> is replaced by the client's own property name, p00 to pNN.
    shapes = {"set": "MATCH (d:WMDoc {id: $doc}) SET d.<prop> = $v RETURN 1 AS done"}

    @staticmethod
    def prop(i: int) -> str:
        return f"p{i:02d}"

    def setup(self, session, n):
        session.run("CREATE (:WMDoc {id: $doc})", {"doc": self.DOC})

    def payload(self, shape, i, n):
        params = {"doc": self.DOC, "v": i}
        query = self.shapes[shape].replace("<prop>", self.prop(i))
        return query, params, {"doc": self.DOC, "prop": self.prop(i), "v": i}

    def classify(self, reply):
        return OK, {"done": int(reply.scalar(0) or 0)}

    def observe(self, session, n):
        columns = ", ".join(f"d.{self.prop(i)} AS {self.prop(i)}" for i in range(n))
        reply = session.run(f"MATCH (d:WMDoc {{id: $doc}}) RETURN {columns}", {"doc": self.DOC}, write=False)
        values = reply.rows[0] if reply.rows else [None] * n
        return {"props": {self.prop(i): (int(values[i]) if values[i] is not None else None) for i in range(n)}}

    def check(self, ops, state, n):
        return check_disjoint(ops, state["props"])

    def sequential_expected(self, ops, state, n):
        present = sum(1 for value in state["props"].values() if value is not None)
        acknowledged = sum(1 for op in ops if op.outcome == OK)
        met = acknowledged == n and present == n
        return met, f"all {n} properties present", f"{acknowledged} acknowledged; {present} present"


SCENARIOS: dict[str, Scenario] = {scenario.id: scenario for scenario in (ClaimState(), ClaimLease(), Counter(), Disjoint())}


@dataclass(frozen=True)
class Expectation:
    """What a baseline configuration is expected to do, and on what basis (master blueprint section 7.1)."""

    role: str  # "negative": keeps the invariant; "positive": documented to violate it
    basis: str  # documented | standard | baseline | issue | inferred
    basis_ref: str
    known_deviation: str | None = None


EXPECTATIONS: dict[tuple[str, str], Expectation] = {
    ("falkordb", "claim.state.naive"): Expectation("negative", "baseline", GNOMON_S3),
    ("falkordb", "claim.lease.naive"): Expectation("negative", "baseline", GNOMON_S3),
    ("falkordb", "counter.direct"): Expectation("negative", "baseline", GNOMON_S3),
    ("falkordb", "counter.via_with"): Expectation("negative", "baseline", GNOMON_S3),
    ("falkordb", "disjoint.set"): Expectation("negative", "baseline", GNOMON_S3),
    ("neo4j", "claim.state.naive"): Expectation("positive", "documented", NEO4J_LOCKING, "KD-N1"),
    ("neo4j", "claim.state.lock_first"): Expectation("negative", "documented", NEO4J_LOCKING),
    ("neo4j", "claim.lease.naive"): Expectation("positive", "documented", NEO4J_LOCKING, "KD-N1"),
    ("neo4j", "claim.lease.lock_first"): Expectation("negative", "documented", NEO4J_LOCKING),
    ("neo4j", "counter.direct"): Expectation("negative", "documented", NEO4J_LOCKING),
    ("neo4j", "counter.via_with"): Expectation("positive", "documented", NEO4J_LOCKING, "KD-N1"),
    ("neo4j", "disjoint.set"): Expectation("negative", "inferred", NEO4J_LOCKING),
}

# The M1 control matrix: every configuration in EXPECTATIONS, in this order.
CALIBRATION = list(EXPECTATIONS)


def resolve(scenario_id: str, shape: str) -> Scenario:
    if scenario_id not in SCENARIOS:
        raise ValueError(f"unknown scenario {scenario_id!r}; known: {sorted(SCENARIOS)}")
    scenario = SCENARIOS[scenario_id]
    if shape not in scenario.shapes:
        raise ValueError(f"scenario {scenario_id} has no shape {shape!r}; known: {sorted(scenario.shapes)}")
    return scenario
