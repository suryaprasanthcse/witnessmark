"""M4 cost, failover-boundary, and cross-process visibility runs.

Only disposable ``wm-*`` containers are controlled here.  Every command is
written so the batch driver can give it a timeout and retain its stdout, exit
status, and evidence independently.
"""

from __future__ import annotations

import json
import math
import os
import re
import statistics
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from witnessmark import env as witnessmark_env
from witnessmark.adapters import make_engine

from .client import OmnigraphClient, OperationResult, Outcome
from .runner_scenarios import SKILL, TASK
from .workload import load_queries

SIZES = (32_000, 128_000, 512_000)
SIBLINGS = (0, 4, 16, 64)
WARMUPS = 3
REPETITIONS = 5
# O4 shortens the S3 cluster lease so a paused owner can be replaced within the test.
# Everything else runs on the documented default: an owner stops every storage write
# once no heartbeat is answered for two thirds of a lease (storage-failures.md), and
# a 2 s lease closed admission under load in O1 (batch m4c, proxy run).
LEASE_SECONDS = 2
DEFAULT_LEASE_SECONDS = 30
MINIO_IMAGE = "witnessmark/minio:RELEASE.2025-09-07T16-13-09Z"
MINIO_DIGEST = "sha256:5c9f6e9b19cdd3c333900e5102b196bfdb2e19f3e25674bfa0cef924e67dc899"


def _utc() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _run_id(started: datetime) -> str:
    return started.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * p / 100
    low, high = math.floor(position), math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _summary(values: list[float]) -> dict:
    return {
        "n": len(values),
        "median": statistics.median(values) if values else None,
        "q1": _percentile(values, 25),
        "q3": _percentile(values, 75),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
    }


def _check(result: OperationResult, action: str) -> OperationResult:
    if result.outcome is not Outcome.OK:
        raise RuntimeError(f"{action}: {result.outcome.value} {result.kind}: {result.message}")
    return result


