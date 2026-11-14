"""C4: the scale ladder (target blueprint section 5, #6170's shape).

One helper process ingests the seeded corpus in batches of ``batch_size`` documents
(``DataItem``s with pinned ``data_id``s), each batch followed by an incremental
``cognify(chunks_per_batch=16)``, as #6170's reporter did. At every rung of the
declared ladder it records the store size, the graph's node and entity counts, the
resident memory of the helper and its children (the Ladybug and LanceDB workers),
and the time per batch. A crash (the helper dying, or Cognee raising after a worker
died) ends the climb: its signal, exit code and the documents reached are recorded,
and the store is then reopened in a fresh process, read-only and read-write.

Each rung is one "trial" in run.json. Stub calls are counted per rung rather than
written to history.jsonl one by one: the full ladder makes some 20,000 of them.
"""

from __future__ import annotations

import asyncio
import ctypes
import os
import subprocess
import sys
import time
from pathlib import Path

from witnessmark import SCHEMA_VERSION
from witnessmark.checkers import Check
from witnessmark.evidence import digest, make_run_id
from witnessmark.history import FAIL, OK, UNKNOWN, Op
from witnessmark.memory import MemoryRunConfig, _finish, _header, _note_crash, _run_dir, _verdicts
from witnessmark.timing import stamp, utc_now
from witnessmark.verdicts import summarize

from .fixtures import build
from .helper import HelperDied, RemoteError

GROUP = "wm_c4"
CRASH_ISSUE = "https://github.com/topoteretes/cognee/issues/6170"


# --- resident memory, standard library only ------------------------------------------------------------------


def _children(pid: int) -> list[int]:
    if os.name != "nt":
        try:
            out = subprocess.check_output(["ps", "-o", "pid=", "--ppid", str(pid)], text=True)
            return [int(x) for x in out.split()]
        except (OSError, subprocess.CalledProcessError):
            return []

    class Entry(ctypes.Structure):
        _fields_ = [("dwSize", ctypes.c_ulong), ("cntUsage", ctypes.c_ulong), ("th32ProcessID", ctypes.c_ulong),
                    ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", ctypes.c_ulong),
                    ("cntThreads", ctypes.c_ulong), ("th32ParentProcessID", ctypes.c_ulong),
                    ("pcPriClassBase", ctypes.c_long), ("dwFlags", ctypes.c_ulong), ("szExeFile", ctypes.c_char * 260)]

    kernel = ctypes.windll.kernel32
    snapshot = kernel.CreateToolhelp32Snapshot(0x2, 0)
    entry, found = Entry(), []
    entry.dwSize = ctypes.sizeof(Entry)
    ok = kernel.Process32First(snapshot, ctypes.byref(entry))
    while ok:
        if entry.th32ParentProcessID == pid:
            found.append(entry.th32ProcessID)
        ok = kernel.Process32Next(snapshot, ctypes.byref(entry))
    kernel.CloseHandle(snapshot)
    return found


def _rss(pid: int) -> int:
    if os.name != "nt":
        try:
            return int(Path(f"/proc/{pid}/statm").read_text().split()[1]) * os.sysconf("SC_PAGESIZE")
        except OSError:
            return 0

    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong), ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t)]

    handle = ctypes.windll.kernel32.OpenProcess(0x1000 | 0x0010, False, pid)
    if not handle:
        return 0
    counters = Counters()
    counters.cb = ctypes.sizeof(Counters)
    ok = ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
    ctypes.windll.kernel32.CloseHandle(handle)
    return counters.WorkingSetSize if ok else 0


def resident_mb(pid: int) -> dict:
    """Working set of a process and of each child, in MB (the helper and its database workers)."""
    children = _children(pid)
    grandchildren = [g for c in children for g in _children(c)]
    return {"helper": round(_rss(pid) / 2**20, 1),
            "children": round(sum(_rss(c) for c in children + grandchildren) / 2**20, 1),
            "child_processes": len(children) + len(grandchildren)}


# --- the store on disk ---------------------------------------------------------------------------------------

REOPEN = r"""
import json, sys
import ladybug
path, mode = sys.argv[1], sys.argv[2]
try:
    db = ladybug.Database(path, read_only=(mode == "read_only"))
    conn = ladybug.Connection(db)
    rows = conn.execute("MATCH (n) RETURN count(n)").get_all()
    print(json.dumps({"opened": True, "nodes": rows[0][0]}))
except Exception as exc:
    print(json.dumps({"opened": False, "error": f"{type(exc).__name__}: {exc}"[:400]}))
"""


def store_files(generation: Path) -> dict:
    graph = [p for p in generation.rglob("*") if p.is_file() and ".lbug" in p.name]
    lance = [p for p in generation.rglob("*") if p.is_file() and ".lance" in str(p)]
    leftovers = sorted({p.name.split(".lbug", 1)[1] or ".lbug" for p in graph})
    return {"graph_bytes": sum(p.stat().st_size for p in graph), "graph_files": leftovers,
            "vector_bytes": sum(p.stat().st_size for p in lance)}


def reopen(generation: Path) -> dict:
    stores = [p for p in generation.rglob("*.lbug") if p.is_file()]
    if not stores:
        return {"read_only": "n/a (no Ladybug store)", "read_write": "n/a"}
    out = {"store": stores[0].relative_to(generation).as_posix()}
    for mode in ("read_only", "read_write"):
        try:
            done = subprocess.run([sys.executable, "-c", REOPEN, str(stores[0]), mode], capture_output=True,
                                  text=True, timeout=600)
            line = (done.stdout.strip().splitlines() or ["{}"])[-1]
            import json

            out[mode] = json.loads(line) if line.startswith("{") else {"opened": False, "error": done.stderr[-300:]}
            out[mode]["exit_code"] = done.returncode
        except subprocess.TimeoutExpired:
            out[mode] = {"opened": False, "error": "no answer in 600 s"}
    return out


