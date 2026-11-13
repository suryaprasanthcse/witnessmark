"""Graphiti scenarios G1 to G5 (target blueprint section 5).

What each scenario may expect comes from Graphiti's own words:

- add_episode's docstring asks callers to add episodes "sequentially and awaited"
  (graphiti.py L1410-1413 at v0.31.2), so concurrent ingest into one group is
  outside the documented contract: violations there are BOUNDARY, not FAIL;
- the request-scope fix for #1676 exists so that concurrent calls for different
  group_ids stay apart (graphiti.py L1427-1429), so that case is supported.
"""

from __future__ import annotations

from collections import Counter

from witnessmark.checkers import Check, check_no_overlapping_current, check_present, check_unique_keys
from witnessmark.fixtures import Fixture, normalize
from witnessmark.history import OK
from witnessmark.memory import Case, CaseSuite, RaceScenario, VisibilityScenario

from .fixtures import SHARED_FACT, build

AT = "https://github.com/getzep/graphiti/blob/v0.31.2/graphiti_core/graphiti.py"
SEQUENTIAL_DOC = f"{AT}#L1410-L1413"
CROSS_GROUP_FIX = f"{AT}#L1427-L1429"
ISSUE_2012 = "https://github.com/getzep/graphiti/issues/2012"
ISSUE_1865 = "https://github.com/getzep/graphiti/issues/1865"
SHARED_CONFIG = (f"{AT}#L1955-L1958 and "
                 "https://github.com/getzep/graphiti/blob/v0.31.2/graphiti_core/utils/maintenance/edge_operations.py#L532")


# --- G1: concurrent ingest, shared entities ------------------------------------------------------------------


def _g1_checks(fixture: Fixture, tags: list[str], state: dict, group: str) -> list[Check]:
    keys = Counter(entity["key"] for entity in state["entities"])
    mentions = {}
    for entity in state["entities"]:
        mentions.setdefault(entity["key"], []).extend(entity["mentioned_by"])
    shared = [fact for fact in state["facts"] if normalize(fact["fact"]) == normalize(SHARED_FACT)]
    expected_facts = sorted({fact.fact for tag in tags for fact in fixture.episode(tag).facts})
    present = {fact["fact"] for fact in state["facts"]}
    expected_keys = sorted({entity.key for tag in tags for entity in fixture.episode(tag).entities})
    return [
        check_unique_keys(dict(keys), f"entities in {group}", {k: sorted(v) for k, v in mentions.items()}),
        check_unique_keys({SHARED_FACT: len(shared)}, f"copies of the repeated fact in {group}"),
        check_present(expected_facts, present, f"facts in {group}"),
        check_present(expected_keys, set(keys), f"entities in {group}"),
    ]


class G1SameGroup(RaceScenario):
    """20 episodes into one group at once; every episode names the same three entities."""

    id = "g1.same_group"
    invariants = ("I1B", "I2")
    support = "boundary"
    basis = "documented"
    basis_ref = SEQUENTIAL_DOC
    GROUP = "wm_g1"

    def __init__(self, anchor: str):
        self.fixture = build("g1", anchor)

    def clients(self):
        return [(self.GROUP, {"tag": episode.tag}) for episode in self.fixture.episodes]

    def check(self, ops, states):
        tags = [op.input["tag"] for op in ops if op.outcome == OK]
        return _g1_checks(self.fixture, tags, states[self.GROUP], self.GROUP)

    def sequential_expected(self, ops, states):
        state = states[self.GROUP]
        keys = Counter(entity["key"] for entity in state["entities"])
        shared = [f for f in state["facts"] if normalize(f["fact"]) == normalize(SHARED_FACT)]
        met = (all(op.outcome == OK for op in ops) and dict(keys) == {"alice": 1, "acme": 1, "payments": 1}
               and len(state["facts"]) == 21 and len(shared) == 1 and shared[0]["episodes"] == 20
               and not any(f["expired"] for f in state["facts"]) and len(state["episodes"]) == 20)
        observed = f"entities {dict(keys)}; {len(state['facts'])} facts; repeated fact x{len(shared)}"
        if shared:
            observed += f" with {shared[0]['episodes']} episodes"
        observed += f"; {len(state['episodes'])} episodes"
        return (met, "3 entities (one per key), 21 facts (the repeated one once, with 20 episodes), 20 episodes, "
                     "nothing expired", observed)


