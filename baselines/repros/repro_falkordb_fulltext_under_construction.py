#!/usr/bin/env python3
"""Repro: what a FalkorDB fulltext query returns while its index is UNDER CONSTRUCTION.

Each trial deletes the test graph, creates N RELATES_TO relationships whose `fact` contains a probe term, and then
creates a fulltext index on RELATES_TO(fact). Until db.indexes() reports that index OPERATIONAL (or the timeout
passes), it samples repeatedly: one read of db.indexes(), then one fulltext query that counts the relationships
matching the probe term. Every relationship matches, so a ready index answers N. Each sample is classified:

    no_index_rows   db.indexes() lists no RELATES_TO fulltext index; the query returned a count
    no_index_error  the same, and the query returned an error
    uc_fewer        the index is UNDER CONSTRUCTION and the query returned fewer than N
    uc_all          the index is UNDER CONSTRUCTION and the query returned all N
    uc_error        the index is UNDER CONSTRUCTION and the query returned an error
    operational     the index is OPERATIONAL
    other           anything else (an unknown status, a status read that failed, more than N rows)

Sequential control, per trial: once the index is OPERATIONAL, the query must return exactly N. A trial whose control
is not met, or whose index is not OPERATIONAL within the timeout, is invalid.

The status and the query are read one after the other, not atomically, so a sample can straddle a change of status.

    python repro_falkordb_fulltext_under_construction.py HOST PORT N TRIALS

Standard library only, with a minimal RESP client inline; nothing else to install. The fulltext DDL follows FalkorDB's
docs at FalkorDB/docs 1ec5540a986ac596c5e4fc8f0bbc6f309c13a67a: cypher/indexing/fulltext-index.mdx L567-589
(relationship index, DDL form) and L11-13 (the procedure form does not work on 6.0; the DDL form works on v4.x and
6.0); cypher/indexing/index.mdx L46 (db.indexes() yields each index's status).

Exit status: 0 if every trial is valid and no under-construction sample returned fewer rows or an error;
1 if every trial is valid and at least one such sample did; 2 if any trial is invalid.
"""

from __future__ import annotations

import platform
import socket
import sys
import time

GRAPH = "wm_m6_fulltext_repro"
TERM = "quokka"
BATCH = 1000
TIMEOUT_S = 120.0

CLASSES = ("no_index_rows", "no_index_error", "uc_fewer", "uc_all", "uc_error", "operational", "other")


# --- RESP ---------------------------------------------------------------------------------------------------------


class RespError(Exception):
    """An error reply from the server."""


def encode(*args) -> bytes:
    parts = [b"*%d\r\n" % len(args)]
    for arg in args:
        data = arg if isinstance(arg, bytes) else str(arg).encode("utf-8")
        parts.append(b"$%d\r\n%s\r\n" % (len(data), data))
    return b"".join(parts)


def read_reply(stream):
    """One RESP2 reply from a binary file-like object. Error replies nested in arrays come back as RespError values."""
    line = stream.readline()
    if not line.endswith(b"\r\n"):
        raise ConnectionError("connection closed mid-reply")
    kind, body = line[:1], line[1:-2]
    if kind == b"+":
        return body.decode("utf-8", "replace")
    if kind == b"-":
        return RespError(body.decode("utf-8", "replace"))
    if kind == b":":
        return int(body)
    if kind == b"$":
        size = int(body)
        if size < 0:
            return None
        data = stream.read(size + 2)
        return data[:-2].decode("utf-8", "replace")
    if kind == b"*":
        size = int(body)
        return None if size < 0 else [read_reply(stream) for _ in range(size)]
    raise ConnectionError(f"unexpected RESP type {kind!r}")


class Client:
    """A blocking RESP client on one TCP connection."""

    def __init__(self, host: str, port: int, timeout: float = 60.0):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.stream = self.sock.makefile("rb")

    def command(self, *args):
        self.sock.sendall(encode(*args))
        reply = read_reply(self.stream)
        if isinstance(reply, RespError):
            raise reply
        if isinstance(reply, list):
            for item in reply:
                if isinstance(item, RespError):
                    raise item
        return reply

    def close(self) -> None:
        self.stream.close()
        self.sock.close()


def rows_of(reply) -> list:
    """The rows of a GRAPH.QUERY reply: [header, rows, stats], or [stats] for a query that returns nothing."""
    return reply[1] if isinstance(reply, list) and len(reply) == 3 else []


def flat_text(value) -> str:
    if isinstance(value, list):
        return " ".join(flat_text(item) for item in value)
    return "" if value is None else str(value)


# --- the trial ----------------------------------------------------------------------------------------------------


def load_batch_query(start: int, end: int) -> str:
    return (f"UNWIND range({start}, {end}) AS i CREATE (:Entity {{i: i}})-[:RELATES_TO {{i: i, fact: 'fact ' + "
            f"toString(i) + ' mentions {TERM}'}}]->(:Entity {{i: i}})")


