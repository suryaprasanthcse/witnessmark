#!/usr/bin/env python3
"""R3: three behaviours of cognee 1.6.1 with the community FalkorDB hybrid adapter (blueprint C24, C27, C28).

    repro_r3_falkor_adapter.py c24 | c27 | c28 | all

Each sub-case runs a control first, then the case, and prints EXPECTED next to OBSERVED. Exit 0 if every
selected sub-case reproduces (its control behaves and its case shows the behaviour), 1 if any does not.

  c24  The adapter's vector client ignores `VECTOR_DB_PORT` (finding 7; candidate issue for
       topoteretes/cognee-community). Control: the graph client on the same settings dials the configured
       port. Case: the vector client dials 6379. No shim is installed for this sub-case.
  c27  `datasets.delete_data` on cognee 1.6.1 + the adapter (finding 5; candidate issues for
       topoteretes/cognee and cognee-community).
       (a) deleting a document that was added but never cognified raises DocumentSubgraphNotFoundError.
           Control: the same delete after cognify succeeds.
       (b) after deleting a cognified document, an edge between two entities that another document still
           references stays in the graph. Control: before the delete, the graph is exactly the fixture's.
  c28  FalkorDB 6.0.4 truncates every result set at RESULTSET_SIZE (default 10000), and the adapter's
       `get_graph_data` reads all nodes in one query, so it silently returns 10000 of 10500 nodes (finding 6).
       Control: a 9000-node graph comes back whole.

c27 and c28 install the port shim that is the only sanctioned workaround for c24 (it copies `vector_db_port`
into `graph_database_port` and changes nothing else), because the vector client would otherwise not connect.

Pins. cognee 1.6.1 (tag eb90d03), cognee-community-hybrid-adapter-falkor 0.4.1 from git ff1324ec7586de8299e4a21fc777c021476af3f4,
falkordb client 1.8.2: venv built from targets/02-cognee/requirements/v1.6.1-falkor.txt. FalkorDB 6.0.4 on
127.0.0.1:16380 (the compose file in baselines/ pins the image digest). ENABLE_BACKEND_ACCESS_CONTROL=false.

Run from the repo root, with the baselines up (`docker compose -f baselines/docker-compose.yml up -d`):

    .state/venvs/cognee-v1.6.1-falkor/Scripts/python.exe targets/02-cognee/repros/repro_r3_falkor_adapter.py all [--root DIR]

Needs only the standard library, cognee and the packages installed with the adapter. No network: it serves its
own OpenAI-compatible endpoint on 127.0.0.1 (the 1.6.1 pipeline also asks for a per-chunk summary, which it
answers), refuses every non-loopback connection, and sets TELEMETRY_DISABLED=1. c24 and c27 EMPTY the Cognee
graph in FalkorDB first (`prune_system`); c28 creates two dedicated graphs and deletes only those. Use
disposable baselines only.

Credit. The adapter is the community's; the shim and the checks here only describe how it behaves with a
non-default port, a delete of an uncognified document, and a result larger than FalkorDB's default limit.
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
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.util import find_spec
from pathlib import Path

SCRATCH = Path(__file__).resolve().parents[3] / ".state" / "scratch"
FALKOR_PORT = 16380
TOKENIZER = "9b5ad71b2ce5302211f9c61530b329a4922fc6a4"
TOKENIZER_HASH = "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7"
DIMENSIONS = 256


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
        GRAPH_DATABASE_PROVIDER="falkor",
        GRAPH_DATABASE_URL="127.0.0.1",
        GRAPH_DATABASE_PORT=str(FALKOR_PORT),
        VECTOR_DB_PROVIDER="falkor",
        VECTOR_DB_URL="127.0.0.1",
        VECTOR_DB_PORT=str(FALKOR_PORT),
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


# The fixture: record 1 says Alice works at Acme; record 2 names the same two entities with no relation.
RECORDS = {
    1: ("Alice Moreau works at Acme Robotics. [record:1]", True),
    2: ("Alice Moreau is a person and Acme Robotics is a company. [record:2]", False),
    3: ("Bilal Okafor works at Borealis Foods. [record:3]", True),
}


def extract(prompt):
    nodes, edges = {}, []
    for match in dict.fromkeys(re.findall(r"\[record:(\d+)\]", prompt)):
        index = int(match)
        if index == 3:
            people = (("Bilal Okafor", "Person"), ("Borealis Foods", "Organization"))
        else:
            people = (("Alice Moreau", "Person"), ("Acme Robotics", "Organization"))
        for name, kind in people:
            nodes[name] = {"id": name, "name": name, "type": kind, "description": f"{kind} {name}"}
        if RECORDS[index][1]:
            edges.append({"source_node_id": people[0][0], "target_node_id": people[1][0],
                          "relationship_name": "works_at",
                          "description": f"{people[0][0]} works at {people[1][0]}"})
    if not nodes:
        raise ValueError("No fixture record in KnowledgeGraph prompt")
    return {"nodes": list(nodes.values()), "edges": edges}


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


def error_text(exc):
    parts, seen = [], set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        parts.append(f"{type(exc).__name__}: {exc}")
        exc = exc.__cause__ or exc.__context__
    return " <- ".join(parts)[:700]


def install_port_shim():
    """The community adapter's vector client reads only graph_database_port (c24); copy vector_db_port into it."""
    from cognee.infrastructure.databases.vector import use_vector_adapter
    from cognee_community_hybrid_adapter_falkor.falkor_adapter import FalkorDBAdapter

    def falkor_vector(**kwargs):
        port = kwargs.pop("vector_db_port", None)
        if port:
            kwargs["graph_database_port"] = int(port)
        return FalkorDBAdapter(**kwargs)

    use_vector_adapter("falkor", falkor_vector)


