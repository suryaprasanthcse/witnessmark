"""The memory-layer runner, fixtures, stubs and checkers, without any real library.

A racy in-memory target looks up an entity, yields, then creates it if absent;
a serial one does the same under a lock. The runner must catch the first and
pass the second, which shows it can see a race before any real target runs.
"""

import asyncio
import json
import math
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from witnessmark.checkers import check_no_overlapping_current, check_present, check_unique_keys
from witnessmark.fixtures import Entity, Episode, Fact, Fixture
from witnessmark.history import OK, Op, read_history
from witnessmark.memory import MemoryRunConfig, MemoryTarget, RaceScenario, TargetSpec, max_in_flight, run_race
from witnessmark.stubs import embed, overlap
from witnessmark.timing import Stamp

REPO_ROOT = Path(__file__).resolve().parents[2]

FIXTURE = Fixture("test", [
    Episode(tag=f"T{i:02d}", name=f"T{i:02d}", text=f"Alice met Bob, note {i}", reference_time="2026-01-01T00:00:00Z",
            entities=(Entity("Alice", "alice"), Entity("Bob", "bob")),
            facts=(Fact("Alice", "Bob", "MET", f"Alice met Bob, note {i}"),))
    for i in range(8)
])

STORES: dict[str, dict] = {}


class MemoryStoreTarget(MemoryTarget):
    name = "memory"
    repo = "witnessmark/test"

    def __init__(self, racy: bool, store: str):
        self.racy = racy
        self.store = STORES.setdefault(store, {})
        self.lock = asyncio.Lock()

    def identity(self):
        return {"name": "memory", "repo": self.repo, "ref": "test", "digest": "sha256:" + "0" * 64}

    def components(self):
        return [{"role": "sut", "name": "memory", "version": "test"}]

    async def reset(self, group):
        self.store[group] = []

    async def _create(self, group, name):
        if name not in self.store[group]:
            await asyncio.sleep(0.002)  # the window between looking and writing
            self.store[group].append(name)

    async def ingest(self, item, group):
        episode = FIXTURE.episode(item["tag"])
        for entity in episode.entities:
            if self.racy:
                seen = entity.name in self.store[group]
                await asyncio.sleep(0.002)
                if not seen:
                    self.store[group].append(entity.name)
            else:
                async with self.lock:
                    await self._create(group, entity.name)
        return {"episode": episode.tag}

    async def search(self, query, group):
        return []

    async def dump(self, group):
        return {"entities": sorted(self.store[group])}


def make_target(racy: bool, store: str) -> MemoryStoreTarget:
    return MemoryStoreTarget(racy, store)


class SameGroup(RaceScenario):
    id = "test.same_group"
    invariants = ("I1B",)
    support = "supported"
    basis = "inferred"
    basis_ref = "test"

    def clients(self):
        return [("g", {"tag": episode.tag}) for episode in FIXTURE.episodes]

    def check(self, ops, states):
        return [check_unique_keys(dict(Counter(states["g"]["entities"])), "entities")]

    def sequential_expected(self, ops, states):
        met = states["g"]["entities"] == ["Alice", "Bob"]
        return met, "Alice and Bob once each", str(states["g"]["entities"])


class MemoryRunnerTest(unittest.TestCase):
    def run_race(self, racy: bool, mode: str = "asyncio"):
        with tempfile.TemporaryDirectory() as tmp:
            config = MemoryRunConfig(spec=TargetSpec(__name__, "make_target", {"racy": racy, "store": f"s{racy}{mode}"}),
                                     mode=mode, trials=4, evidence_root=Path(tmp), repo_root=REPO_ROOT,
                                     evidence_dir="memory/test")
            manifest = asyncio.run(run_race(config, SameGroup()))
            history = read_history(Path(manifest["path"]) / "history.jsonl")
            on_disk = json.loads((Path(manifest["path"]) / "run.json").read_text(encoding="utf-8"))
        return manifest, history, on_disk

    def test_racy_target_is_caught(self):
        manifest, _, _ = self.run_race(True)
        sequential, overlap_control = manifest["controls"]
        self.assertTrue(sequential["met"], sequential)
        self.assertTrue(overlap_control["met"], overlap_control)
        self.assertEqual(manifest["verdicts"][0]["status"], "FAIL")
        self.assertGreaterEqual(manifest["verdicts"][0]["magnitude"]["max"], 2)

    def test_serial_target_passes(self):
        manifest, history, on_disk = self.run_race(False)
        self.assertEqual(manifest["verdicts"][0]["status"], "PASS")
        self.assertEqual(len([op for op in history if op["phase"] in ("control", "race")]), 8 + 8 * 4)
        self.assertEqual(on_disk["scenario"]["mode"], "asyncio")
        self.assertEqual(Path(manifest["path"]).parent.name, "test.same_group.asyncio")

    def test_queue_mode_serialises_one_group(self):
        manifest, _, _ = self.run_race(True, "queue")
        self.assertEqual(manifest["verdicts"][0]["status"], "PASS", "a FIFO per group leaves nothing to race")


