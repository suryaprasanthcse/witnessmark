"""Scripted episodes for the Graphiti scenarios (target blueprint section 5).

Dates are absolute, or relative to an anchor time that the parent process fixes
once per run and hands to every worker, so all processes see the same fixture.
Fact texts avoid future-tense words ("will", "plans to", ...): Graphiti rewrites
the dates of such facts (temporal_edge_utils.normalize_future_temporal_bounds),
and these cases are about the resolver, not that rewrite.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from witnessmark.fixtures import Entity, Episode, Fact, Fixture

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)

ALICE, ACME, PAYMENTS = Entity("Alice", "alice"), Entity("Acme", "acme"), Entity("Payments", "payments")
SHARED_FACT = "Alice works at Acme"


def iso(moment: datetime) -> str:
    return moment.isoformat().replace("+00:00", "Z")


def g1() -> Fixture:
    """20 episodes naming the same three entities; each repeats one fact and adds one of its own."""
    episodes = []
    for i in range(20):
        when = BASE + timedelta(hours=i)
        episodes.append(Episode(
            tag=f"G1E{i:02d}", name=f"G1E{i:02d}", text=f"Alice from Acme reviewed payments change {i:02d}.",
            reference_time=iso(when), entities=(ALICE, ACME, PAYMENTS),
            facts=(
                Fact("Alice", "Acme", "WORKS_AT", SHARED_FACT, valid_at="2025-01-01T00:00:00Z",
                     key="alice.employer", value="acme"),
                Fact("Alice", "Payments", "REVIEWED", f"Alice reviewed payments change {i:02d}", valid_at=iso(when)),
            ),
        ))
    return Fixture("g1", episodes)


def g2() -> Fixture:
    """10 episodes, each giving Alice a new employer: one single-valued fact, ten values."""
    episodes = []
    for i in range(10):
        when = BASE + timedelta(days=30 * i)
        company = Entity(f"Company{i}", f"company{i}")
        episodes.append(Episode(
            tag=f"G2E{i:02d}", name=f"G2E{i:02d}", text=f"Alice joined Company{i}.", reference_time=iso(when),
            entities=(ALICE, company),
            facts=(Fact("Alice", f"Company{i}", "WORKS_AT", f"Alice works at Company{i}", valid_at=iso(when),
                        key="alice.employer", value=f"company{i}"),),
        ))
    return Fixture("g2", episodes)


def g3(anchor: str) -> Fixture:
    """Known-answer cases R1-R6 (target blueprint section 5, G3).

    R1-R4 follow the cases a community member (Adam13y) published in getzep/graphiti#2012;
    R5 is the repeated assignment of getzep/graphiti#1865; R6 is a plain supersession.
    """
    now = datetime.fromisoformat(anchor.replace("Z", "+00:00"))

    def day(offset: int) -> str:
        return iso(now + timedelta(days=offset))

    leave = Fact("Alice", "Acme", "ON_LEAVE_FROM", "Alice is on parental leave from Acme until next year",
                 valid_at=day(-10), invalid_at=day(365), key="alice.leave", value="on_leave")
    coffee = Fact("Alice", "Acme", "LIKES_COFFEE_AT", "Alice likes the coffee at Acme", valid_at=day(-100),
                  key="alice.coffee", value="likes")
    worked = Fact("Alice", "Acme", "WORKED_AT", "Alice worked at Acme until last month", valid_at=day(-400),
                  invalid_at=day(-45), key="alice.employment", value="past")
    bob, carol, project_x = Entity("Bob", "bob"), Entity("Carol", "carol"), Entity("Project X", "project_x")
    carol_x = Fact("Carol", "Project X", "LEADS", "Carol leads Project X", valid_at=day(16), key="project_x.lead",
                   value="carol")
    bob_x = Fact("Bob", "Project X", "LEADS", "Bob leads Project X", valid_at=day(-15), invalid_at=day(7),
                 key="project_x.lead", value="bob")
    project_y = Entity("Project Y", "project_y")
    bob_y_then = Fact("Bob", "Project Y", "LEADS", "Bob leads Project Y", valid_at=day(-100), invalid_at=day(-60),
                      key="project_y.lead", value="bob")
    bob_y_again = Fact("Bob", "Project Y", "LEADS", "Bob leads Project Y", valid_at=day(-10), key="project_y.lead",
                       value="bob")
    dana, erin, project_z = Entity("Dana", "dana"), Entity("Erin", "erin"), Entity("Project Z", "project_z")
    dana_z = Fact("Dana", "Project Z", "LEADS", "Dana leads Project Z", valid_at=day(-30), key="project_z.lead",
                  value="dana")
    erin_z = Fact("Erin", "Project Z", "LEADS", "Erin leads Project Z", valid_at=day(-5), key="project_z.lead",
                  value="erin")

    def episode(tag, text, entities, facts, offset=0):
        return Episode(tag=tag, name=tag, text=text, reference_time=day(offset), entities=entities, facts=facts)

    return Fixture("g3", [
        episode("G3R1C", "Alice is on parental leave from Acme until next year.", (ALICE, ACME), (leave,)),
        episode("G3R2S", "Alice likes the coffee at Acme.", (ALICE, ACME), (coffee,), -100),
        episode("G3R2C", "Alice is on parental leave from Acme until next year.", (ALICE, ACME), (leave,)),
        episode("G3R3S", "Alice likes the coffee at Acme.", (ALICE, ACME), (coffee,), -100),
        episode("G3R3C", "Alice worked at Acme until last month.", (ALICE, ACME), (worked,)),
        episode("G3R4S", "Carol leads Project X from next month.", (carol, project_x), (carol_x,), -1),
        episode("G3R4C", "Bob leads Project X until next week.", (bob, project_x), (bob_x,)),
        episode("G3R5S", "Bob led Project Y for forty days.", (bob, project_y), (bob_y_then,), -60),
        episode("G3R5C", "Bob leads Project Y again since last week.", (bob, project_y), (bob_y_again,)),
        episode("G3R6S", "Dana leads Project Z.", (dana, project_z), (dana_z,), -30),
        episode("G3R6C", "Erin took over Project Z from Dana.", (erin, project_z), (erin_z,), -5),
    ])


def g4() -> Fixture:
    """10 episodes, each with one fact a reader must find right after the write returns."""
    frank, deployments = Entity("Frank", "frank"), Entity("Deployments", "deployments")
    episodes = []
    for i in range(10):
        when = BASE + timedelta(hours=i)
        fact = f"Frank logged deployment {i:02d}"
        episodes.append(Episode(tag=f"G4E{i:02d}", name=f"G4E{i:02d}", text=f"Frank logged deployment {i:02d}.",
                                reference_time=iso(when), entities=(frank, deployments),
                                facts=(Fact("Frank", "Deployments", "LOGGED", fact, valid_at=iso(when)),)))
    return Fixture("g4", episodes)


def build(name: str, anchor: str) -> Fixture:
    if name == "g1":
        return g1()
    if name in ("g2", "g5"):
        return g2()
    if name == "g3":
        return g3(anchor)
    if name == "g4":
        return g4()
    raise ValueError(f"unknown fixture {name!r}")
