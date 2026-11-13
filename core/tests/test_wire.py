"""RESP framing and FalkorDB parameter encoding."""

import io
import unittest

from witnessmark.adapters.base import EngineError
from witnessmark.adapters.falkordb import (cypher_literal, module_version, parse_query_reply, version_string,
                                           with_params)
from witnessmark.adapters.resp import RespErrorReply, encode_command, read_reply


class RespTest(unittest.TestCase):
    def test_encode_command(self):
        self.assertEqual(encode_command("PING"), b"*1\r\n$4\r\nPING\r\n")
        self.assertEqual(encode_command("GRAPH.QUERY", "g", "RETURN 1"),
                         b"*3\r\n$11\r\nGRAPH.QUERY\r\n$1\r\ng\r\n$8\r\nRETURN 1\r\n")

    def test_encode_counts_bytes_not_characters(self):
        self.assertEqual(encode_command("é"), b"*1\r\n$2\r\n\xc3\xa9\r\n")

    def test_read_scalar_replies(self):
        self.assertEqual(read_reply(io.BytesIO(b"+PONG\r\n")), "PONG")
        self.assertEqual(read_reply(io.BytesIO(b":42\r\n")), 42)
        self.assertEqual(read_reply(io.BytesIO(b"$5\r\nhello\r\n")), "hello")
        self.assertIsNone(read_reply(io.BytesIO(b"$-1\r\n")))
        error = read_reply(io.BytesIO(b"-ERR boom\r\n"))
        self.assertIsInstance(error, RespErrorReply)
        self.assertEqual(error.message, "ERR boom")

    def test_read_nested_arrays(self):
        payload = b"*3\r\n*1\r\n$3\r\nwon\r\n*1\r\n*1\r\n:1\r\n*1\r\n$26\r\nProperties set: 2 (approx)\r\n"
        self.assertEqual(read_reply(io.BytesIO(payload)), [["won"], [[1]], ["Properties set: 2 (approx)"]])

    def test_truncated_reply_is_a_connection_error(self):
        with self.assertRaises(ConnectionError):
            read_reply(io.BytesIO(b"$5\r\nhel"))
        with self.assertRaises(ConnectionError):
            read_reply(io.BytesIO(b""))


class FalkorEncodingTest(unittest.TestCase):
    def test_literals(self):
        self.assertEqual(cypher_literal(None), "null")
        self.assertEqual(cypher_literal(True), "true")
        self.assertEqual(cypher_literal(7), "7")
        self.assertEqual(cypher_literal(1.5), "1.5")
        self.assertEqual(cypher_literal("it's"), "'it\\'s'")
        self.assertEqual(cypher_literal("a\\b"), "'a\\\\b'")
        self.assertEqual(cypher_literal(["c00", 1]), "['c00', 1]")
        self.assertEqual(cypher_literal({"k": 1, "odd key": "v"}), "{k: 1, `odd key`: 'v'}")
        with self.assertRaises(ValueError):
            cypher_literal(float("nan"))

    def test_params_prefix(self):
        self.assertEqual(with_params("RETURN $a", {"a": 1, "b": "x"}), "CYPHER a=1 b='x' RETURN $a")
        self.assertEqual(with_params("RETURN 1", {}), "RETURN 1")
        with self.assertRaises(ValueError):
            with_params("RETURN 1", {"bad name": 1})

    def test_parse_reply_with_and_without_rows(self):
        reply = parse_query_reply([["won"], [[1]], ["Properties set: 2", "Query internal execution time: 0.1 ms"]])
        self.assertEqual(reply.columns, ["won"])
        self.assertEqual(reply.scalar(), 1)
        self.assertEqual(reply.stats["Properties set"], "2")
        empty = parse_query_reply([["Nodes created: 1"]])
        self.assertEqual(empty.rows, [])
        self.assertEqual(empty.stats["Nodes created"], "1")

    def test_nested_error_is_a_refusal(self):
        with self.assertRaises(EngineError):
            parse_query_reply([["x"], [[RespErrorReply("boom")]], []])

    def test_module_version(self):
        modules = [["name", "graph", "ver", 60004, "path", "/x.so", "args", []]]
        self.assertEqual(module_version(modules), 60004)
        self.assertEqual(version_string(60004), "6.0.4")
        self.assertIsNone(module_version([["name", "search", "ver", 1]]))


if __name__ == "__main__":
    unittest.main()