def _command(args: list[str], *, cwd: Path, environ: dict[str, str] | None = None,
             timeout: float = 300, check: bool = True) -> subprocess.CompletedProcess:
    completed = subprocess.run(args, cwd=cwd, env=environ, text=True, encoding="utf-8", errors="replace",
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    if check and completed.returncode:
        raise RuntimeError(f"command failed ({completed.returncode}): {' '.join(args)}\n{completed.stdout[-2000:]}")
    return completed


class Stack:
    """One disposable Omnigraph compose project."""

    def __init__(self, repo: Path, project: str, build: dict, storage: str,
                 lease_seconds: int = DEFAULT_LEASE_SECONDS):
        self.lease_seconds = lease_seconds
        self.repo = repo
        self.project = project
        self.build = build
        self.storage = storage
        self.compose_file = repo / "targets" / "03-omnigraph" / "docker" / "compose.yml"
        self.root = "file:///var/lib/omnigraph" if storage == "local" else \
            f"s3://witnessmark/{project}"
        self.environ = dict(os.environ)
        self.environ.update({
            "WM_OMNIGRAPH_IMAGE": f"{build['image']}@{build['digest']}",
            "WM_OMNIGRAPH_CLUSTER": self.root,
            "WM_S3_ENDPOINT": "http://wm-object-proxy:9010" if storage == "proxy" else "http://wm-minio:9000",
            "WM_CLUSTER_LEASE_SECONDS": str(lease_seconds),
            "WM_MINIO_IMAGE": MINIO_IMAGE,
        })

    def compose(self, *args: str, timeout: float = 300, check: bool = True) -> subprocess.CompletedProcess:
        return _command(["docker", "compose", "-p", self.project, "-f", str(self.compose_file), *args],
                        cwd=self.repo, environ=self.environ, timeout=timeout, check=check)

    def down(self) -> None:
        self.compose("--profile", "failover-b", "down", "-v", "--remove-orphans", check=False)

    # Wait on /readyz, never /healthz: the listener opens before graphs load, so
    # /healthz answers while data requests still get 503 graph_unavailable
    # (deployment.md, S3 cluster serving text on /readyz).
    def _wait_url(self, url: str, timeout: float = 45) -> None:
        deadline = time.monotonic() + timeout
        last = "no response"
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    if response.status < 400:
                        return
            except (OSError, urllib.error.URLError) as exc:
                last = str(exc)
            time.sleep(0.25)
        raise RuntimeError(f"service did not become ready at {url}: {last}")

    def _start_object_store(self) -> None:
        services = ["wm-minio"] + (["wm-object-proxy"] if self.storage == "proxy" else [])
        self.compose("up", "-d", "--no-build", *services)
        self._wait_url("http://127.0.0.1:19000/minio/health/ready")
        aws_env = dict(os.environ)
        aws_env.update({"AWS_ACCESS_KEY_ID": "witnessmark", "AWS_SECRET_ACCESS_KEY": "witnessmark-local-only",
                        "AWS_DEFAULT_REGION": "us-east-1"})
        made = _command(["aws", "--endpoint-url", "http://127.0.0.1:19000", "s3api", "create-bucket",
                         "--bucket", "witnessmark"], cwd=self.repo, environ=aws_env, check=False)
        if made.returncode and "BucketAlreadyOwnedByYou" not in made.stdout:
            raise RuntimeError(f"could not create test bucket: {made.stdout[-1000:]}")

    def provision(self) -> None:
        self.down()
        if self.storage != "local":
            self._start_object_store()
        apply = self.compose("run", "--rm", "--no-deps", "--entrypoint", "/usr/local/bin/omnigraph",
                             "wm-omnigraph-a", "cluster", "apply", "--target", self.root,
                             "--config", "/config", "--as", "witnessmark", "--json", timeout=600)
        found = re.search(r"Admission lock:\s*([A-Z0-9]+)", apply.stdout)
        if not found:
            raise RuntimeError(f"cluster apply did not report its admission lock: {apply.stdout[-1500:]}")
        self.compose("run", "--rm", "--no-deps", "--entrypoint", "/usr/local/bin/omnigraph",
                     "wm-omnigraph-a", "cluster", "force-unlock", found.group(1), "--target", self.root)
        self.compose("up", "-d", "--no-build", "wm-omnigraph-a")
        self._wait_url("http://127.0.0.1:18080/readyz")

    def pause_a(self) -> None:
        _command(["docker", "pause", "wm-omnigraph-a"], cwd=self.repo)

    def resume_a(self) -> None:
        _command(["docker", "unpause", "wm-omnigraph-a"], cwd=self.repo, check=False)

    def stop_a(self) -> None:
        self.compose("stop", "wm-omnigraph-a", check=False)

    def start_b(self, *, check: bool = True) -> subprocess.CompletedProcess:
        result = self.compose("--profile", "failover-b", "up", "-d", "--no-build", "wm-omnigraph-b",
                              check=check)
        if check:
            self._wait_url("http://127.0.0.1:18081/readyz")
        return result


def _manifest(repo: Path, batch: str, build: dict, build_name: str, storage: str,
              scenario: str, mode: str, started: datetime, trials: list[dict], *,
              run_id: str | None = None, **extra) -> dict:
    record = {
        "schema_version": 1,
        "run_id": run_id or _run_id(started),
        "batch": batch,
        "started_at": _iso(started),
        "finished_at": _iso(_utc()),
        "harness": witnessmark_env.harness_info(repo),
        "host": witnessmark_env.host_info(),
        "target": {"name": "omnigraph", "repo": "ModernRelay/omnigraph", "ref": build_name,
                   "digest": build["digest"]},
        "components": [{"role": "sut", "name": "omnigraph-server", "version": build_name,
                        "image": build["image"], "digest": build["digest"],
                        "config": {"backend": storage}},
                       {"role": "object-store", "name": "minio",
                        "version": "RELEASE.2025-09-07T16-13-09Z", "image": MINIO_IMAGE,
                        "digest": MINIO_DIGEST}],
        "scenario": {"id": scenario, "mode": mode, "invariants": extra.pop("invariants", [])},
        "trials": trials,
        **extra,
    }
    return record


def write_manifest(repo: Path, evidence: Path, manifest: dict) -> Path:
    component = manifest["components"][0]
    storage = component["config"]["backend"]
    scenario = manifest["scenario"]
    destination = evidence / "omnigraph" / f"{component['version']}.{storage}" / \
        f"{scenario['id']}.{scenario['mode']}" / manifest["run_id"]
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "run.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                           encoding="utf-8", newline="\n")
    return destination


def update_manifest(destination: Path, manifest: dict) -> None:
    (destination / "run.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                           encoding="utf-8", newline="\n")


def redact_paths(text: str, repo: Path) -> str:
    """Remove the repository location and anything under a user's home folder."""
    text = text.replace(str(repo), "<repo>").replace(repo.as_posix(), "<repo>")
    return re.sub(r"(?i)[A-Z]:[/\\]Users[/\\][^/\\\s]+(?:[/\\]AppData[^\s\"')]*)?", "<user-home>", text)


def _error_note(destination: Path, repo: Path, exc: Exception) -> None:
    message = redact_paths(f"{type(exc).__name__}: {exc}", repo)
    (destination / "ERROR.md").write_text(
        "# Run error\n\nThe declared run did not complete. No result was inferred.\n\n"
        f"- Error: `{message[:1000].replace('`', "'")}`\n",
        encoding="utf-8", newline="\n")


def _rss_mb(container: str) -> float | None:
    result = _command(["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", container],
                      cwd=Path.cwd(), check=False)
    if result.returncode or not result.stdout.strip():
        return None
    text = result.stdout.split("/")[0].strip()
    match = re.match(r"([0-9.]+)([KMG]iB)", text)
    if not match:
        return None
    scale = {"KiB": 1 / 1024, "MiB": 1, "GiB": 1024}[match.group(2)]
    return float(match.group(1)) * scale


def _local_store_bytes() -> int | None:
    result = _command(["docker", "exec", "wm-omnigraph-a", "du", "-sb", "/var/lib/omnigraph"],
                      cwd=Path.cwd(), check=False)
    match = re.match(r"(\d+)", result.stdout.strip()) if not result.returncode else None
    return int(match.group(1)) if match else None


def _proxy(method: str, path: str) -> dict:
    request = urllib.request.Request(f"http://127.0.0.1:19010{path}", method=method, data=b"" if method == "POST" else None)
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read() or b"{}")


def _padding_batches(client: OmnigraphClient, start: int, stop: int, batch_size: int = 4096) -> None:
    for first in range(start, stop, batch_size):
        last = min(stop, first + batch_size)
        lines = [json.dumps({"type": "Entry", "id": f"pad-{i}", "data": {
            "id": f"pad-{i}", "seq": i, "rule": "padding", "hash": str(i), "prev": "", "ts": 0,
        }}, separators=(",", ":")) for i in range(first, last)]
        _check(client.load_ndjson(("\n".join(lines) + "\n").encode()), f"load nodes {first}:{last}")
    # Each increment is a cycle. Across increments this still gives exactly one
    # Next edge for every padding node without rewriting an older edge.
    for first in range(start, stop, batch_size):
        last = min(stop, first + batch_size)
        lines = []
        for i in range(first, last):
            target = start if i == stop - 1 else i + 1
            lines.append(json.dumps({"edge": "Next", "id": f"next-{i}",
                                     "from": f"pad-{i}", "to": f"pad-{target}", "data": {}},
                                    separators=(",", ":")))
        _check(client.load_ndjson(("\n".join(lines) + "\n").encode()), f"load edges {first}:{last}")


class _Reader:
    def __init__(self, client: OmnigraphClient, query: str):
        self.client, self.query = client, query
        self.stop = threading.Event()
        self.samples: list[tuple[int, int]] = []
        self.error: str | None = None
        self.thread = threading.Thread(target=self._run, name="wm-o1-reader", daemon=True)

    def _run(self) -> None:
        while not self.stop.is_set():
            before = time.perf_counter_ns()
            result = self.client.query(self.query, {"task_id": TASK}, name="q_task")
            after = time.perf_counter_ns()
            if result.outcome is not Outcome.OK:
                self.error = f"{result.outcome.value} {result.kind}: {result.message}"
                return
            self.samples.append((before, after))

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.stop.set()
        self.thread.join(timeout=10)


def _timed_branch_create(client: OmnigraphClient, queries: dict[str, str], name: str) -> dict:
    rss_before = _rss_mb("wm-omnigraph-a")
    with _Reader(OmnigraphClient("http://127.0.0.1:18080", "witnessmark", timeout=60), queries["q_task"]) as reader:
        time.sleep(0.25)
        split = time.perf_counter_ns()
        started = time.perf_counter_ns()
        result = client.branch_create(name, from_branch="main")
        finished = time.perf_counter_ns()
        time.sleep(0.1)
    _check(result, f"create branch {name}")
    if reader.error:
        raise RuntimeError(f"closed-loop reader failed: {reader.error}")
    before_lats = [(end - begin) / 1e6 for begin, end in reader.samples if end < split]
    during_lats = [(end - begin) / 1e6 for begin, end in reader.samples if begin <= finished and end >= started]
    completions_before = [end for _begin, end in reader.samples if end < split]
    completions_during = [end for _begin, end in reader.samples if started <= end <= finished]
    baseline_gaps = [(b - a) / 1e6 for a, b in zip(completions_before, completions_before[1:])]
    during_gaps = [(b - a) / 1e6 for a, b in zip([started, *completions_during], [*completions_during, finished])]
    return {
        "create_ms": (finished - started) / 1e6,
        "reader_p99_before_ms": _percentile(before_lats, 99),
        "reader_p99_during_ms": _percentile(during_lats, 99),
        "stall_ms": max(0.0, (max(during_gaps) if during_gaps else 0) -
                        (statistics.median(baseline_gaps) if baseline_gaps else 0)),
        "rss_before_mb": rss_before,
        "rss_after_mb": _rss_mb("wm-omnigraph-a"),
    }


def _lease_rows(client: OmnigraphClient, queries: dict[str, str], branch: str = "main", rule: str = "i6") -> list[int]:
    result = _check(client.query(queries["q_ledger"], {"rule": rule}, name="q_ledger", branch=branch), "read ledger")
    data = result.data if isinstance(result.data, dict) else {}
    return [int(row["seq"]) for row in data.get("rows", [])]


def _i6_controls(client: OmnigraphClient, queries: dict[str, str]) -> dict:
    for name in ("i6-prefix", "i6-isolation"):
        client.branch_delete(name)
    anchors = [json.dumps({"type": "Entry", "id": name, "data": {
        "id": name, "seq": 0, "rule": "anchor", "hash": "0", "prev": "", "ts": 0,
    }}, separators=(",", ":")) for name in ("i6-anchor", "i6b-branch-anchor", "i6b-main-anchor")]
    _check(client.load_ndjson(("\n".join(anchors) + "\n").encode()), "load I6 anchors")
    writer_done = threading.Event()
    writer_error: list[str] = []

    def writer():
        try:
            for seq in range(1, 21):
                _check(client.mutate(queries["m_ledger"], {"id": f"i6-{seq}", "seq": seq, "rule": "i6",
                              "hash": str(seq), "prev": f"i6-{seq - 1}" if seq > 1 else "i6-anchor", "ts": seq},
                              name="m_ledger"), "append i6 ledger")
                time.sleep(0.01)
        except Exception as exc:  # retained as evidence, then raised below
            writer_error.append(str(exc))
        finally:
            writer_done.set()

    thread = threading.Thread(target=writer, name="wm-i6-writer", daemon=True)
    thread.start()
    time.sleep(0.04)
    _check(client.branch_create("i6-prefix", from_branch="main"), "create ledger branch")
    writer_done.wait(30)
    thread.join(timeout=2)
    if writer_error:
        raise RuntimeError(writer_error[0])
    main = _lease_rows(client, queries)
    prefix = _lease_rows(client, queries, "i6-prefix")
    prefix_ok = prefix == main[:len(prefix)] and prefix == list(range(1, len(prefix) + 1))

    _check(client.branch_create("i6-isolation", from_branch="main"), "create isolation branch")
    _check(client.mutate(queries["m_ledger"], {"id": "branch-only", "seq": 1001, "rule": "i6b",
                  "hash": "b", "prev": "i6b-branch-anchor", "ts": 1}, name="m_ledger", branch="i6-isolation"),
           "write branch-only row")
    _check(client.mutate(queries["m_ledger"], {"id": "main-only", "seq": 1002, "rule": "i6b",
                  "hash": "m", "prev": "i6b-main-anchor", "ts": 2}, name="m_ledger"), "write main-only row")
    on_main = _lease_rows(client, queries, rule="i6b")
    on_branch = _lease_rows(client, queries, "i6-isolation", "i6b")
    isolation_ok = on_main == [1002] and on_branch == [1001]
    return {"i6a_gapless_prefix": prefix_ok, "main_seq": main, "branch_prefix_seq": prefix,
            "i6b_isolation": isolation_ok, "main_visible": on_main, "branch_visible": on_branch}


def run_o1(repo: Path, evidence: Path, batch: str, build_name: str, build: dict, storage: str,
           *, include_falkor: bool = False) -> tuple[dict, Path]:
    started = _utc()
    run_id = _run_id(started)
    project = f"wm-m4-o1-{build_name.replace('.', '-')}-{storage}".lower()
    stack = Stack(repo, project, build, storage)
    trials: list[dict] = []
    copy_weight: list[dict] = []
    queries = load_queries()
    sweep = {"nodes": list(SIZES), "edges_per_size": list(SIZES), "siblings": list(SIBLINGS),
             "storage": storage, "warmups": WARMUPS, "measured_repetitions": REPETITIONS}
    planned = _manifest(repo, batch, build, build_name, storage, "o1.branch_cost", "curve", started, [],
                        run_id=run_id, invariants=["I6a", "I6b", "I6c"], sweep=sweep,
                        cluster_lease_seconds=stack.lease_seconds, status="planned-before-execution")
    path = write_manifest(repo, evidence, planned)
    try:
        stack.provision()
        client = OmnigraphClient("http://127.0.0.1:18080", "witnessmark", timeout=180)
        _check(client.mutate(queries["m_reset"], {}, name="m_reset"), "reset O1 graph")
        _check(client.mutate(queries["m_o1_fixture"], {"task_id": TASK, "skill_id": SKILL},
                             name="m_o1_fixture"), "create O1 fixture")
        previous = 0
        for size in SIZES:
            _padding_batches(client, previous, size)
            previous = size
            for branch in [f"o1-sibling-{i:02d}" for i in range(max(SIBLINGS))]:
                client.branch_delete(branch)
            live = 0
            for siblings in SIBLINGS:
                while live < siblings:
                    _check(client.branch_create(f"o1-sibling-{live:02d}", from_branch="main"), "create sibling")
                    live += 1
                for warmup in range(WARMUPS):
                    name = f"o1-warm-{size}-{siblings}-{warmup}"
                    _check(client.branch_create(name, from_branch="main"), "warm branch create")
                    _check(client.branch_delete(name), "warm branch delete")
                measured = []
                for repetition in range(REPETITIONS):
                    name = f"o1-measure-{size}-{siblings}-{repetition}"
                    sample = _timed_branch_create(client, queries, name)
                    begin = time.perf_counter_ns()
                    _check(client.merge(name, target="main"), "merge unchanged branch")
                    sample["merge_unchanged_ms"] = (time.perf_counter_ns() - begin) / 1e6
                    begin = time.perf_counter_ns()
                    _check(client.branch_delete(name), "delete measured branch")
                    sample["delete_ms"] = (time.perf_counter_ns() - begin) / 1e6
                    sample["repetition"] = repetition
                    measured.append(sample)
                counts = None
                if storage == "proxy":
                    _proxy("POST", "/__witnessmark__/reset")
                    count_name = f"o1-count-{size}-{siblings}"
                    _check(client.branch_create(count_name, from_branch="main"), "count branch create")
                    _check(client.branch_delete(count_name), "count branch delete")
                    counts = _proxy("GET", "/__witnessmark__/counts")
                trials.append({"valid": True, "size": size, "siblings": siblings,
                               "warmups": WARMUPS, "repetitions": REPETITIONS,
                               "timing_kind": "matched-counts" if storage == "proxy" else "timing",
                               "samples": measured, "object_store_counts": counts,
                               "graph_store_bytes": _local_store_bytes() if storage == "local" else None})
            anchor = f"weight-anchor-{size}"
            anchor_row = json.dumps({"type": "Entry", "id": anchor, "data": {
                "id": anchor, "seq": 0, "rule": "anchor", "hash": "0", "prev": "", "ts": 0,
            }}, separators=(",", ":")) + "\n"
            _check(client.load_ndjson(anchor_row.encode()), "load copy-weight anchor")
            weight_branch = f"o1-weight-{size}"
            begun = time.perf_counter_ns()
            _check(client.branch_create(weight_branch, from_branch="main"), "copy-weight create")
            _check(client.mutate(queries["m_ledger"], {"id": f"weight-{size}", "seq": size,
                          "rule": "copy-weight", "hash": str(size), "prev": anchor, "ts": size},
                          name="m_ledger", branch=weight_branch), "copy-weight claim")
            _check(client.query(queries["q_task"], {"task_id": TASK}, name="q_task", branch=weight_branch),
                   "copy-weight score")
            _check(client.branch_delete(weight_branch), "copy-weight discard")
            copy_weight.append({"size": size, "cycle_ms": (time.perf_counter_ns() - begun) / 1e6})
        i6 = _i6_controls(client, queries)
        falkor = run_falkor_curve(repo) if include_falkor else None
        manifest = _manifest(repo, batch, build, build_name, storage, "o1.branch_cost", "curve", started,
                             trials, run_id=run_id, invariants=["I6a", "I6b", "I6c"], sweep=sweep,
                             cluster_lease_seconds=stack.lease_seconds, status="complete",
                             copy_weight=copy_weight, controls={"i6": i6, "falkordb": falkor})
        update_manifest(path, manifest)
        return manifest, path
    except Exception as exc:
        _error_note(path, repo, exc)
        raise
    finally:
        stack.down()


def _info_value(text: str, key: str) -> int | None:
    match = re.search(rf"(?m)^{re.escape(key)}:(\d+)", text)
    return int(match.group(1)) if match else None


def _falkor_reader(session, graph: str, stop: threading.Event, samples: list[int], write: bool = False):
    while not stop.is_set():
        try:
            if write:
                session.call("GRAPH.QUERY", graph, "MERGE (n:Pulse {id: 1}) SET n.v = coalesce(n.v,0)+1")
            else:
                session.call("GRAPH.RO_QUERY", graph, "MATCH (n) RETURN count(n)")
            samples.append(time.perf_counter_ns())
        except Exception:
            return


# The S28 figures were measured with `appendfsync always` (master 7.2). The baseline
# container runs with appendonly off, where GRAPH.COPY is 40 to 60% faster and the
# sanity band cannot be compared, so the curve sets S28's persistence for its own
# duration, records it, and restores what it found.
S28_PERSISTENCE = {"appendonly": "yes", "appendfsync": "always"}


def _config_get(session, key: str) -> str | None:
    pair = session.call("CONFIG", "GET", key)
    return str(pair[1]) if isinstance(pair, list) and len(pair) > 1 else None


def run_falkor_curve(repo: Path) -> dict:
    engine = make_engine("falkordb", host="127.0.0.1", port=16380)
    admin = engine.session(timeout=300)
    source, other = "o1source", "o1other"
    rows = []
    found = {key: _config_get(admin, key) for key in S28_PERSISTENCE}
    try:
        for key, value in S28_PERSISTENCE.items():
            admin.call("CONFIG", "SET", key, value)
        persistence = {key: _config_get(admin, key) for key in S28_PERSISTENCE}
        for graph in (source, other):
            try:
                admin.call("GRAPH.DELETE", graph)
            except Exception:
                pass
        admin.call("GRAPH.QUERY", other, "CREATE (:Pulse {id: 1, v: 0})")
        previous = 0
        for size in SIZES:
            if previous == 0:
                admin.call("GRAPH.QUERY", source, "CREATE INDEX FOR (n:Entry) ON (n.id)")
            for first in range(previous, size, 10_000):
                last = min(size - 1, first + 9_999)
                admin.call("GRAPH.QUERY", source,
                           f"UNWIND range({first},{last}) AS i CREATE (:Entry {{id:i}})")
            # Give each newly added chunk its own cycle; exactly one edge per node.
            for first in range(previous, size, 10_000):
                last = min(size - 1, first + 9_999)
                admin.call("GRAPH.QUERY", source,
                           f"UNWIND range({first},{last}) AS i MATCH (a:Entry {{id:i}}), "
                           f"(b:Entry {{id: CASE WHEN i={last} THEN {first} ELSE i+1 END}}) CREATE (a)-[:Next]->(b)")
            previous = size
            for warmup in range(WARMUPS):
                dest = f"o1warm{size}{warmup}"
                admin.call("GRAPH.COPY", source, dest)
                admin.call("GRAPH.DELETE", dest)
            samples = []
            for repetition in range(REPETITIONS):
                dest = f"o1copy{size}{repetition}"
                stop = threading.Event()
                source_done: list[int] = []
                other_done: list[int] = []
                writer_done: list[int] = []
                sessions = [engine.__class__(host="127.0.0.1", port=16380, graph=g).session(timeout=300)
                            for g in (source, other, other)]
                threads = [threading.Thread(target=_falkor_reader,
                                            args=(sessions[i], (source, other, other)[i], stop,
                                                  (source_done, other_done, writer_done)[i], i == 2), daemon=True)
                           for i in range(3)]
                for thread in threads:
                    thread.start()
                time.sleep(0.2)
                before = _rss_mb("wm-falkordb")
                started = time.perf_counter_ns()
                admin.call("GRAPH.COPY", source, dest)
                finished = time.perf_counter_ns()
                stop.set()
                for thread in threads:
                    thread.join(timeout=10)
                for session in sessions:
                    session.close()
                info = admin.call("INFO", "persistence")
                info_text = info if isinstance(info, str) else ""
                def gap(values):
                    inside = [v for v in values if started <= v <= finished]
                    return max(((b - a) / 1e6 for a, b in zip([started, *inside], [*inside, finished])), default=0)
                rss_after = _rss_mb("wm-falkordb")
                deleted = time.perf_counter_ns()
                admin.call("GRAPH.DELETE", dest)
                delete_ms = (time.perf_counter_ns() - deleted) / 1e6
                samples.append({"repetition": repetition, "copy_ms": (finished - started) / 1e6,
                                "delete_ms": delete_ms,
                                "source_reader_stall_ms": gap(source_done),
                                "unrelated_reader_stall_ms": gap(other_done),
                                "unrelated_writer_stall_ms": gap(writer_done),
                                "rss_before_mb": before, "rss_after_mb": rss_after,
                                "aof_bytes": _info_value(info_text, "aof_current_size")})
            median_ms = statistics.median(sample["copy_ms"] for sample in samples)
            reference = {32_000: 165, 128_000: 546, 512_000: 2400}[size]
            rows.append({"size": size, "warmups": WARMUPS, "repetitions": REPETITIONS,
                         "samples": samples, "copy_ms": _summary([s["copy_ms"] for s in samples]),
                         "s28_reference_ms": reference, "inside_50_percent_band": reference * .5 <= median_ms <= reference * 1.5})
        return {"rows": rows, "sanity_band_met": all(row["inside_50_percent_band"] for row in rows),
                "persistence_during_curve": persistence, "persistence_found": found}
    finally:
        for key, value in found.items():
            if value is not None:
                try:
                    admin.call("CONFIG", "SET", key, value)
                except Exception:
                    pass
        admin.close()


def _health(url: str, timeout: float = 8) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status < 400:
                    return True
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.25)
    return False


