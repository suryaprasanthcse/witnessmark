"""Scripted episodes for the Graphiti scenarios (target blueprint section 5).

Dates are absolute, or relative to an anchor time that the parent process fixes
once per run and hands to every worker, so all processes see the same fixture.
Fact texts avoid future-tense words ("will", "plans to", ...): Graphiti rewrites
the dates of such facts (temporal_edge_utils.normalize_future_temporal_bounds),
and these cases are about the resolver, not that rewrite.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from collections import Counter
from functools import lru_cache

from witnessmark.fixtures import Entity, Episode, Fact, Fixture
from witnessmark.stubs import embed, tokens

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


#: G6's declared load (target blueprint section 5, G6): G6_EPISODES episodes of G6_FACTS facts each.
G6_EPISODES = 400
G6_FACTS = 5
#: The term every G6 fact contains; the raw fulltext probe counts the facts it matches.
G6_PROBE_TERM = "invoice"
#: G6c: one episode of G6C_FACTS facts per group, in G6C_GROUPS groups.
G6C_GROUPS = 8
G6C_FACTS = 5
G6C_PROBE_TERM = "voucher"


def g6_fact(episode: int, k: int) -> str:
    return f"Clerk{episode:04d} posted invoice INV{episode:04d}x{k:02d} to Ledger{episode:04d}"


def g6(episodes: int = G6_EPISODES, facts: int = G6_FACTS) -> Fixture:
    """A populated group: each episode links one clerk to one ledger through ``facts`` distinct postings.

    Every fact carries one token of its own (INV<episode>x<k>), so a search for that token has exactly one
    right answer, and the shared word "invoice", which the raw fulltext probe counts.
    """
    out = []
    for j in range(episodes):
        clerk, ledger = Entity(f"Clerk{j:04d}", f"clerk{j:04d}"), Entity(f"Ledger{j:04d}", f"ledger{j:04d}")
        out.append(Episode(
            tag=f"G6E{j:04d}", name=f"G6E{j:04d}", text=f"{clerk.name} posted {facts} invoices to {ledger.name}.",
            reference_time=iso(BASE + timedelta(minutes=j)), entities=(clerk, ledger),
            facts=tuple(Fact(clerk.name, ledger.name, "POSTED", g6_fact(j, k), valid_at=iso(BASE + timedelta(minutes=j)))
                        for k in range(facts)),
        ))
    return Fixture("g6", out)


#: The stub embedder's dimension (witnessmark_graphiti.stubs.StubEmbedder).
EMBED_DIM = 1024


@lru_cache(maxsize=None)
def _slot(token: str) -> tuple[int, bool]:
    """The bucket and sign the stub embedder hashes one word into."""
    vector = embed(token, EMBED_DIM)
    index = next(i for i, value in enumerate(vector) if value)
    return index, vector[index] > 0


def _unique_slot(token: str, slots: Counter) -> bool:
    """Both engines score cosine as (1 + cos) / 2 and Graphiti keeps scores above 0.6, so any other fact with a
    word in the same bucket and sign would come back too. A token alone in its slot has one right answer."""
    return slots[_slot(token)] == 1


def _slots(fixture: Fixture) -> Counter:
    words = {word for episode in fixture.episodes for fact in episode.facts for word in tokens(fact.fact)}
    return Counter(_slot(word) for word in words)


def g6_queries(episodes: int = G6_EPISODES, facts: int = G6_FACTS, count: int = 10) -> list[tuple[str, str]]:
    """(query, the one fact it must return). Query n starts at episode n * episodes / count and takes the first fact,
    in order, whose own token shares no embedding slot with another word of the load."""
    slots = _slots(g6(episodes, facts))
    step = max(1, episodes // count)
    chosen: list[tuple[int, int]] = []
    for n in range(count):
        found = next(((j, (n + i) % facts) for j in range(n * step, episodes) for i in range(facts)
                      if (j, (n + i) % facts) not in chosen and _unique_slot(f"inv{j:04d}x{(n + i) % facts:02d}", slots)),
                     None)
        if found is not None:
            chosen.append(found)
    return [(f"INV{j:04d}x{k:02d}", g6_fact(j, k)) for j, k in chosen]


def g6c_fact(group: int, k: int) -> str:
    return f"Auditor{group} cleared voucher VCH{group}x{k:02d} for Fund{group}"


def g6c_query(group: int, facts: int = G6C_FACTS) -> tuple[str, str]:
    """The group's first fact whose own token shares no embedding slot with another word of the group."""
    slots = _slots(Fixture("g6c-one", [g6c(group + 1, facts).episodes[group]]))
    k = next((k for k in range(facts) if _unique_slot(f"vch{group}x{k:02d}", slots)), 0)
    return f"VCH{group}x{k:02d}", g6c_fact(group, k)