class G1CrossGroup(RaceScenario):
    """Ten episodes at once, one per group: no group sees concurrency of its own, so any loss,
    duplicate or foreign episode comes from groups interfering with each other (#1676)."""

    id = "g1.cross_group"
    invariants = ("I1B", "I2")
    support = "supported"
    basis = "documented"
    basis_ref = CROSS_GROUP_FIX
    GROUPS = [f"wm_g1c_{n:02d}" for n in range(10)]

    def __init__(self, anchor: str):
        self.fixture = build("g1", anchor)

    def clients(self):
        return [(group, {"tag": episode.tag}) for group, episode in zip(self.GROUPS, self.fixture.episodes)]

    def _tags(self, ops, group):
        return [op.input["tag"] for op in ops if op.outcome == OK and op.input["group"] == group]

    def check(self, ops, states):
        checks = []
        for group in self.GROUPS:
            checks += _g1_checks(self.fixture, self._tags(ops, group), states[group], group)
            stray = sorted({e for e in states[group]["episodes"]} - set(self._tags(ops, group)))
            checks.append(Check("I2", not stray, len(stray), "episodes from other groups",
                                f"episodes from other groups in {group}: {stray}" if stray
                                else f"{group} holds only its own episodes", stray))
        return checks

    def sequential_expected(self, ops, states):
        problems = []
        for group in self.GROUPS:
            state = states[group]
            keys = Counter(entity["key"] for entity in state["entities"])
            if dict(keys) != {"alice": 1, "acme": 1, "payments": 1} or len(state["facts"]) != 2 or \
                    len(state["episodes"]) != 1:
                problems.append(f"{group}: entities {dict(keys)}, {len(state['facts'])} facts, "
                                f"{len(state['episodes'])} episodes")
        met = not problems and all(op.outcome == OK for op in ops)
        return met, "each of 10 groups: 3 entities, 2 facts, its own 1 episode", "; ".join(problems) or "as expected"


# --- G2: concurrent contradicting facts ----------------------------------------------------------------------


def _employer_versions(state: dict) -> list[dict]:
    return [{"label": fact["fact"], "valid_at": fact["valid_at"], "invalid_at": fact["invalid_at"],
             "current": not fact["expired"]} for fact in state["facts"] if fact["relation"] == "WORKS_AT"]


class G2Contradictions(RaceScenario):
    """10 episodes give Alice ten successive employers, all released at once."""

    id = "g2.contradictions"
    invariants = ("I7A",)
    support = "boundary"
    basis = "documented"
    basis_ref = SEQUENTIAL_DOC
    GROUP = "wm_g2"

    def __init__(self, anchor: str):
        self.fixture = build("g2", anchor)

    def clients(self):
        return [(self.GROUP, {"tag": episode.tag}) for episode in self.fixture.episodes]

    def check(self, ops, states):
        return [check_no_overlapping_current(_employer_versions(states[self.GROUP]), "Alice's employer")]

    def sequential_expected(self, ops, states):
        versions = _employer_versions(states[self.GROUP])
        current = [v["label"] for v in versions if v["current"]]
        chained = all(v["invalid_at"] for v in versions if not v["current"])
        met = len(versions) == 10 and current == ["Alice works at Company9"] and chained
        return (met, "10 versions; only 'Alice works at Company9' current; every other version closed",
                f"{len(versions)} versions; current: {current}")


# --- G3: known-answer temporal cases -------------------------------------------------------------------------

# Expected `expired` for each case's subject fact under three readings of expired_at:
# "issue": #2012's expectation (expired only once its end of validity has passed, or when superseded);
# "code": the v0.31.2 rule (any end of validity expires the edge at ingest, edge_operations.py L727-728);
# "standard": the bitemporal model (transaction time ends only on supersession, master blueprint I7b).
READINGS = {
    "R1": ("Alice is on parental leave from Acme until next year", {"issue": False, "code": True, "standard": False}),
    "R2": ("Alice is on parental leave from Acme until next year", {"issue": False, "code": True, "standard": False}),
    "R3": ("Alice worked at Acme until last month", {"issue": True, "code": True, "standard": False}),
    "R4": ("Bob leads Project X", {"issue": False, "code": True, "standard": False}),
}