def _op_json(result: OperationResult | None) -> dict | None:
    if result is None:
        return None
    return {"outcome": result.outcome.value, "status": result.status, "kind": result.kind,
            "message": result.message, "data": result.data}


O4_HARNESS_GAPS = [
    "The epoch claim (Omnigraph::claim_branch_writer, an embedding-program call) was not performed, so the "
    "writer epoch fence was never engaged and the acceptance criteria could not be tested.",
    "On a local root the documented ownership transfer (stop the previous owner, then force-unlock its exact "
    "lock id) was not performed: A was paused, not terminal, so the successor was refused admission.",
]


def classify_o4_cell(build_name: str, storage: str, successor_ready: bool) -> tuple[str, str]:
    """Return (status, reason) for one O4 cell from what happened, never from what was hoped."""
    if not successor_ready:
        return ("NOT_EXERCISED",
                "no failover took place: the successor server did not become ready; the local root's "
                "admission lock is unleased and its documented transfer needs a terminal owner, so a "
                "paused A keeps it" if storage == "local" else
                "no failover took place: the successor server did not become ready")
    if build_name.startswith("edge"):
        return ("NOT_EXERCISED",
                "the successor took over, but main's epoch was never claimed (no CLI or HTTP route claims a "
                "branch at this pin), so the fence acceptance criteria cannot apply; the outcome at epoch 0 "
                "is recorded")
    return ("BOUNDARY",
            "the stable release predates the epoch fence; a stale writer is bounded only by the documented "
            "one-writer deployment rule")


