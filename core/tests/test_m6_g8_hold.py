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
    """graphiti-core's drivers take `execute_query(self, cypher_query_, **kwargs)`; the kwargs are Cypher parameters."""

    def __init__(self, log):
        self.log = log

    async def execute_query(self, cypher_query_, **kwargs):
        await asyncio.sleep(0)
        self.log.append(("query", cypher_query_))
        return [], None, None


def fake_classes(log):
    """Edge and Node with graphiti-core's shape: delete_by_uuids is a classmethod defined on the class itself."""

    class Edge:
        @classmethod
        async def delete_by_uuids(cls, driver, uuids):
            await asyncio.sleep(0)
            log.append(("edge delete", cls.__name__))

    class Node:
        @classmethod
        async def delete_by_uuids(cls, driver, uuids, batch_size=100):
            await asyncio.sleep(0)
            log.append(("node delete", cls.__name__))

    return Edge, Node


def fake_module(log, mentioned=3, write_steps=1, write_raises=False):
    async def get_mentioned_nodes(driver, episodes):
        await asyncio.sleep(0)
        return [f"n{i}" for i in range(mentioned)]

    async def add_nodes_and_edges_bulk(*args, **kwargs):
        for _ in range(write_steps):  # a write that takes several turns of the loop, like a real round trip
            await asyncio.sleep(0)
        if write_raises:
            raise RuntimeError("write failed")
        log.append(("bulk", args))
        return "written"

    edge, node = fake_classes(log)
    return SimpleNamespace(get_mentioned_nodes=get_mentioned_nodes, add_nodes_and_edges_bulk=add_nodes_and_edges_bulk,
                           Edge=edge, Node=node)


async def remove_like(module, driver, log, between=0):
    """remove_episode's order: find the mentioned entities, count each one's MENTIONS, then delete edges and nodes."""
    nodes = await module.get_mentioned_nodes(driver, ["G8E"])
    for _ in nodes:
        await driver.execute_query(COUNT, uuid="x")
        for _ in range(between):
            await asyncio.sleep(0)
    await module.Edge.delete_by_uuids(driver, ["e"])
    await module.Node.delete_by_uuids(driver, ["n"])
    log.append(("remove done", None))


async def add_like(module, log, steps_before_write=0):
    """add_episode's order: extraction and resolution (some turns of the loop), then the bulk write."""
    for _ in range(steps_before_write):
        await asyncio.sleep(0)
    return await module.add_nodes_and_edges_bulk("G8N")


def position(log, kind):
    return next(i for i, (k, _) in enumerate(log) if k == kind)


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

    def test_cypher_parameters_named_query_pass_through(self):
        """The bug behind M6 G8 commands 2 and 4: the wrapper took a parameter named `query`, and graphiti-core's
        search passes a Cypher parameter `query=`, so every held add raised TypeError before its write."""
        async def scenario():
            log = []
            module, driver = fake_module(log, mentioned=1), FakeDriver(log)
            hold = repro.HeldWrite(timeout_s=5)
            hold.install(module, driver)
            await module.get_mentioned_nodes(driver, [])
            await driver.execute_query("CALL db.index.fulltext.queryRelationships('x', $query)", query="Alice",
                                       limit=10, routing_="r")
            await driver.execute_query(COUNT, uuid="u", query="also a parameter")
            return log, hold.counted.is_set()

        log, opened = asyncio.run(scenario())
        self.assertTrue(opened)
        self.assertEqual(len(log), 2)

    def test_undo_restores_the_originals(self):
        log = []
        module, driver = fake_module(log), FakeDriver(log)
        originals = (module.get_mentioned_nodes, module.add_nodes_and_edges_bulk)
        descriptors = (vars(module.Edge)["delete_by_uuids"], vars(module.Node)["delete_by_uuids"])
        undo = repro.HeldWrite().install(module, driver)
        self.assertIn("execute_query", vars(driver))
        self.assertIsNot(module.add_nodes_and_edges_bulk, originals[1])
        self.assertIsNot(vars(module.Node)["delete_by_uuids"], descriptors[1])
        undo()
        self.assertEqual((module.get_mentioned_nodes, module.add_nodes_and_edges_bulk), originals)
        self.assertEqual((vars(module.Edge)["delete_by_uuids"], vars(module.Node)["delete_by_uuids"]), descriptors)
        self.assertNotIn("execute_query", vars(driver), "the class's method shows through again")
        self.assertEqual(driver.execute_query.__func__, FakeDriver.execute_query)

    def test_unknown_mode(self):
        with self.assertRaises(ValueError):
            repro.HeldWrite(mode="interleave")