def port_of(driver):
    try:
        return driver.connection.connection_pool.connection_kwargs["port"]
    except Exception:  # noqa: BLE001 - only used to print
        return "unknown"


# --- c24 -----------------------------------------------------------------------------------------------------


async def case_c24(store, endpoint, cache):
    configure(store, endpoint, cache)
    import cognee  # noqa: F401  (the environment is set before this import)
    import cognee_community_hybrid_adapter_falkor.register  # noqa: F401  (registers the "falkor" adapters)
    from cognee.infrastructure.databases.graph import get_graph_engine
    from cognee.infrastructure.databases.vector import get_vector_engine

    graph = await get_graph_engine()
    try:
        graphs = graph.driver.list_graphs()
        control = f"graph client port {port_of(graph.driver)}, list_graphs() answered ({len(graphs)} graphs)"
        control_ok = str(port_of(graph.driver)) == str(FALKOR_PORT)
    except Exception as exc:  # noqa: BLE001
        control, control_ok = f"graph client failed: {error_text(exc)}", False
    print(f"c24 CONTROL | EXPECTED graph client on port {FALKOR_PORT} answers | OBSERVED {control}", flush=True)
    stage, port = "get_vector_engine()", "unknown"
    try:
        vector = get_vector_engine()
        stage = "vector.driver.list_graphs()"
        port = port_of(vector.driver)
        vector.driver.list_graphs()
        observed, reproduced = f"vector client port {port}, list_graphs() answered", False
    except Exception as exc:  # noqa: BLE001 - the refusal is the observation
        text = error_text(exc)
        observed = f"vector client port {port}; {stage} raised {text}"
        reproduced = "127.0.0.1:6379" in text
    print(f"c24 CASE | EXPECTED vector client on port {FALKOR_PORT} answers (VECTOR_DB_PORT={FALKOR_PORT}) | "
          f"OBSERVED {observed}", flush=True)
    return control_ok and reproduced


# --- c27 -----------------------------------------------------------------------------------------------------