def run_o4(repo: Path, evidence: Path, batch: str, build_name: str, build: dict, storage: str,
           seed: int = 20261115) -> tuple[dict, Path]:
    """Run the O4 topology and classify each cell from what it actually did.

    The edge pin documents that no CLI or HTTP route claims a branch; only a
    program that embeds the engine calls ``Omnigraph::claim_branch_writer``.
    This harness drives the published server and CLI binaries and never claims,
    so no cell can engage the epoch fence. A cell is therefore never PASS or
    FAIL here, and a gap of the harness is never labelled a boundary:

    * NOT_EXERCISED: the successor did not become a writer (the local root's
      unleased admission lock was not transferred), or it did but the fence
      acceptance criteria cannot apply because ``main`` was never claimed.
    * BOUNDARY: a failover took place on the stable release, whose documented
      deployment rule (one writer process) is its only protection.
    """
    started = _utc()
    trials = []
    queries = load_queries()
    offsets = {"p1": -1.0, "p2": 0.001, "p3": 0.005}
    for phase, offset in offsets.items():
        for variant in ("a", "b"):
            project = f"wm-m4-o4-{build_name.replace('.', '-')}-{storage}-{phase}-{variant}".lower()
            stack = Stack(repo, project, build, storage, lease_seconds=LEASE_SECONDS)
            actions = []
            a_result: list[OperationResult] = []
            try:
                stack.provision()
                a = OmnigraphClient("http://127.0.0.1:18080", "witnessmark", timeout=60)
                _check(a.mutate(queries["m_reset"], {}, name="m_reset"), "reset O4 graph")
                _check(a.mutate(queries["m_fixture_base"], {"task_id": TASK, "skill_id": SKILL},
                                name="m_fixture_base"), "create O4 fixture")

                def write_a():
                    a_result.append(a.mutate(queries["m_fixture_agent"],
                                             {"agent_id": f"a-{phase}-{variant}", "skill_id": SKILL},
                                             name="m_fixture_agent"))

                thread = threading.Thread(target=write_a, name="wm-o4-a-write", daemon=True)
                if offset < 0:
                    stack.pause_a()
                    actions.append({"client": "nemesis", "kind": "pause", "target": "wm-omnigraph-a",
                                    "assertion": "pause our A test container before staging"})
                    thread.start()
                else:
                    thread.start()
                    time.sleep(offset)
                    stack.pause_a()
                    actions.append({"client": "nemesis", "kind": "pause", "target": "wm-omnigraph-a",
                                    "assertion": f"pause our A test container at seeded {phase} offset {offset}s"})

                # S3 admission has the configured leased takeover. Local roots
                # deliberately have no timeout and cannot be transferred while
                # a paused owner is potentially active.
                if storage != "local":
                    time.sleep(LEASE_SECONDS * 1.75)
                start = stack.start_b(check=False)
                b_ready = _health("http://127.0.0.1:18081/readyz", 10 if storage != "local" else 3)
                b_write = None
                if b_ready and variant == "b":
                    b = OmnigraphClient("http://127.0.0.1:18081", "witnessmark", timeout=30)
                    b_write = b.mutate(queries["m_fixture_agent"],
                                       {"agent_id": f"b-{phase}-{variant}", "skill_id": SKILL},
                                       name="m_fixture_agent")
                stack.resume_a()
                actions.append({"client": "nemesis", "kind": "resume", "target": "wm-omnigraph-a",
                                "assertion": "resume our stale A test container and observe its pending publication"})
                thread.join(timeout=30)
                branch_state = a.branch_list(detailed=True)
                scan_results = [
                    a.query(queries["q_task"], {"task_id": TASK}, name="q_task"),
                    a.query(queries["q_eligible"], {}, name="q_eligible"),
                    a.query(queries["q_ledger"], {"rule": "genesis"}, name="q_ledger"),
                ]
                fenced = bool(a_result and a_result[0].kind == "WriterFenced")
                status, reason = classify_o4_cell(build_name, storage, b_ready)
                trials.append({
                    "valid": True, "phase": phase, "variant": variant, "seed": seed, "offset_s": offset,
                    "status": status, "reason": reason,
                    "fault_actions": actions, "successor_start_exit": start.returncode, "successor_ready": b_ready,
                    "a_write": _op_json(a_result[0] if a_result else None), "b_write": _op_json(b_write),
                    "writer_fenced_observed": fenced, "branch_list": _op_json(branch_state),
                    "graph_open_and_scan": all(result.outcome is Outcome.OK for result in scan_results),
                    "referenced_objects_exist": "not_exercised_without_a_claimed_epoch",
                    "single_epoch": "epoch_zero_unclaimed",
                })
            finally:
                stack.resume_a()
                stack.down()
    boundary_probes = [
        {"operation": name, "status": "NOT_EXERCISED",
         "reason": "needs a claimed epoch; claiming is an embedding-program step this harness did not perform"}
        for name in ("branch create/delete", "cleanup", "optimize", "several failovers", "simultaneous claims")
    ]
    manifest = _manifest(repo, batch, build, build_name, storage, "o4.failover_acceptance", "matrix", started,
                         trials, invariants=["I1A", "I2"], seed=seed,
                         matrix={"phases": list(offsets), "variants": ["a", "b"], "storage": storage,
                                 "build": build_name}, boundary_probes=boundary_probes,
                         cluster_lease_seconds=LEASE_SECONDS, harness_gaps=O4_HARNESS_GAPS,
                         basis="documented", basis_ref="docs/user/operations/troubleshooting.md#writer-epoch")
    return manifest, write_manifest(repo, evidence, manifest)