# --- the run -------------------------------------------------------------------------------------------------


async def run_ladder(config: MemoryRunConfig, sizes: list[int], batch_size: int = 16) -> dict:
    target = config.spec.build()
    await target.open()
    try:
        started = utc_now()
        corpus = build("c4")
        sizes = sorted(sizes)
        if sizes[-1] > len(corpus.docs):
            raise ValueError(f"the corpus has {len(corpus.docs)} documents")
        params = {"ladder": sizes, "batch_size": batch_size, "chunks_per_batch": 16, "pinned_ids": True,
                  "corpus": "c4: seeded generator, seed 6170, one dated sentence per document",
                  "declared_sweep": [{"documents": s} for s in sizes]}
        header = _header(config, target, "c4.ladder", ("I2",), "sequential", 1, len(sizes), started, params)
        run_id = make_run_id(started, header)
        run_dir = _run_dir(config, "c4.ladder", run_id)
        history: list[Op] = []
        trials: list[dict] = []
        tags = [doc.tag for doc in corpus.docs]
        crash: dict | None = None
        done = 0
        climb_start = time.perf_counter()
        for k, size in enumerate(sizes, 1):
            batch_seconds, peak = [], {"helper": 0.0, "children": 0.0}
            stub = {"llm": 0, "embed": 0, "errors": 0}
            while done < size and crash is None:
                batch = tags[done:min(done + batch_size, size)]
                item = {"entry": "add_cognify", "tags": batch, "pinned_ids": True, "chunks_per_batch": 16}
                inv = stamp()
                began = time.perf_counter()
                pid = target.helper.process.pid if target.helper else None
                try:
                    result = await target.ingest(item, GROUP)
                    op = Op(run_id, k, "race", f"{k}-c00-{done:05d}", "c00", "ingest",
                            {"group": GROUP, "entry": "add_cognify", "first": batch[0], "documents": len(batch)},
                            inv, stamp(), OK, {"seconds": result.get("seconds")}, process=str(pid))
                    done += len(batch)
                    batch_seconds.append(time.perf_counter() - began)
                except (HelperDied, RemoteError) as exc:
                    died = isinstance(exc, HelperDied)
                    crash = {"documents_committed": done, "batch_first": batch[0], "kind": "process exit" if died
                             else "Cognee raised", "exit_code": exc.exitcode if died else None,
                             "error": str(exc)[:1500]}
                    op = Op(run_id, k, "race", f"{k}-c00-{done:05d}", "c00", "ingest",
                            {"group": GROUP, "entry": "add_cognify", "first": batch[0], "documents": len(batch)},
                            inv, None, UNKNOWN if died else FAIL, None,
                            {"type": type(exc).__name__, "message": str(exc)[:1500]}, process=str(pid))
                history.append(op)
                if pid and crash is None:
                    sample = resident_mb(pid)
                    peak = {key: max(peak[key], sample[key]) for key in peak}
                for call in target.drain_stub_calls():
                    stub[call.get("kind", "llm")] = stub.get(call.get("kind", "llm"), 0) + 1
                    stub["errors"] += int(bool((call.get("decision") or {}).get("error")))
            generation = target._current()
            counts = None
            if crash is None:
                counts = await target.call("graph_counts", GROUP)
            expected_entities = len(corpus.entity_keys(tags[:size]))
            checks = []
            if counts is not None:
                checks.append(Check("I2", counts["entities"] == expected_entities,
                                    abs(expected_entities - counts["entities"]), "entities off",
                                    f"{counts['entities']} entity nodes; the fixture names {expected_entities}"))
            checks.append(Check("CRASH", crash is None, 0 if crash is None else 1, "crashes",
                                "no crash" if crash is None else f"{crash['kind']} after {crash['documents_committed']}"
                                f" documents: {crash['error'][:300]}"))
            trials.append({
                "k": k, "rung": size, "valid": stub["errors"] == 0, "precondition_digest": "",
                "release_spread_ms": 0.0, "max_in_flight": 1,
                "outcomes": {o: sum(1 for op in history if op.k == k and op.outcome == o) for o in (OK, FAIL, UNKNOWN)},
                "quiesce_ms": 0.0, "final_state_digest": digest(counts or {}), "state_file": "",
                "documents": done, "elapsed_s": round(time.perf_counter() - climb_start, 1),
                "batch_seconds": {**summarize(batch_seconds), "unit": "s", "batches": len(batch_seconds)},
                "resident_mb_peak": peak, "store": store_files(generation), "graph": counts, "stub_calls": stub,
                "crash": crash, "checks": [c.to_json() for c in checks],
                **({"invalid_reason": f"{stub['errors']} stub errors"} if stub["errors"] else {}),
            })
            if crash is not None:
                break
        target._stop_helper()  # release the store before reopening it
        generation = target._current()
        reopened = reopen(generation)
        run_dir.write_state(0, {GROUP: {"documents": done, "crash": crash, "reopen": reopened,
                                        "store": store_files(generation)}})
        manifest = {
            "schema_version": SCHEMA_VERSION, "run_id": run_id, "batch": config.batch, **header,
            "expectation": {"role": "target", "support": "none", "basis": "issue", "basis_ref": CRASH_ISSUE,
                            "known_deviation": None},
            "controls": [], "trials": trials, "ladder": {"documents": done, "crash": crash, "reopen": reopened},
            "verdicts": _verdicts(("I2", "CRASH"), trials, True, "none", "issue", CRASH_ISSUE),
        }
        return _finish(config, run_dir, manifest, history)
    except Exception:
        _note_crash(locals())
        raise
    finally:
        await target.close()
