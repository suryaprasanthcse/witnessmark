#!/usr/bin/env python3
"""R2: several processes cognify one dataset on a shared LanceDB store (blueprint findings 3 and 4, C14, C26).

Issue it bears on: topoteretes/cognee#5254 (cross-process LanceDB writers). It also exercises #4167's gap
(the per-dataset pipeline lock is process-local) but does not test either pull request.

What it does, in order:

1. CONTROL: one process adds 24 documents that share entities and runs `cognify(data_per_batch=1)`.
   EXPECTED: no error and no duplicate vector id.
2. CASE: `--trials` times, on a fresh store and an emptied Neo4j graph, 4 processes (spawn) each add an
   overlapping slice of the same 24 documents to ONE dataset and run `cognify(data_per_batch=1)` after a
   barrier. EXPECTED: every call returns without error, and no vector id has two rows.
   Counted per trial: calls that raised `AfterRunHookError` / "Retryable commit conflict" (the pipeline
   finished and stored its data, then LanceDB's post-run compaction lost a commit race), calls that raised
   "Too many concurrent writers" (#5254's symptom), other errors, and duplicate vector ids per table.

Exit 0 if the behaviour reproduces (the control is clean and at least one trial shows a post-run error or a
duplicate id), 1 if it does not. The race is timing dependent: a trial can come out clean, so the exit code
depends on all trials. The measured rates in the batch are in the blueprint's section 12 (runs
20261114T204652Z-d5f2e1c9, 20261114T133423Z-70f45910 and 20261114T214705Z-8a40b975).

Pins. cognee 1.6.8 (tag 069f3cc119bdf5628be054bb915992b2fc78cfc5), LanceDB 0.39.0, `neo4j` driver 5.28.8:
venv built from targets/02-cognee/requirements/v1.6.8.txt. Neo4j 5.26.2 with APOC (the compose file in
baselines/ pins the image digest and enables APOC) on bolt://127.0.0.1:17687, no authentication.
ENABLE_BACKEND_ACCESS_CONTROL=false, so every dataset shares one LanceDB store (blueprint C12).

Run from the repo root, with the baselines up (`docker compose -f baselines/docker-compose.yml up -d`):

    .state/venvs/cognee-v1.6.8/Scripts/python.exe targets/02-cognee/repros/repro_r2_lancedb_multiprocess.py [--trials 3] [--root DIR]

Needs only the standard library, cognee and the packages installed with it (lancedb, neo4j). No network: it
serves its own OpenAI-compatible endpoint on 127.0.0.1, refuses every non-loopback connection, and sets
TELEMETRY_DISABLED=1. The script EMPTIES the Neo4j graph before each phase and when it ends; use disposable
baselines only.

Credit. #5254's reporter found the cross-process writer problem and asked for tests that cover it; this
script is such a test. The Cognee team's `AfterRunHookError` wrapper is what makes the stored data visible
in the error text.
"""

import argparse
import asyncio
import hashlib
import json
import multiprocessing
import os
import re
import socket
import sys
import tempfile
import threading
from collections import Counter
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.util import find_spec
from pathlib import Path

SCRATCH = Path(__file__).resolve().parents[3] / ".state" / "scratch"
NEO4J = "bolt://127.0.0.1:17687"
TABLES = ("DocumentChunk_text", "EdgeType_relationship_name", "EntityType_name", "Entity_name",
          "TextDocument_name", "TextSummary_text")
TOKENIZER = "9b5ad71b2ce5302211f9c61530b329a4922fc6a4"
TOKENIZER_HASH = "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7"
DIMENSIONS = 256
DOCUMENTS = 24
WORKERS = 4
DATASET = "repro_r2"


def fresh_root(root, prefix):
    temp = SCRATCH / "tmp"
    temp.mkdir(parents=True, exist_ok=True)
    os.environ.update(TEMP=str(temp), TMP=str(temp), TMPDIR=str(temp))
    if root is None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(prefix=prefix, dir=SCRATCH))
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=root))