def run_o5(repo: Path, evidence: Path, batch: str, build_name: str, build: dict,
           storage: str = "local") -> tuple[dict, Path]:
    started = _utc()
    stack = Stack(repo, f"wm-m4-o5-{build_name.replace('.', '-')}-{storage}".lower(), build, storage)
    queries = load_queries()
    trials = []
    try:
        stack.provision()
        a = OmnigraphClient("http://127.0.0.1:18080", "witnessmark", timeout=60)
        _check(a.mutate(queries["m_reset"], {}, name="m_reset"), "reset O5 graph")
        _check(a.mutate(queries["m_fixture_base"], {"task_id": TASK, "skill_id": SKILL},
                        name="m_fixture_base"), "create O5 fixture")
        _check(a.mutate(queries["m_fixture_agent"], {"agent_id": "c00", "skill_id": SKILL},
                        name="m_fixture_agent"), "create O5 agent")
        before = time.perf_counter_ns()
        acknowledged = _check(a.mutate(queries["m_claim_card"], {"task_id": TASK, "agent_id": "c00",
                              "from_seq": 1, "until_pt": 9_223_372_036_854_775_807, "rw": "o5-lease"},
                              name="m_claim_card"), "A acknowledged O5 write")
        acknowledged_at = time.perf_counter_ns()
        stack.stop_a()
        stack.start_b(check=True)
        b = OmnigraphClient("http://127.0.0.1:18081", "witnessmark", timeout=30)
        deadline = time.monotonic() + 30
        seen = False
        attempts = 0
        last = None
        while time.monotonic() < deadline:
            attempts += 1
            last = b.query(queries["q_task_holder"], {"task_id": TASK}, name="q_task_holder")
            data = last.data if isinstance(last.data, dict) else {}
            holders = [row.get("holder") for row in data.get("rows", [])]
            if holders == ["c00"]:
                seen = True
                break
            time.sleep(0.01)
        observed_at = time.perf_counter_ns()
        trials.append({"valid": True, "write_acknowledged": acknowledged.outcome is Outcome.OK,
                       "second_process": "wm-omnigraph-b", "seen": seen, "attempts": attempts,
                       "write_ms": (acknowledged_at - before) / 1e6,
                       "staleness_ms": (observed_at - acknowledged_at) / 1e6,
                       "last_read": _op_json(last)})
        manifest = _manifest(repo, batch, build, build_name, storage, "o5.cross_process_ryw", "visibility",
                             started, trials, invariants=["I3"], cluster_lease_seconds=stack.lease_seconds)
        return manifest, write_manifest(repo, evidence, manifest)
    finally:
        stack.down()
