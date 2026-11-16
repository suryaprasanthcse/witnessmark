"""Scripted documents for Cognee (target blueprint sections 4 and 5).

Every document is one short text ending in ``[wm:<tag>]``. The fixture holds,
for each tag, what a perfect model extracts from it: entities with a type and a
canonical key, and the relations between them. Entity ids in the extraction are
the canonical names, so the same entity in two documents is one id, as an ideal
model would answer.

All corpora are generated here; nothing comes from outside the repository.
"""

from __future__ import annotations

import random
import re
import uuid
from dataclasses import dataclass, field

TAG = re.compile(r"\[wm:([A-Za-z0-9_\-]+)\]")


def tags_in(text: str | None) -> list[str]:
    found = []
    for tag in TAG.findall(text or ""):
        if tag not in found:
            found.append(tag)
    return found


def key(name: str) -> str:
    return " ".join(name.lower().split())


@dataclass(frozen=True)
class Ent:
    name: str
    type: str


@dataclass(frozen=True)
class Rel:
    source: str
    relation: str
    target: str


@dataclass(frozen=True)
class Doc:
    tag: str
    sentence: str
    entities: tuple[Ent, ...]
    relations: tuple[Rel, ...]

    @property
    def text(self) -> str:
        return f"{self.sentence} [wm:{self.tag}]"

    @property
    def data_id(self) -> str:
        """A pinned id, as #6170's reporter pinned theirs."""
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"witnessmark:{self.tag}"))


@dataclass
class Corpus:
    name: str
    docs: list[Doc] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.by_tag = {doc.tag: doc for doc in self.docs}
        if len(self.by_tag) != len(self.docs):
            raise ValueError(f"corpus {self.name} repeats a tag")

    def doc(self, tag: str) -> Doc:
        return self.by_tag[tag]

    def entity_keys(self, tags) -> set[str]:
        return {key(e.name) for t in tags for e in self.by_tag[t].entities}

    def relation_keys(self, tags) -> set[str]:
        return {f"{key(r.source)}|{r.relation}|{key(r.target)}" for t in tags for r in self.by_tag[t].relations}


# --- C1, C2, C3, C5, C6: people, companies and cities that documents share ----------------------------------

PEOPLE = ["Alice Moreau", "Bilal Okafor", "Chen Wei", "Dana Petrov", "Elif Kaya", "Farid Haddad"]
COMPANIES = [("Acme Robotics", "Lyon"), ("Borealis Foods", "Oslo"), ("Cobalt Analytics", "Porto"),
             ("Delta Freight", "Gdansk")]


def employment(tag: str, person: str, company: int, note: str) -> Doc:
    org, city = COMPANIES[company]
    return Doc(tag, f"{person} works at {org}, which is based in {city}. {note}.",
               (Ent(person, "Person"), Ent(org, "Organization"), Ent(city, "City")),
               (Rel(person, "works_at", org), Rel(org, "based_in", city)))


def shared_corpus(prefix: str, count: int, offset: int = 0) -> list[Doc]:
    """``count`` documents; person j % 6 at company j % 4, so entities and relations repeat."""
    return [employment(f"{prefix}{j:03d}", PEOPLE[(j + offset) % len(PEOPLE)], (j + offset) % len(COMPANIES),
                       f"Record {prefix}{j:03d}") for j in range(count)]


# --- C4: #6170's corpus shape ------------------------------------------------------------------------------

_ADJ = ["Golden", "Silver", "Blue", "Red", "Green", "Northern", "Southern", "Eastern", "Western", "Royal", "Urban",
        "Rustic", "Modern", "Classic", "Sunny", "Misty", "Quiet", "Lucky", "Bright", "Hidden"]
_NOUN = ["Bakery", "Garage", "Florist", "Bistro", "Pharmacy", "Bookshop", "Tailor", "Barber", "Deli", "Laundry",
         "Hardware", "Cafe", "Studio", "Clinic", "Market", "Cycles", "Optics", "Kitchen", "Gallery", "Print"]
_STREET = ["Maple", "Oak", "Cedar", "Elm", "Birch", "Willow", "Harbor", "Mill", "Church", "Station", "Park", "River",
           "Hill", "Bridge", "Garden", "Market", "Castle", "Forest", "Lake", "Meadow"]
_KIND = ["Street", "Road", "Avenue", "Lane"]
_CITY = ["Springfield", "Riverton", "Lakeside", "Fairview", "Kingsport", "Ashford", "Brookhaven", "Cloverdale"]


def scale_corpus(count: int = 5401, seed: int = 6170) -> list[Doc]:
    """One dated sentence of about 100 characters per document: a business, an address, a phone number."""
    rng = random.Random(seed)
    docs = []
    for j in range(count):
        business = f"{rng.choice(_ADJ)} {rng.choice(_NOUN)} {rng.randrange(1, 400)}"
        address = f"{rng.randrange(1, 999)} {rng.choice(_STREET)} {rng.choice(_KIND)}, {rng.choice(_CITY)}"
        phone = f"+1-555-{rng.randrange(100, 999)}-{rng.randrange(1000, 9999)}"
        day = f"2025-{rng.randrange(1, 13):02d}-{rng.randrange(1, 29):02d}"
        sentence = f"On {day} {business} opened at {address}; phone {phone}."
        docs.append(Doc(f"S{j:05d}", sentence,
                        (Ent(business, "Business"), Ent(address, "Address"), Ent(phone, "PhoneNumber")),
                        (Rel(business, "located_at", address), Rel(business, "has_phone", phone))))
    return docs


# --- the registry the stub and the engine share ------------------------------------------------------------


def build(name: str) -> Corpus:
    if name == "c1":
        return Corpus("c1", shared_corpus("C1D", 24))
    if name == "c2":
        return Corpus("c2", shared_corpus("C2A", 8) + shared_corpus("C2B", 8, 1) + shared_corpus("C2C", 8, 2))
    if name == "c3":
        return Corpus("c3", [employment("C3X", "Alice Moreau", 0, "Shared file record")])
    if name == "c4":
        return Corpus("c4", scale_corpus())
    if name == "c5":
        return Corpus("c5", shared_corpus("C5D", 10))
    if name == "c6":
        return Corpus("c6", [
            employment("C6D1", "Alice Moreau", 0, "Deletion record one"),   # Alice only here; Acme and Lyon shared
            employment("C6D2", "Bilal Okafor", 0, "Deletion record two"),
            employment("C6D3", "Chen Wei", 1, "Deletion record three"),
            employment("C6E1", "Dana Petrov", 0, "Other dataset record one"),  # another dataset, Acme again
            employment("C6E2", "Elif Kaya", 2, "Other dataset record two"),
        ])
    raise ValueError(f"unknown corpus {name!r}")


CORPORA = ("c1", "c2", "c3", "c4", "c5", "c6")

# Conflict review (improve's review_conflicts stage, target blueprint C30): the contradictions each corpus
# scripts, keyed by the canonical key of the subject. No corpus scripts one. A person named at two companies in two
# undated records holds both jobs, and a company's employees are a set, so an ideal model that follows the fixture
# reports no conflict for any subject it is shown.
SCRIPTED_CONFLICTS: dict[str, list] = {}


def entity_keys() -> set[str]:
    """The canonical key of every entity any corpus names."""
    return {key(e.name) for doc in all_docs().values() for e in doc.entities}


def all_docs() -> dict[str, Doc]:
    docs: dict[str, Doc] = {}
    for name in CORPORA:
        for doc in build(name).docs:
            if doc.tag in docs:
                raise ValueError(f"tag {doc.tag} appears in two corpora")
            docs[doc.tag] = doc
    return docs