class PinnedTest(unittest.TestCase):
    """The two-sided gate: count -> write -> delete, whichever call gets there first."""

    def run_race(self, mode, steps_before_write, between=0, timeout_s=5, write_raises=False, add=True):
        async def scenario():
            log = []
            module, driver = fake_module(log, write_steps=3, write_raises=write_raises), FakeDriver(log)
            hold = repro.HeldWrite(timeout_s=timeout_s, mode=mode)
            undo = hold.install(module, driver)
            tasks = [asyncio.create_task(remove_like(module, driver, log, between=between))]
            if add:
                tasks.append(asyncio.create_task(add_like(module, log, steps_before_write)))
            results = await asyncio.gather(*tasks, return_exceptions=True)
            undo()
            return log, hold, results

        return asyncio.run(scenario())

    def assert_pinned(self, log, hold):
        last_count = max(i for i, (kind, query) in enumerate(log) if kind == "query" and repro.COUNT_MARK in query)
        self.assertLess(last_count, position(log, "bulk"), "the write ran after the last count")
        self.assertLess(position(log, "bulk"), position(log, "edge delete"), "no delete before the write completed")
        self.assertLess(position(log, "bulk"), position(log, "node delete"))
        self.assertTrue(hold.pinned_order())
        self.assertLess(hold.at("bulk write returned"), hold.first_delete())
        self.assertFalse(hold.timed_out)

    def test_write_first_waits_for_the_count_and_the_delete_waits_for_the_write(self):
        log, hold, _ = self.run_race("pinned", steps_before_write=0, between=3)
        self.assert_pinned(log, hold)
        self.assertIn("order count -> write -> delete yes", hold.summary())

    def test_count_first_makes_the_remove_wait_for_a_late_write(self):
        log, hold, _ = self.run_race("pinned", steps_before_write=40)
        self.assert_pinned(log, hold)
        self.assertLess(hold.at("remove waits for the write"), hold.at("bulk write starts"))
        self.assertLess(hold.at("bulk write returned"), hold.at("remove resumes") + 1e-9)

    def test_held_alone_lets_the_delete_run_before_a_late_write(self):
        """What `held` does not force: with the write late, the deletes go first."""
        log, hold, _ = self.run_race("held", steps_before_write=40)
        self.assertLess(position(log, "node delete"), position(log, "bulk"))
        self.assertFalse(hold.pinned_order())
        self.assertIn("order count -> write -> delete NO", hold.summary())

    def test_observe_times_everything_and_waits_for_nothing(self):
        log, hold, _ = self.run_race("observe", steps_before_write=0, between=3)
        self.assertLess(position(log, "bulk"), max(i for i, (k, q) in enumerate(log) if k == "query"),
                        "in observe mode the write does not wait for the count")
        labels = [label for label, _ in hold.events]
        for label in ("count done", "bulk write starts", "bulk write returned", "edge delete starts",
                      "edge delete returned", "node delete starts", "node delete returned"):
            self.assertIn(label, labels)

    def test_remove_times_out_when_no_write_comes(self):
        log, hold, _ = self.run_race("pinned", steps_before_write=0, timeout_s=0.05, add=False)
        self.assertTrue(hold.timed_out)
        self.assertIn("hold timed out (remove)", [label for label, _ in hold.events])
        self.assertIn(("remove done", None), log, "after the timeout the remove goes on to its deletes")
        self.assertIn("HOLD TIMED OUT", hold.summary())

    def test_a_write_that_raises_still_releases_the_remove(self):
        log, hold, results = self.run_race("pinned", steps_before_write=0, between=3, write_raises=True)
        self.assertIsInstance(results[1], RuntimeError)
        self.assertIn(("remove done", None), log)
        self.assertFalse(hold.timed_out)
        self.assertIn("bulk write raised", [label for label, _ in hold.events])


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