COUNT_LOADED = "MATCH ()-[r:RELATES_TO]->() RETURN count(r)"
CREATE_INDEX = "CREATE FULLTEXT INDEX FOR ()-[r:RELATES_TO]-() ON (r.fact)"
INDEXES = "CALL db.indexes() YIELD label, types, entitytype, status RETURN label, types, entitytype, status"
PROBE = f"CALL db.idx.fulltext.queryRelationships('RELATES_TO', '{TERM}') YIELD relationship RETURN count(relationship)"


def status_category(raw) -> str:
    """FalkorDB reports e.g. '[Indexing] 0/1000: UNDER CONSTRUCTION'; keep the state, drop the progress."""
    text = str(raw).strip()
    if text.startswith("[") and ":" in text:
        text = text.rsplit(":", 1)[1]
    return text.strip().upper() or "UNKNOWN"


def relates_to_fulltext(index_rows: list):
    """The raw status of the RELATES_TO fulltext index, or None if db.indexes() does not list it."""
    for row in index_rows:
        if isinstance(row, list) and len(row) >= 4 and row[0] == "RELATES_TO" and "FULLTEXT" in flat_text(row[1]):
            return row[3]
    return None


def classify(status_raw, status_error, rows, query_error, n: int) -> str:
    """One sample's class. status_raw is None when db.indexes() lists no RELATES_TO fulltext index."""
    if status_error is not None:
        return "other"
    if status_raw is None:
        return "no_index_error" if query_error is not None else "no_index_rows"
    state = status_category(status_raw)
    if state == "OPERATIONAL":
        return "operational"
    if "CONSTRUCTION" in state:
        if query_error is not None:
            return "uc_error"
        if rows < n:
            return "uc_fewer"
        if rows == n:
            return "uc_all"
    return "other"


def query(client, cypher: str, read_only: bool = False):
    return client.command("GRAPH.RO_QUERY" if read_only else "GRAPH.QUERY", GRAPH, cypher)


def sample(client, n: int, t0: float, clock=time.perf_counter) -> dict:
    record = {"t_ms": (clock() - t0) * 1000, "status_raw": None, "status_error": None,
              "rows": None, "query_error": None}
    try:
        record["status_raw"] = relates_to_fulltext(rows_of(query(client, INDEXES, read_only=True)))
    except RespError as exc:
        record["status_error"] = str(exc)
    try:
        record["rows"] = int(rows_of(query(client, PROBE, read_only=True))[0][0])
    except RespError as exc:
        record["query_error"] = str(exc)
    record["class"] = classify(record["status_raw"], record["status_error"], record["rows"],
                               record["query_error"], n)
    return record


def plain_steps(n: int) -> list[str]:
    """The commands of one trial, as redis-cli would send them."""
    steps = [f"GRAPH.DELETE {GRAPH}"]
    for start in range(0, n, BATCH):
        steps.append(f'GRAPH.QUERY {GRAPH} "{load_batch_query(start, min(start + BATCH, n) - 1)}"')
    steps.append(f'GRAPH.QUERY {GRAPH} "{COUNT_LOADED}"')
    steps.append(f'GRAPH.QUERY {GRAPH} "{CREATE_INDEX}"')
    steps.append("repeat until the status is OPERATIONAL:")
    steps.append(f'  GRAPH.RO_QUERY {GRAPH} "{INDEXES}"')
    steps.append(f'  GRAPH.RO_QUERY {GRAPH} "{PROBE}"')
    return steps


def run_trial(client, n: int, timeout_s: float = TIMEOUT_S, clock=time.perf_counter) -> dict:
    trial = {"valid": False, "reason": None, "samples": [], "create_ms": None, "operational_ms": None,
             "control_rows": None}
    try:
        client.command("GRAPH.DELETE", GRAPH)
    except RespError:
        pass  # no graph to delete
    for start in range(0, n, BATCH):
        query(client, load_batch_query(start, min(start + BATCH, n) - 1))
    loaded = int(rows_of(query(client, COUNT_LOADED))[0][0])
    if loaded != n:
        trial["reason"] = f"loaded {loaded} relationships, expected {n}"
        return trial
    before = relates_to_fulltext(rows_of(query(client, INDEXES, read_only=True)))
    if before is not None:
        trial["reason"] = f"an index existed before creation ({before})"
        return trial
    t0 = clock()
    query(client, CREATE_INDEX)
    trial["create_ms"] = (clock() - t0) * 1000
    while True:
        record = sample(client, n, t0, clock)
        trial["samples"].append(record)
        if record["class"] == "operational":
            trial["operational_ms"] = record["t_ms"]
            break
        if clock() - t0 > timeout_s:
            trial["reason"] = f"index not OPERATIONAL within {timeout_s:.0f} s"
            return trial
    control = sample(client, n, t0, clock)
    trial["control_rows"] = control["rows"]
    if control["class"] != "operational" or control["rows"] != n:
        trial["reason"] = (f"control: status {control['status_raw']!r}, rows {control['rows']}, "
                           f"error {control['query_error']!r}; expected OPERATIONAL and {n}")
        return trial
    trial["valid"] = True
    return trial