class G3Temporal(CaseSuite):
    """R1-R6 through one entry point; each case in its own group."""

    invariants = ("I7.issue", "I7.code", "I7.standard", "I7C", "I2", "MR1")

    def __init__(self, anchor: str, entry: str):
        self.fixture = build("g3", anchor)
        self.entry = entry
        self.id = f"g3.temporal.{entry}"

    def cases(self):
        def item(tag):
            return {"tag": tag, "entry": self.entry}

        def case(name, setup, subject):
            return Case(name, f"wm_g3_{name.lower()}", tuple(item(tag) for tag in setup), item(subject))

        return [
            case("R1", [], "G3R1C"),
            case("R2", ["G3R2S"], "G3R2C"),
            case("R3", ["G3R3S"], "G3R3C"),
            case("R4", ["G3R4S"], "G3R4C"),
            case("R5", ["G3R5S"], "G3R5C"),
            case("R6", ["G3R6S"], "G3R6C"),
        ]

    @staticmethod
    def _facts(state: dict) -> list[dict]:
        # Wherever the facts landed: the group's graph, or (FalkorDB) the default graph.
        return state["facts"] + state.get("facts_in_default_graph", [])

    def check(self, case, ops, state):
        facts = self._facts(state)
        checks = []
        if state.get("facts_in_default_graph"):
            checks.append(Check("I2", False, len(state["facts_in_default_graph"]), "facts outside the group's graph",
                                f"{len(state['facts_in_default_graph'])} fact(s) for {case.group} were written to "
                                "the default graph, not the group's graph", [case.id]))
        if case.id in READINGS:
            text, expected = READINGS[case.id]
            subject = [fact for fact in facts if fact["fact"] == text]
            if not subject:
                checks.append(Check("I2", False, 1, "missing facts", f"{case.id}: '{text}' is missing", [case.id]))
                return checks
            observed = subject[-1]["expired"]
            for reading, want in expected.items():
                checks.append(Check(f"I7.{reading}", observed == want, int(observed != want), "mismatches",
                                    f"{case.id}: expired={observed}, the {reading} reading expects {want}",
                                    [] if observed == want else [case.id]))
            if case.id == "R4":
                episode = self.fixture.episode("G3R4C")
                end = episode.facts[0].invalid_at
                kept = subject[-1]["invalid_at"] == end
                checks.append(Check("I7C", kept, int(not kept), "extended intervals",
                                    f"R4: invalid_at {subject[-1]['invalid_at']} (fixture end {end})",
                                    [] if kept else [case.id]))
        if case.id == "R5":
            occurrences = [fact for fact in facts if fact["fact"] == "Bob leads Project Y"]
            again = self.fixture.episode("G3R5C").facts[0].valid_at
            kept = len(occurrences) == 2 and any(fact["valid_at"] == again for fact in occurrences)
            checks.append(Check("I2", kept, int(not kept), "lost occurrences",
                                f"R5: {len(occurrences)} edge(s) for 'Bob leads Project Y', valid_at "
                                f"{[fact['valid_at'] for fact in occurrences]}; the second occurrence starts {again}",
                                [] if kept else [case.id]))
        if case.id == "R6":
            dana = [fact for fact in facts if fact["fact"] == "Dana leads Project Z"]
            erin = [fact for fact in facts if fact["fact"] == "Erin leads Project Z"]
            erin_start = self.fixture.episode("G3R6C").facts[0].valid_at
            superseded = bool(dana) and dana[-1]["expired"] and dana[-1]["invalid_at"] == erin_start
            current = bool(erin) and not erin[-1]["expired"]
            for reading in ("issue", "code", "standard"):
                held = superseded and current
                checks.append(Check(f"I7.{reading}", held, int(not held), "mismatches",
                                    f"R6: Dana expired={dana[-1]['expired'] if dana else None}, "
                                    f"invalid_at={dana[-1]['invalid_at'] if dana else None}; "
                                    f"Erin expired={erin[-1]['expired'] if erin else None}",
                                    [] if held else [case.id]))
        return checks

    def suite_checks(self, states):
        r1 = [f["expired"] for f in self._facts(states.get("R1", {"facts": []}))
              if f["fact"] == READINGS["R1"][0]]
        r2 = [f["expired"] for f in self._facts(states.get("R2", {"facts": []}))
              if f["fact"] == READINGS["R2"][0]]
        held = bool(r1) and bool(r2) and r1[-1] == r2[-1]
        return [Check("MR1", held, int(not held), "disagreements",
                      f"R1 expired={r1[-1] if r1 else None}, R2 expired={r2[-1] if r2 else None}: an unrelated fact "
                      f"{'did not change' if held else 'changed'} the result", [] if held else ["R1", "R2"])]


# --- G4: read your writes --------------------------------------------------------------------------------------


class G4Visibility(VisibilityScenario):
    id = "g4.visibility"

    def __init__(self, anchor: str):
        self.fixture = build("g4", anchor)

    def group(self):
        return "wm_g4"

    def items(self):
        return [({"tag": episode.tag}, episode.facts[0].fact, episode.facts[0].fact)
                for episode in self.fixture.episodes]


# --- G5: a read changes later writes -----------------------------------------------------------------------------


class G5SharedSearchLimit(CaseSuite):
    """Graphiti.search sets .limit on the shared EDGE_HYBRID_SEARCH_RRF object, which add_episode's
    contradiction search also uses. Case "default" searches with the default limit first, case
    "limit1" with num_results=1; both then ingest the G2 chain one episode at a time."""

    id = "g5.shared_search_limit"
    invariants = ("I7A",)

    def __init__(self, anchor: str):
        self.fixture = build("g5", anchor)

    def cases(self):
        episodes = [{"tag": episode.tag} for episode in self.fixture.episodes]
        default = {"entry": "search", "query": "Alice works at", "num_results": 10}
        narrow = {"entry": "search", "query": "Alice works at", "num_results": 1}
        return [Case("default", "wm_g5_default", (default, *episodes[:-1]), episodes[-1]),
                Case("limit1", "wm_g5_limit1", (narrow, *episodes[:-1]), episodes[-1])]

    def check(self, case, ops, state):
        limit_after = (ops[0].result or {}).get("edge_search_limit_after")
        check = check_no_overlapping_current(_employer_versions(state), "Alice's employer")
        check.detail += f" (shared edge-search limit after the read: {limit_after})"
        return [check]
