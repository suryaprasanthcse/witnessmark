#!/usr/bin/env python3
"""C0: one `cognify` call over documents that share entities stores duplicate LanceDB ids (blueprint findings 1, C14, C17).

Issue it bears on: topoteretes/cognee#5254 (duplicate vector ids), although no second process is involved.

What it does, in order, each case in a fresh process on a fresh store (Ladybug graph, LanceDB vectors, SQLite):

1. CONTROL: add 8 documents that share people, companies and cities, then `cognify(data_per_batch=1)`.
   EXPECTED: no id has two rows in any LanceDB table (`EntityType_name`, `Entity_name`,
   `EdgeType_relationship_name`).
2. CASE: the same 8 documents and Cognee's default, `cognify()` with `data_per_batch=20`.
   EXPECTED (the same as the control): no duplicate id. OBSERVED so far: duplicate ids in `EntityType_name`
   and `Entity_name`, and sometimes in `EdgeType_relationship_name`.

Exit 0 if the behaviour reproduces (the control is clean and the default run has duplicate ids in both
`EntityType_name` and `Entity_name`), 1 if it does not. Nothing races: one process, one call. The measured
runs are in the blueprint's section 12, finding 1 (`20261114T131142Z-daa65b09`, `20261114T181918Z-b9974e3e`,
`20261114T131148Z-0fb02db6`), with the stale-handle trace that [code] and [measured] explain it: the default
processes up to 20 data items at once, and `create_data_points` opens the table before it takes the lock, so a
merge can run on a handle that does not yet see what an earlier merge committed (C14).

Pins. cognee 1.6.8 (tag 069f3cc119bdf5628be054bb915992b2fc78cfc5), Ladybug 0.22.3, LanceDB 0.39.0: venv built
from targets/02-cognee/requirements/v1.6.8.txt. Access control at its default (on), graph and vector subprocess
workers on (the defaults), SQLite.

Run from the repo root (no database server is needed):

    .state/venvs/cognee-v1.6.8/Scripts/python.exe targets/02-cognee/repros/repro_c0_single_call_duplicates.py [--root DIR]

Needs only the standard library, cognee and the packages installed with it (lancedb). No network: it serves its
own OpenAI-compatible endpoint on 127.0.0.1, refuses every non-loopback connection, and sets
TELEMETRY_DISABLED=1. The stores go under `--root` (default: a new folder under .state/scratch).

Credit. #5254's reporter described the duplicate ids and asked for tests of concurrent writers; this repro shows
that the default `data_per_batch` produces them even without a second process.
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
TABLES = ("EntityType_name", "Entity_name", "EdgeType_relationship_name")
TOKENIZER = "9b5ad71b2ce5302211f9c61530b329a4922fc6a4"
TOKENIZER_HASH = "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7"
DIMENSIONS = 256


def fresh_root(root, prefix):
    temp = SCRATCH / "tmp"
    temp.mkdir(parents=True, exist_ok=True)
    os.environ.update(TEMP=str(temp), TMP=str(temp), TMPDIR=str(temp))
    if root is None:
        return Path(tempfile.mkdtemp(prefix=prefix, dir=SCRATCH))
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=root))


def prepare_tokenizer(root):
    # LiteLLM's Windows wheel can contain CRLF where tiktoken expects LF.
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


def duplicate_ids(store):
    import lancedb  # installed with Cognee

    stores = list((store / "system").rglob("*.lance.db"))
    if len(stores) != 1:
        raise RuntimeError(f"Expected one LanceDB store, found {len(stores)}")
    database = lancedb.connect(str(stores[0]))
    duplicates = {}
    for name in TABLES:
        ids = database.open_table(name).to_arrow().column("id").to_pylist()
        if not ids:
            raise RuntimeError(f"No vector rows in {name}")
        duplicates[name] = sum(count > 1 for count in Counter(ids).values())
    return duplicates


async def cognify(store, endpoint, cache, mode):
    configure(store, endpoint, cache)
    os.environ.update(
        GRAPH_DATABASE_PROVIDER="ladybug",
        GRAPH_DATABASE_SUBPROCESS_ENABLED="true",
        VECTOR_DB_PROVIDER="lancedb",
        VECTOR_DB_SUBPROCESS_ENABLED="true",
        ENABLE_BACKEND_ACCESS_CONTROL="true",
    )
    import cognee
    from cognee.modules.engine.operations.setup import setup

    await setup()
    await cognee.add([document(i) for i in range(8)], dataset_name="duplicates")
    kwargs = {"data_per_batch": 1} if mode == "control" else {}
    await cognee.cognify(datasets=["duplicates"], **kwargs)
    return duplicate_ids(store)


def run_case(ctx, root, endpoint, mode):
    # Each case gets a fresh Cognee process and store, including the engine caches.
    receive, send = ctx.Pipe(duplex=False)
    process = ctx.Process(target=run_worker, args=(send, root / mode, endpoint, root / "tiktoken", mode))
    with receive, send:
        process.start()
        send.close()
        process.join()
        if process.exitcode:
            raise RuntimeError(f"{mode} worker exited with code {process.exitcode}")
        return receive.recv()


def run_worker(send, store, endpoint, cache, mode):
    with send:
        send.send(asyncio.run(cognify(store, endpoint, cache, mode)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="Parent directory for the fresh stores")
    args = parser.parse_args()
    root = fresh_root(args.root, "repro-c0-")
    prepare_tokenizer(root)
    ctx = multiprocessing.get_context("spawn")
    with model_server() as endpoint:
        control = run_case(ctx, root, endpoint, "control")
        print(f"CONTROL data_per_batch=1 | EXPECTED zero duplicate ids | OBSERVED {control}", flush=True)
        case = run_case(ctx, root, endpoint, "default")
        print(f"CASE default (data_per_batch=20) | EXPECTED zero duplicate ids | OBSERVED {case}", flush=True)
    control_clean = not any(control.values())
    reproduced = bool(case["EntityType_name"] and case["Entity_name"])
    print(f"REPRODUCED: {control_clean and reproduced} (control clean: {control_clean}; duplicate ids in both "
          f"EntityType_name and Entity_name on the default path: {reproduced}; the counts vary from run to run)",
          flush=True)
    return 0 if control_clean and reproduced else 1


if __name__ == "__main__":
    sys.exit(main())
