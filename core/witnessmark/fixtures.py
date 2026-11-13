"""Scripted episodes for memory layers (master blueprint section 8).

A fixture lists episodes. Each episode names its entities and states its facts,
with the dates a perfect model would extract. Every episode body carries a tag,
``[wm:<tag>]``, so a stub can tell which episode a prompt is about.

Entities carry a canonical key: two names with one key are the same thing.
Facts may carry a functional key (a subject and predicate that hold one value
at a time) and a value; two facts with one key and different values contradict.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

TAG = re.compile(r"\[wm:([A-Za-z0-9_\-]+)\]")


def normalize(text: str) -> str:
    return " ".join(text.lower().split())


@dataclass(frozen=True)
class Entity:
    name: str
    key: str


@dataclass(frozen=True)
class Fact:
    source: str
    target: str
    relation: str
    fact: str
    valid_at: str | None = None
    invalid_at: str | None = None
    key: str = ""  # functional key; empty means the fact never contradicts another
    value: str = ""


@dataclass(frozen=True)
class Episode:
    tag: str
    name: str
    text: str
    reference_time: str
    entities: tuple[Entity, ...] = ()
    facts: tuple[Fact, ...] = ()
    entry: str = "add_episode"  # add_episode | add_episode_bulk | add_triplet

    @property
    def body(self) -> str:
        return f"{self.text} [wm:{self.tag}]"


@dataclass
class Fixture:
    name: str
    episodes: list[Episode] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._by_tag = {episode.tag: episode for episode in self.episodes}
        if len(self._by_tag) != len(self.episodes):
            raise ValueError(f"fixture {self.name} repeats an episode tag")
        self._entity_keys: dict[str, str] = {}
        self._facts: dict[str, Fact] = {}
        for episode in self.episodes:
            for entity in episode.entities:
                known = self._entity_keys.setdefault(normalize(entity.name), entity.key)
                if known != entity.key:
                    raise ValueError(f"entity {entity.name!r} has two keys: {known} and {entity.key}")
            for fact in episode.facts:
                self._facts.setdefault(normalize(fact.fact), fact)

    def episode(self, tag: str) -> Episode:
        return self._by_tag[tag]

    def episodes_in(self, text: str | None) -> list[Episode]:
        """The episodes whose tags appear in ``text``, in order of appearance."""
        found = []
        for tag in TAG.findall(text or ""):
            if tag in self._by_tag and self._by_tag[tag] not in found:
                found.append(self._by_tag[tag])
        return found

    def entity_key(self, name: str | None) -> str | None:
        return self._entity_keys.get(normalize(name or ""))

    def fact(self, text: str | None) -> Fact | None:
        return self._facts.get(normalize(text or ""))

    def same_assertion(self, a: Fact | None, b: Fact | None) -> bool:
        if a is None or b is None:
            return False
        if normalize(a.fact) == normalize(b.fact):
            return True
        return bool(a.key) and a.key == b.key and a.value == b.value

    def contradicts(self, a: Fact | None, b: Fact | None) -> bool:
        return a is not None and b is not None and bool(a.key) and a.key == b.key and a.value != b.value

    def to_json(self) -> dict:
        return {"name": self.name, "episodes": [asdict(episode) for episode in self.episodes]}