async def lookup(name):
    from cognee.infrastructure.databases.relational import get_relational_engine
    from cognee.modules.data.models import Data, Dataset
    from cognee.modules.users.methods import get_default_user
    from sqlalchemy import select

    user = await get_default_user()
    async with get_relational_engine().get_async_session() as session:
        dataset = (await session.scalars(select(Dataset).where(Dataset.name == name,
                                                               Dataset.owner_id == user.id))).first()
        rows = list((await session.scalars(select(Data).where(Data.dataset_id == dataset.id))).all())
    return user, dataset, rows


def stored_text(row):
    """The text of a stored document; Cognee writes its locations as file:///C:/... on Windows."""
    from urllib.parse import urlparse
    from urllib.request import url2pathname

    location = row.raw_data_location
    path = url2pathname(urlparse(location).path) if location.startswith("file:") else location
    return Path(path).read_text(encoding="utf-8", errors="replace")


async def entity_graph():
    """(Entity nodes, edges between two Entity nodes), read from the adapter."""
    from cognee.infrastructure.databases.graph import get_graph_engine

    graph = await get_graph_engine()
    nodes = (await graph.query("MATCH (n) WHERE n.type = 'Entity' RETURN count(n)")).result_set[0][0]
    edges = (await graph.query("MATCH (a)-[r]->(b) WHERE a.type = 'Entity' AND b.type = 'Entity' "
                               "RETURN count(r)")).result_set[0][0]
    return nodes, edges


async def case_c27(store, endpoint, cache):
    configure(store, endpoint, cache)
    import cognee
    import cognee_community_hybrid_adapter_falkor.register  # noqa: F401
    from cognee.modules.engine.operations.setup import setup

    install_port_shim()
    await setup()
    await cognee.prune.prune_system(graph=True, vector=True, metadata=False, cache=False)

    async def delete_all(name):
        user, dataset, rows = await lookup(name)
        for row in rows:
            await cognee.datasets.delete_data(dataset_id=dataset.id, data_id=row.id, user=user)

    # (a) delete of a document that was never cognified, with its control
    await cognee.add([RECORDS[3][0]], dataset_name="c27a_control")
    await cognee.cognify(datasets=["c27a_control"], data_per_batch=1)
    try:
        await delete_all("c27a_control")
        control_a, control_a_ok = "no error", True
    except Exception as exc:  # noqa: BLE001
        control_a, control_a_ok = error_text(exc), False
    print(f"c27a CONTROL, cognified document | EXPECTED delete returns without error | OBSERVED {control_a}",
          flush=True)
    await cognee.add([RECORDS[1][0]], dataset_name="c27a")
    try:
        await delete_all("c27a")
        case_a, reproduced_a = "no error", False
    except Exception as exc:  # noqa: BLE001
        case_a, reproduced_a = error_text(exc), "DocumentSubgraphNotFoundError" in error_text(exc)
    print(f"c27a CASE, added but never cognified | EXPECTED delete returns without error | OBSERVED {case_a}",
          flush=True)

    # (b) an edge between two entities that another document still references
    await cognee.prune.prune_system(graph=True, vector=True, metadata=False, cache=False)
    await cognee.add([RECORDS[1][0], RECORDS[2][0]], dataset_name="c27b")
    await cognee.cognify(datasets=["c27b"], data_per_batch=1)
    before = await entity_graph()
    print(f"c27b CONTROL, before the delete | EXPECTED 2 Entity nodes and 1 edge between them (the fixture) | "
          f"OBSERVED {before[0]} Entity nodes, {before[1]} edge(s)", flush=True)
    control_b_ok = before == (2, 1)
    user, dataset, rows = await lookup("c27b")
    target = next(row for row in rows if "[record:1]" in stored_text(row))
    await cognee.datasets.delete_data(dataset_id=dataset.id, data_id=target.id, user=user)
    after = await entity_graph()
    print(f"c27b CASE, after deleting record 1 (record 2 still names both entities) | EXPECTED 2 Entity nodes and "
          f"0 edges (the edge belonged to record 1 only) | OBSERVED {after[0]} Entity nodes, {after[1]} edge(s)",
          flush=True)
    reproduced_b = after == (2, 1)
    return control_a_ok and reproduced_a and control_b_ok and reproduced_b


