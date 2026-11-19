"""M6 Phase D: the G8 held-write hook (targets/01-zep-graphiti/repros/repro_g8_held_write.py), with fakes.

The repro imports graphiti-core only when it runs, so the hook and the fixture answers load here with the standard
library alone. The fakes stand in for graphiti_core.graphiti (get_mentioned_nodes, add_nodes_and_edges_bulk) and for
a driver whose execute_query is a method of its class, as in graphiti-core's drivers.
"""

import asyncio
import contextlib
import importlib.util
import io
import unittest
from pathlib import Path
from types import SimpleNamespace

REPRO = (Path(__file__).resolve().parents[2] / "targets" / "01-zep-graphiti" / "repros"
         / "repro_g8_held_write.py")
_spec = importlib.util.spec_from_file_location("repro_g8_held_write", REPRO)
repro = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(repro)

COUNT = "MATCH (e:Episodic)-[:MENTIONS]->(n:Entity {uuid: $uuid}) RETURN count(*) AS episode_count"


class FakeDriver:
    def __init__(self, log):
        self.log = log

    async def execute_query(self, query, **kwargs):
        await asyncio.sleep(0)
        self.log.append(("query", query))
        return [], None, None


def fake_module(log, mentioned=3):
    async def get_mentioned_nodes(driver, episodes):
        await asyncio.sleep(0)
        return [f"n{i}" for i in range(mentioned)]

    async def add_nodes_and_edges_bulk(*args, **kwargs):
        log.append(("bulk", args))
        return "written"

    return SimpleNamespace(get_mentioned_nodes=get_mentioned_nodes, add_nodes_and_edges_bulk=add_nodes_and_edges_bulk)


async def remove_like(module, driver, log, between=0):
    """remove_episode's order: find the mentioned entities, count each one's MENTIONS, then delete."""
    nodes = await module.get_mentioned_nodes(driver, ["G8E"])
    for _ in nodes:
        await driver.execute_query(COUNT, uuid="x")
        for _ in range(between):
            await asyncio.sleep(0)
    await driver.execute_query("MATCH (n) DETACH DELETE n")
    log.append(("remove done", None))


class HoldTest(unittest.TestCase):
    def test_a_write_that_arrives_first_waits_for_the_last_count(self):
        async def scenario():
            log = []
            module, driver = fake_module(log), FakeDriver(log)
            hold = repro.HeldWrite(timeout_s=5)
            undo = hold.install(module, driver)
            write = asyncio.create_task(module.add_nodes_and_edges_bulk("episode"))
            await asyncio.sleep(0)
            self.assertFalse(any(kind == "bulk" for kind, _ in log), "the write must wait")
            await remove_like(module, driver, log, between=3)
            self.assertEqual(await write, "written")
            undo()
            return log, hold

        log, hold = asyncio.run(scenario())
        labels = [label for label, _ in hold.events]
        self.assertEqual(labels[:3], ["bulk write reached the hold", "remove found 3 mentioned entities", "count done"])
        self.assertLess(labels.index("count done"), labels.index("bulk write starts"))
        counts = [i for i, (kind, query) in enumerate(log) if kind == "query" and repro.COUNT_MARK in query]
        bulk = next(i for i, (kind, _) in enumerate(log) if kind == "bulk")
        self.assertEqual(len(counts), 3)
        self.assertGreater(bulk, counts[-1], "the write ran after the third count")
        self.assertFalse(hold.timed_out)
        self.assertIn("held", hold.summary())

    def test_a_write_after_the_count_passes_at_once(self):
        async def scenario():
            log = []
            module, driver = fake_module(log), FakeDriver(log)
            hold = repro.HeldWrite(timeout_s=5)
            hold.install(module, driver)
            await remove_like(module, driver, log)
            await module.add_nodes_and_edges_bulk("episode")
            return hold

        hold = asyncio.run(scenario())
        self.assertLess(hold.at("count done"), hold.at("bulk write reached the hold"))
        self.assertIn("not held", hold.summary())

    def test_other_queries_do_not_open_the_hold(self):
        async def scenario():
            log = []
            module, driver = fake_module(log, mentioned=2), FakeDriver(log)
            hold = repro.HeldWrite(timeout_s=5)
            hold.install(module, driver)
            await module.get_mentioned_nodes(driver, [])
            await driver.execute_query("MATCH (n) RETURN count(n)")
            await driver.execute_query(COUNT)
            first = hold.counted.is_set()
            await driver.execute_query(COUNT)
            return first, hold.counted.is_set()

        self.assertEqual(asyncio.run(scenario()), (False, True))

    def test_no_mentioned_entity_opens_at_once(self):
        async def scenario():
            log = []
            module, driver = fake_module(log, mentioned=0), FakeDriver(log)
            hold = repro.HeldWrite(timeout_s=5)
            hold.install(module, driver)
            await module.get_mentioned_nodes(driver, [])
            return hold.counted.is_set()

        self.assertTrue(asyncio.run(scenario()))

    def test_a_hold_that_never_opens_times_out_and_writes(self):
        async def scenario():
            log = []
            module, driver = fake_module(log), FakeDriver(log)
            hold = repro.HeldWrite(timeout_s=0.05)
            hold.install(module, driver)
            result = await module.add_nodes_and_edges_bulk("episode")
            return result, hold

        result, hold = asyncio.run(scenario())
        self.assertEqual(result, "written")
        self.assertTrue(hold.timed_out)
        self.assertIn("HOLD TIMED OUT", hold.summary())

    def test_undo_restores_the_originals(self):
        log = []
        module, driver = fake_module(log), FakeDriver(log)
        originals = (module.get_mentioned_nodes, module.add_nodes_and_edges_bulk)
        undo = repro.HeldWrite().install(module, driver)
        self.assertIn("execute_query", vars(driver))
        self.assertIsNot(module.add_nodes_and_edges_bulk, originals[1])
        undo()
        self.assertEqual((module.get_mentioned_nodes, module.add_nodes_and_edges_bulk), originals)
        self.assertNotIn("execute_query", vars(driver), "the class's method shows through again")
        self.assertEqual(driver.execute_query.__func__, FakeDriver.execute_query)


class FixtureTest(unittest.TestCase):
    def test_loads_without_graphiti_core(self):
        self.assertTrue(hasattr(repro, "build"))
        self.assertNotIn("graphiti_core", repro.__dict__)

    def test_answers_follow_the_fixture(self):
        prompt = "<CURRENT MESSAGE>\nAlice audited Payments. [wm:G8N]\n</CURRENT MESSAGE>"
        self.assertEqual([e["name"] for e in repro.extract_nodes(prompt)["extracted_entities"]], ["Alice", "Payments"])
        self.assertEqual([e["fact"] for e in repro.extract_edges(prompt)["edges"]], [repro.ADDED])
        same, lost, _ = repro.compare({"episodes": ["G8N", "G8S"], "entities": ["Acme", "Alice"],
                                       "facts": [f"{repro.SHARED} (1 episode)"]})
        self.assertFalse(same)
        self.assertEqual(lost["entities"], ["Payments"])
        self.assertEqual(lost["facts"], [f"{repro.ADDED} (1 episode)"])
        self.assertEqual(len(repro.hashed_vector("Alice audited Payments")), 1024)

    def test_bad_arguments(self):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(repro.main(["repro", "sqlite"]), 64)
            self.assertEqual(repro.main(["repro", "neo4j", "interleave"]), 64)
        self.assertIn("usage", err.getvalue())


if __name__ == "__main__":
    unittest.main()