def g6c(groups: int = G6C_GROUPS, facts: int = G6C_FACTS) -> Fixture:
    """One episode per group; each names its own two entities and ``facts`` facts."""
    out = []
    for g in range(groups):
        auditor, fund = Entity(f"Auditor{g}", f"auditor{g}"), Entity(f"Fund{g}", f"fund{g}")
        out.append(Episode(
            tag=f"G6C{g}", name=f"G6C{g}", text=f"{auditor.name} cleared {facts} vouchers for {fund.name}.",
            reference_time=iso(BASE + timedelta(hours=g)), entities=(auditor, fund),
            facts=tuple(Fact(auditor.name, fund.name, "CLEARED", g6c_fact(g, k), valid_at=iso(BASE + timedelta(hours=g)))
                        for k in range(facts)),
        ))
    return Fixture("g6c", out)


#: G7: episodes ingested before each container action.
G7_EPISODES = 10


def g7(episodes: int = G7_EPISODES) -> Fixture:
    """K episodes, each with one fact, all naming the same two entities."""
    grace, repo = Entity("Grace", "grace"), Entity("Repository", "repository")
    out = []
    for i in range(episodes):
        when = BASE + timedelta(hours=i)
        out.append(Episode(tag=f"G7E{i:02d}", name=f"G7E{i:02d}", text=f"Grace merged change {i:02d} into Repository.",
                           reference_time=iso(when), entities=(grace, repo),
                           facts=(Fact("Grace", "Repository", "MERGED", f"Grace merged change {i:02d}",
                                       valid_at=iso(when)),)))
    return Fixture("g7", out)


G8_SHARED_FACT = "Alice works at Acme"
G8_REMOVED_FACT = "Alice approved the Payments budget"
G8_ADDED_FACT = "Alice audited Payments"


def g8() -> Fixture:
    """G8S stays; G8E is removed while G8N, which shares G8E's entities, is added.

    G8E repeats G8S's fact (so that edge outlives the delete, carried by G8S), states one fact of its own (which
    the delete must remove), and is the only episode naming Payments before the race; G8N names Payments too.
    """
    alice, acme, payments = Entity("Alice", "alice"), Entity("Acme", "acme"), Entity("Payments", "payments")
    shared = Fact("Alice", "Acme", "WORKS_AT", G8_SHARED_FACT, valid_at="2025-01-01T00:00:00Z")
    return Fixture("g8", [
        Episode(tag="G8S", name="G8S", text="Alice works at Acme.", reference_time=iso(BASE),
                entities=(alice, acme), facts=(shared,)),
        Episode(tag="G8E", name="G8E", text="Alice from Acme approved the Payments budget.",
                reference_time=iso(BASE + timedelta(hours=1)), entities=(alice, acme, payments),
                facts=(shared, Fact("Alice", "Payments", "APPROVED", G8_REMOVED_FACT,
                                    valid_at=iso(BASE + timedelta(hours=1))))),
        Episode(tag="G8N", name="G8N", text="Alice audited Payments.", reference_time=iso(BASE + timedelta(hours=2)),
                entities=(alice, payments),
                facts=(Fact("Alice", "Payments", "AUDITED", G8_ADDED_FACT, valid_at=iso(BASE + timedelta(hours=2))),)),
    ])


def build(name: str, anchor: str) -> Fixture:
    if name == "g1":
        return g1()
    if name in ("g2", "g5"):
        return g2()
    if name == "g3":
        return g3(anchor)
    if name == "g4":
        return g4()
    if name == "g6":
        return g6()
    if name.startswith("g6@"):  # a smaller load for smoke runs; the batch uses the declared size
        return g6(int(name.split("@", 1)[1]))
    if name == "g6c":
        return g6c()
    if name == "g7":
        return g7()
    if name == "g8":
        return g8()
    raise ValueError(f"unknown fixture {name!r}")