class FixtureAndStubTest(unittest.TestCase):
    def test_fixture_lookups(self):
        self.assertEqual([e.tag for e in FIXTURE.episodes_in("prev [wm:T03] now [wm:T01] [wm:T03] [wm:nope]")],
                         ["T03", "T01"])
        self.assertEqual(FIXTURE.entity_key("  alice "), "alice")
        self.assertIsNone(FIXTURE.entity_key("Carol"))
        self.assertEqual(FIXTURE.fact("alice met bob, NOTE 2").fact, "Alice met Bob, note 2")

    def test_contradiction_rules(self):
        a = Fact("A", "X", "LEADS", "A leads X", key="x.lead", value="a")
        b = Fact("B", "X", "LEADS", "B leads X", key="x.lead", value="b")
        plain = Fact("A", "Y", "LIKES", "A likes Y")
        fixture = Fixture("rules", [])
        self.assertTrue(fixture.contradicts(a, b))
        self.assertFalse(fixture.contradicts(a, plain))
        self.assertTrue(fixture.same_assertion(a, Fact("A", "X", "LEADS", "a LEADS x")))
        self.assertFalse(fixture.same_assertion(a, b))

    def test_repeated_tag_is_rejected(self):
        episode = FIXTURE.episodes[0]
        with self.assertRaises(ValueError):
            Fixture("dup", [episode, episode])

    def test_embedding_is_deterministic_and_unit_length(self):
        first, second = embed("Alice works at Company3"), embed("alice works at company3")
        self.assertEqual(first, second)
        self.assertAlmostEqual(math.sqrt(sum(v * v for v in first)), 1.0)
        related = sum(x * y for x, y in zip(embed("Alice works at Company3"), embed("Alice works at Company5")))
        self.assertGreater(related, 0.5)
        self.assertEqual(len(embed("")), 1024)

    def test_overlap(self):
        self.assertEqual(overlap("a b c", "a b d"), 0.5)
        self.assertEqual(overlap("", ""), 0.0)


class MemoryCheckerTest(unittest.TestCase):
    def test_unique_keys(self):
        self.assertTrue(check_unique_keys({"alice": 1, "bob": 1}, "entities").held)
        check = check_unique_keys({"alice": 3, "bob": 1}, "entities", {"alice": ["E1", "E2"]})
        self.assertFalse(check.held)
        self.assertEqual((check.magnitude, check.witnesses), (3, ["E1", "E2"]))

    def test_present(self):
        self.assertTrue(check_present(["a", "b"], {"a", "b", "c"}, "facts").held)
        self.assertEqual(check_present(["a", "b"], {"a"}, "facts").witnesses, ["b"])

    def test_overlapping_current_versions(self):
        chain = [
            {"label": "v1", "valid_at": "2026-01-01T00:00:00Z", "invalid_at": "2026-02-01T00:00:00Z", "current": False},
            {"label": "v2", "valid_at": "2026-02-01T00:00:00Z", "invalid_at": None, "current": True},
        ]
        self.assertTrue(check_no_overlapping_current(chain, "x").held)
        both = [dict(chain[0], current=True, invalid_at=None), chain[1]]
        check = check_no_overlapping_current(both, "x")
        self.assertFalse(check.held)
        self.assertEqual(check.witnesses, ["v1", "v2"])
        touching = [dict(chain[0], current=True), chain[1]]
        self.assertTrue(check_no_overlapping_current(touching, "x").held, "[a, b) and [b, c) do not overlap")

    def test_max_in_flight(self):
        def op(start, end):
            return Op("r", 1, "race", f"o{start}", "c", "ingest", {}, Stamp(start, "w"),
                      Stamp(end, "w") if end is not None else None, OK if end is not None else "unknown")
        self.assertEqual(max_in_flight([op(0, 10), op(5, 15), op(20, 30)]), 2)
        self.assertEqual(max_in_flight([op(0, 10), op(10, 20)]), 1, "back-to-back operations never overlap")
        self.assertEqual(max_in_flight([op(0, None), op(50, 60)]), 2, "an unknown outcome stays in flight")

    def test_op_round_trip(self):
        op = Op("r", 2, "race", "2-c01-0", "c01", "ingest", {"tag": "T01"}, Stamp(1, "w", "host"),
                Stamp(2, "w2", "host"), OK, {"episode": "T01"}, process="42")
        self.assertEqual(Op.from_json(op.to_json()).to_json(), op.to_json())


if __name__ == "__main__":
    unittest.main()