# --- output -------------------------------------------------------------------------------------------------------


def runs(samples: list[dict]) -> list[dict]:
    """Consecutive samples of the same class, merged."""
    merged = []
    for record in samples:
        if merged and merged[-1]["class"] == record["class"]:
            run = merged[-1]
        else:
            run = {"class": record["class"], "count": 0, "first_ms": record["t_ms"], "rows": [], "errors": set(),
                   "first_status": record["status_raw"]}
            merged.append(run)
        run["count"] += 1
        run["last_ms"] = record["t_ms"]
        run["last_status"] = record["status_raw"]
        if record["rows"] is not None:
            run["rows"].append(record["rows"])
        for key in ("status_error", "query_error"):
            if record[key] is not None:
                run["errors"].add(record[key])
    return merged


def counts(samples: list[dict]) -> dict:
    tally = dict.fromkeys(CLASSES, 0)
    for record in samples:
        tally[record["class"]] += 1
    return tally


def describe_run(run: dict) -> str:
    rows = run["rows"]
    rows_text = (f"rows {min(rows)}" if rows and min(rows) == max(rows) else
                 f"rows {min(rows)}-{max(rows)}" if rows else "no rows")
    text = (f"{run['class']:<15} x{run['count']:<5} t={run['first_ms']:.1f}-{run['last_ms']:.1f} ms  {rows_text}  "
            f"status {run['first_status']!r}")
    if run["last_status"] != run["first_status"]:
        text += f" .. {run['last_status']!r}"
    if run["errors"]:
        text += f"  errors {sorted(run['errors'])}"
    return text


def engine_info(client) -> list[str]:
    lines = []
    try:
        info = client.command("INFO", "server")
        version = [line for line in str(info).splitlines() if line.startswith("redis_version:")]
        lines.append(version[0] if version else "redis_version: unknown")
    except RespError as exc:
        lines.append(f"INFO server: error {exc}")
    try:
        for module in client.command("MODULE", "LIST"):
            fields = dict(zip(module[0::2], module[1::2])) if isinstance(module, list) else {}
            lines.append(f"module {fields.get('name')} ver {fields.get('ver')}")
    except RespError as exc:
        lines.append(f"MODULE LIST: error {exc}")
    return lines


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        print("usage: python repro_falkordb_fulltext_under_construction.py HOST PORT N TRIALS", file=sys.stderr)
        return 64
    host, port, n, trials = argv[1], int(argv[2]), int(argv[3]), int(argv[4])
    client = Client(host, port)
    print(f"repro_falkordb_fulltext_under_construction: {host}:{port}, N = {n}, trials = {trials}, "
          f"timeout {TIMEOUT_S:.0f} s per trial, probe term {TERM!r}")
    print(f"python {platform.python_version()} on {platform.system()} {platform.release()}")
    for line in engine_info(client):
        print(line)
    print()
    print("Plain steps of one trial:")
    for step in plain_steps(n):
        print(f"  {step}")
    print()
    results = []
    for k in range(1, trials + 1):
        trial = run_trial(client, n)
        results.append(trial)
        tally = counts(trial["samples"])
        verdict = "valid" if trial["valid"] else f"INVALID ({trial['reason']})"
        if trial["create_ms"] is None:
            print(f"trial {k:>2}: {verdict}")
        else:
            print(f"trial {k:>2}: {verdict}; {len(trial['samples'])} samples; "
                  f"CREATE INDEX returned in {trial['create_ms']:.1f} ms")
            operational = (f"{trial['operational_ms']:.1f} ms" if trial["operational_ms"] is not None else "never")
            print(f"  first OPERATIONAL sample at {operational}; control rows {trial['control_rows']} (expected {n})")
            print("  " + ", ".join(f"{name} {tally[name]}" for name in CLASSES))
            for run in runs(trial["samples"]):
                print(f"    {describe_run(run)}")
    client.close()

    valid = [trial for trial in results if trial["valid"]]
    total = dict.fromkeys(CLASSES, 0)
    trials_with = dict.fromkeys(CLASSES, 0)
    for trial in valid:
        for name, value in counts(trial["samples"]).items():
            total[name] += value
            trials_with[name] += 1 if value else 0
    print()
    print(f"Totals over {len(valid)} valid of {trials} trials (samples / trials with at least one):")
    for name in CLASSES:
        print(f"  {name:<15} {total[name]:>6} / {trials_with[name]}")
    print("The status and the query are read one after the other, so a sample can straddle a change of status.")
    if len(valid) < trials:
        return 2
    return 1 if total["uc_fewer"] or total["uc_error"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