def prepare_tokenizer(root):
    # LiteLLM's Windows wheel can contain CRLF where tiktoken expects LF, so tiktoken would delete the file
    # and download a fresh copy. Keep an LF copy that matches tiktoken's hash instead.
    cache = root / "tiktoken"
    cache.mkdir()
    bundled = Path(find_spec("litellm").origin).parent / "litellm_core_utils" / "tokenizers"
    data = (bundled / TOKENIZER).read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(data).hexdigest() != TOKENIZER_HASH:
        raise RuntimeError("Unexpected hash for the bundled cl100k_base tokenizer")
    (cache / TOKENIZER).write_bytes(data)


def loopback_only():
    def check(host):
        if isinstance(host, bytes):
            host = host.decode()
        if host not in (None, "127.0.0.1", "::1", "localhost"):
            raise OSError(f"Only loopback connections are allowed (requested {host!r})")

    connect, connect_ex, getaddrinfo = socket.socket.connect, socket.socket.connect_ex, socket.getaddrinfo

    def guarded_connect(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            check(address[0])
        return connect(sock, address)

    def guarded_connect_ex(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            check(address[0])
        return connect_ex(sock, address)

    def guarded_getaddrinfo(host, *args, **kwargs):
        check(host)
        return getaddrinfo(host, *args, **kwargs)

    socket.socket.connect = guarded_connect
    socket.socket.connect_ex = guarded_connect_ex
    socket.getaddrinfo = guarded_getaddrinfo


def configure(store, endpoint, cache):
    os.environ.update(
        TELEMETRY_DISABLED="1",
        LITELLM_LOCAL_MODEL_COST_MAP="True",
        LITELLM_LOG="ERROR",
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        COGNEE_LOG_FILE="false",
        NO_PROXY="127.0.0.1,localhost",
        LLM_PROVIDER="openai",
        LLM_ENDPOINT=endpoint,
        LLM_MODEL="openai/repro-stub",
        LLM_API_KEY="local-test-key",
        EMBEDDING_PROVIDER="openai_compatible",
        EMBEDDING_ENDPOINT=endpoint,
        EMBEDDING_MODEL="repro-embed",
        EMBEDDING_DIMENSIONS=str(DIMENSIONS),
        SYSTEM_ROOT_DIRECTORY=str(store / "system"),
        DATA_ROOT_DIRECTORY=str(store / "data"),
        TIKTOKEN_CACHE_DIR=str(cache),
        CUSTOM_TIKTOKEN_CACHE_DIR=str(cache),
        DB_PROVIDER="sqlite",
        GRAPH_DATABASE_PROVIDER="neo4j",
        GRAPH_DATABASE_URL=NEO4J,
        GRAPH_DATABASE_USERNAME="neo4j",
        GRAPH_DATABASE_PASSWORD="unused",
        VECTOR_DB_PROVIDER="lancedb",
        ENABLE_BACKEND_ACCESS_CONTROL="false",
    )
    loopback_only()


def text(body, role):
    parts = []
    for message in body["messages"]:
        if message["role"] == role:
            content = message["content"]
            parts.extend([content] if isinstance(content, str) else
                         [part.get("text", "") for part in content])
    return "\n".join(parts)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        model = body["model"]
        if self.path == "/v1/embeddings":
            inputs = body["input"]
            inputs = [inputs] if isinstance(inputs, str) else inputs
            rows = []
            for index, value in enumerate(inputs):
                digest = hashlib.sha256(value.encode()).digest()
                vector = [(byte - 128) / 128 for byte in digest] * (DIMENSIONS // len(digest))
                rows.append({"object": "embedding", "index": index, "embedding": vector})
            self.send_json(200, {"object": "list", "model": model, "data": rows})
        elif self.path == "/v1/chat/completions":
            system = text(body, "system")
            schema = (body.get("response_format") or {}).get("json_schema", {}).get("schema", {})
            if 'Respond to me with the following string: "test"' in system:
                answer = "test"
            elif schema.get("title") == "KnowledgeGraph" or '"KnowledgeGraph"' in system:
                answer = json.dumps(extract(text(body, "user")))
            elif schema.get("title") == "SummarizedContent" or '"SummarizedContent"' in system:
                answer = json.dumps({"summary": "A short fixture document."})
            else:
                self.send_json(400, {"error": {"message": "Unexpected chat prompt"}})
                return
            self.send_json(200, {
                "id": "chatcmpl-local", "object": "chat.completion", "created": 0, "model": model,
                "choices": [{"index": 0, "finish_reason": "stop",
                             "message": {"role": "assistant", "content": answer}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            })
        else:
            self.send_json(404, {"error": {"message": "Unexpected endpoint"}})

    def send_json(self, status, payload):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


@contextmanager
def model_server():
    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}/v1"
        finally:
            server.shutdown()
            thread.join()


PEOPLE = ("Alice Moreau", "Bilal Okafor", "Chen Wei", "Dana Petrov", "Elif Kaya", "Farid Haddad")
COMPANIES = (("Acme Robotics", "Lyon"), ("Borealis Foods", "Oslo"),
             ("Cobalt Analytics", "Porto"), ("Delta Freight", "Gdansk"))


def employment(index):
    person = PEOPLE[index % len(PEOPLE)]
    company, city = COMPANIES[index % len(COMPANIES)]
    return person, company, city


def document(index):
    person, company, city = employment(index)
    return f"{person} works at {company}, which is based in {city}. [record:{index}]"


def extract(prompt):
    nodes, edges = {}, []
    for match in dict.fromkeys(re.findall(r"\[record:(\d+)\]", prompt)):
        person, company, city = employment(int(match))
        for name, kind in ((person, "Person"), (company, "Organization"), (city, "City")):
            nodes[name] = {"id": name, "name": name, "type": kind, "description": f"{kind} {name}"}
        for source, relation, target in ((person, "works_at", company), (company, "based_in", city)):
            edges.append({"source_node_id": source, "target_node_id": target, "relationship_name": relation,
                          "description": f"{source} {relation.replace('_', ' ')} {target}"})
    if not nodes:
        raise ValueError("No fixture record in KnowledgeGraph prompt")
    return {"nodes": list(nodes.values()), "edges": edges}


def slices():
    """Worker i adds slice i and the first two documents of slice i+1, so neighbours overlap."""
    size = DOCUMENTS // WORKERS
    out = []
    for i in range(WORKERS):
        own = list(range(i * size, (i + 1) * size))
        nxt = [(j % DOCUMENTS) for j in range((i + 1) * size, (i + 1) * size + 2)]
        out.append(own + nxt)
    return out


def empty_neo4j():
    from neo4j import GraphDatabase  # installed with the neo4j extra

    with GraphDatabase.driver(NEO4J, auth=("neo4j", "unused")) as driver:
        driver.execute_query("MATCH (n) DETACH DELETE n")
        count = driver.execute_query("MATCH (n) RETURN count(n) AS c").records[0]["c"]
    if count:
        raise RuntimeError(f"Neo4j still holds {count} nodes after the delete")


def error_text(exc):
    parts, seen = [], set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        parts.append(f"{type(exc).__name__}: {exc}")
        exc = exc.__cause__ or exc.__context__
    return " <- ".join(parts)[:1500]


def duplicate_ids(store):
    import lancedb  # installed with Cognee

    found = [p for p in (store / "system").rglob("*.lancedb") if p.is_dir()]
    if len(found) != 1:
        raise RuntimeError(f"Expected one shared LanceDB store, found {len(found)}")
    database = lancedb.connect(str(found[0]))
    duplicates = {}
    for name in TABLES:
        ids = database.open_table(name).to_arrow().column("id").to_pylist()
        if not ids:
            raise RuntimeError(f"No vector rows in {name}")
        duplicates[name] = sum(count > 1 for count in Counter(ids).values())
    return duplicates


async def prepare(store, endpoint, cache):
    configure(store, endpoint, cache)
    import cognee  # noqa: F401  (the environment is set before this import)
    from cognee.modules.engine.operations.setup import setup

    await setup()


async def ingest(store, endpoint, cache, documents, barrier):
    configure(store, endpoint, cache)
    import cognee

    if barrier is not None:
        barrier.wait(120)
    try:
        await cognee.add([document(i) for i in documents], dataset_name=DATASET)
        await cognee.cognify(datasets=[DATASET], data_per_batch=1)
    except Exception as exc:  # noqa: BLE001 - the error text is the measurement
        return error_text(exc)
    return None


def worker(send, kind, store, endpoint, cache, documents, barrier):
    with send:
        if kind == "prepare":
            asyncio.run(prepare(store, endpoint, cache))
            send.send(None)
        else:
            send.send(asyncio.run(ingest(store, endpoint, cache, documents, barrier)))


def run_processes(ctx, store, endpoint, cache, jobs):
    """Start one spawned process per job; return the error text (or None) each one reported."""
    barrier = ctx.Barrier(len(jobs)) if len(jobs) > 1 else None
    pipes, processes = [], []
    for kind, documents in jobs:
        receive, send = ctx.Pipe(duplex=False)
        process = ctx.Process(target=worker, args=(send, kind, store, endpoint, cache, documents, barrier))
        process.start()
        send.close()
        pipes.append(receive)
        processes.append(process)
    results = []
    for process, receive in zip(processes, pipes):
        results.append(receive.recv() if receive.poll(1800) else "no answer within 1800 s")
        process.join()
        if process.exitcode:
            results[-1] = results[-1] or f"worker exited with code {process.exitcode}"
    return results


def classify(errors):
    hook = sum(1 for e in errors if e and ("AfterRunHookError" in e or "Retryable commit conflict" in e))
    writers = sum(1 for e in errors if e and "Too many concurrent writers" in e)
    other = sum(1 for e in errors if e and "AfterRunHookError" not in e and "Retryable commit conflict" not in e
                and "Too many concurrent writers" not in e)
    return {"post_run_hook_errors": hook, "too_many_writers": writers, "other_errors": other}


def new_store(ctx, root, endpoint, cache, label):
    empty_neo4j()
    store = Path(tempfile.mkdtemp(prefix=f"{label}-", dir=root))
    run_processes(ctx, store, endpoint, cache, [("prepare", None)])
    return store


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=Path, help="Parent directory for the fresh stores (default .state/scratch)")
    parser.add_argument("--trials", type=int, default=3, help="Number of multi-process trials (default 3)")
    args = parser.parse_args()
    loopback_only()
    root = fresh_root(args.root, "repro-r2-")
    prepare_tokenizer(root)
    cache = root / "tiktoken"
    ctx = multiprocessing.get_context("spawn")
    try:
        with model_server() as endpoint:
            store = new_store(ctx, root, endpoint, cache, "control")
            control_errors = run_processes(ctx, store, endpoint, cache, [("ingest", list(range(DOCUMENTS)))])
            control = {"errors": [e for e in control_errors if e], "duplicate_ids": duplicate_ids(store)}
            control_clean = not control["errors"] and not any(control["duplicate_ids"].values())
            print(f"CONTROL, 1 process, data_per_batch=1 | EXPECTED no error, no duplicate id | OBSERVED {control}",
                  flush=True)
            reproduced = False
            for trial in range(1, args.trials + 1):
                store = new_store(ctx, root, endpoint, cache, f"trial{trial}")
                errors = run_processes(ctx, store, endpoint, cache, [("ingest", s) for s in slices()])
                counts = classify(errors)
                dups = duplicate_ids(store)
                seen = bool(counts["post_run_hook_errors"] or counts["too_many_writers"] or any(dups.values()))
                reproduced |= seen
                print(f"CASE trial {trial}, {WORKERS} processes, one dataset | EXPECTED 0 errors and 0 duplicate ids | "
                      f"OBSERVED {counts} duplicate_ids={dups}", flush=True)
                first = next((e for e in errors if e), None)
                if first:
                    print(f"  first error: {first[:600]}", flush=True)
    finally:
        empty_neo4j()
    print(f"REPRODUCED: {control_clean and reproduced} (control clean: {control_clean}; "
          f"a trial showed a post-run error or a duplicate id: {reproduced})", flush=True)
    return 0 if control_clean and reproduced else 1


if __name__ == "__main__":
    sys.exit(main())