# --- c28 -----------------------------------------------------------------------------------------------------


async def case_c28(store, endpoint, cache):
    configure(store, endpoint, cache)
    import cognee  # noqa: F401
    from cognee_community_hybrid_adapter_falkor.falkor_adapter import FalkorDBAdapter
    from falkordb import FalkorDB

    client = FalkorDB(host="127.0.0.1", port=FALKOR_PORT)
    limit = client.connection.execute_command("GRAPH.CONFIG", "GET", "RESULTSET_SIZE")
    print(f"c28 GRAPH.CONFIG GET RESULTSET_SIZE -> {limit}", flush=True)
    names = {"small": "witnessmark_repro_c28_small", "big": "witnessmark_repro_c28_big"}
    sizes = {"small": 9000, "big": 10500}
    results = {}
    try:
        for key, name in names.items():
            graph = client.select_graph(name)
            graph.query("UNWIND range(1, $n) AS i CREATE (:Probe {id: toString(i), type: 'Probe', "
                        "name: 'n' + toString(i)})", {"n": sizes[key]})
            held = graph.query("MATCH (n) RETURN count(n)").result_set[0][0]
            adapter = FalkorDBAdapter(graph_database_url="127.0.0.1", graph_database_port=FALKOR_PORT,
                                      database_name=name)
            nodes, _edges = await adapter.get_graph_data()
            results[key] = (held, len(nodes))
    finally:
        for name in names.values():
            try:
                client.select_graph(name).delete()
            except Exception:  # noqa: BLE001 - the graph may not exist if creation failed
                pass
    small, big = results["small"], results["big"]
    print(f"c28 CONTROL, {sizes['small']} nodes | EXPECTED get_graph_data returns all {sizes['small']} | "
          f"OBSERVED FalkorDB holds {small[0]}, get_graph_data returned {small[1]}", flush=True)
    print(f"c28 CASE, {sizes['big']} nodes | EXPECTED get_graph_data returns all {sizes['big']} | "
          f"OBSERVED FalkorDB holds {big[0]}, get_graph_data returned {big[1]}", flush=True)
    return small[0] == small[1] == sizes["small"] and big[0] == sizes["big"] and big[1] == 10000


CASES = {"c24": case_c24, "c27": case_c27, "c28": case_c28}


def worker(send, name, store, endpoint, cache):
    with send:
        try:
            send.send(asyncio.run(CASES[name](store, endpoint, cache)))
        except Exception as exc:  # noqa: BLE001
            print(f"{name} ERROR {error_text(exc)}", flush=True)
            send.send(False)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("case", choices=["c24", "c27", "c28", "all"])
    parser.add_argument("--root", type=Path, help="Parent directory for the fresh stores (default .state/scratch)")
    args = parser.parse_args()
    loopback_only()
    root = fresh_root(args.root, "repro-r3-")
    prepare_tokenizer(root)
    cache = root / "tiktoken"
    ctx = multiprocessing.get_context("spawn")
    selected = ["c24", "c27", "c28"] if args.case == "all" else [args.case]
    verdicts = {}
    with model_server() as endpoint:
        for name in selected:
            # A fresh process per sub-case: Cognee caches its engines and reads its settings once.
            store = Path(tempfile.mkdtemp(prefix=f"{name}-", dir=root))
            receive, send = ctx.Pipe(duplex=False)
            process = ctx.Process(target=worker, args=(send, name, store, endpoint, cache))
            process.start()
            send.close()
            verdicts[name] = bool(receive.recv()) if receive.poll(1800) else False
            process.join()
            print(f"{name} REPRODUCED: {verdicts[name]}", flush=True)
    return 0 if all(verdicts.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
