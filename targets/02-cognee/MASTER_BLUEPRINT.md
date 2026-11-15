# Target 02: Cognee (topoteretes/cognee)

Part of Witnessmark. Read it together with the [master blueprint](../../MASTER_BLUEPRINT.md); "master §n" refers to a section there.

| | |
|---|---|
| Status | v0.3, 2026-11-15. M3 ran; results are in §12 and in `evidence/M3_COGNEE*.md`. Implemented in M3: `witnessmark_cognee/` (adapter, helper process, stub handlers, fixtures, scenarios C0–C6, the C4 ladder), `wm_cognee.py` (entry point), `requirements/` (frozen builds). §1.2 records what was read at the pin. A finding counts only when a run in `evidence/` backs it. |
| Code | Run with the build's venv Python: `.state/venvs/cognee-v1.6.8/Scripts/python targets/02-cognee/wm_cognee.py {race,cases,visibility,ladder} --row R1 …`. Row R3 runs in `.state/venvs/cognee-v1.6.1-falkor` with `--build v1.6.1`. |
| Project | [topoteretes/cognee](https://github.com/topoteretes/cognee), Apache-2.0. A memory engine that ingests data, builds a knowledge graph with an LLM (`cognify`), and serves graph and vector retrieval. |
| Line under test | v1.6.x. The primary pin is **v1.6.8**, tag commit `069f3cc119bdf5628be054bb915992b2fc78cfc5` (2026-11-12), which is also the current PyPI release. Before anything is filed, the scenario is re-run on the `dev` branch, where development happens. |
| Pull requests under regression | [#5253](https://github.com/topoteretes/cognee/pull/5253) (serialise local LanceDB writes across processes), [#4167](https://github.com/topoteretes/cognee/pull/4167) (lock datasets across workers), [#6571](https://github.com/topoteretes/cognee/pull/6571) (regression test for #6559). Each head commit is recorded when it is pulled. |
| Stores | Defaults: Ladybug (graph), LanceDB (vector), SQLite (relational). Alternatives: Neo4j 5.26.2, and FalkorDB 6.0.4 through the community hybrid adapter. |
| Models | An OpenAI-compatible deterministic stub endpoint (§4); no API keys |
| Out of scope | Cognee Cloud, the hosted UI, Neptune, Turso, Postgres graph handlers |

Every source link points at the v1.6.8 tag.

## 1. What is already known

| # | Fact | Tag |
|---|---|---|
| C1 | The default graph provider is `ladybug`, and the graph subprocess worker is on by default ([graph/config.py L47, L62](https://github.com/topoteretes/cognee/blob/v1.6.8/cognee/infrastructure/databases/graph/config.py#L47-L62)). The default vector store is `lancedb` and the default relational store is `sqlite` (`.env.template`). Note that `.env.template` itself sets `GRAPH_DATABASE_PROVIDER="kuzu"` (see §10). | [code] |
| C2 | Pins: `ladybug==0.22.3` on every platform except older macOS, `lancedb>=0.39.0,<0.40.0`, `pylance` 12.0.x and `litellm>=1.102.2,<2.0.0` ([pyproject.toml](https://github.com/topoteretes/cognee/blob/v1.6.8/pyproject.toml)). | [code] |
| C3 | The high-level v1.6 API is `remember` / `recall` ([README.md L100–123](https://github.com/topoteretes/cognee/blob/v1.6.8/README.md#L100-L123)). The issue repros use the lower-level `add`, `cognify`, `search` and `datasets.delete_data`. | [docs] |
| C4 | [#5254](https://github.com/topoteretes/cognee/issues/5254) (open). `LanceDBAdapter.VECTOR_DB_LOCK` is per adapter instance and per process, and `delete_data_points` did not take it. Concurrent cognify, memify and rollback work in several processes failed with `Too many concurrent writers` during `create_data_points` / `merge_insert`, leaving partially indexed documents and duplicate vector IDs. The reporter's fix is [#5253](https://github.com/topoteretes/cognee/pull/5253) (open). The reporter asked that follow-up tests cover cross-process writers and deletes. | [gh] |
| C5 | [#6559](https://github.com/topoteretes/cognee/issues/6559) (open). Stored files are content-addressed per tenant and shared across datasets. Cleanup counts the rows that reference a file and then removes it, with no lock. Ingestion writes the file first and inserts its row only at the final commit. Delete and add hold different per-dataset locks. The reporter's repro holds the window open with an injected pause; without the pause, `add()` itself failed at 1 of 36 timing offsets. The reporter says a fix is in progress, and [#6571](https://github.com/topoteretes/cognee/pull/6571) (open) adds an end-to-end regression test. | [gh] |
| C6 | [#6170](https://github.com/topoteretes/cognee/issues/6170) (open). On cognee 1.6.2 with Ladybug 0.19.0, `cognify` crashed with SIGSEGV at about 1,650 documents, twice (at 1,664 and 1,632), both in-process and in the subprocess worker. A 448-document run of the same shape completed. After the crash, the reopened store reported a corrupted WAL. The only reply so far is a bot asking for minimal code. v1.6.8 now pins Ladybug 0.22.3 (C2). | [gh] |
| C7 | [#4167](https://github.com/topoteretes/cognee/pull/4167) (open, last updated 2026-09-21). The per-dataset pipeline lock is an `asyncio.Lock` that exists only within one process. The PR adds PostgreSQL advisory locks, and file locks for SQLite and Turso. | [gh] |
| C8 | The FalkorDB adapter is the community package `cognee-community-hybrid-adapter-falkor` 0.4.1, which stores both graph and vectors in FalkorDB. It requires `falkordb>=1.0.9,<2.0.0` and pins `cognee==1.6.1` ([topoteretes/cognee-community, packages/hybrid/falkordb](https://github.com/topoteretes/cognee-community/tree/main/packages/hybrid/falkordb)). | [code] |
| C9 | Contribution rules: bugs are reported as issues; pull requests target `dev`; every commit needs a DCO sign-off ([CONTRIBUTING.md L151, L183](https://github.com/topoteretes/cognee/blob/v1.6.8/CONTRIBUTING.md)). | [docs] |

**Re-checked on 2026-11-14 (read-only, `gh api` and PyPI).** v1.6.8 is still the latest release, at tag commit `069f3cc`; the PyPI wheel's `cognee/` tree equals the tag's, line for line. #5254, #6559 and #6170 are open. #5253 (head `599ae011`), #4167 (head `87301c70`) and #6571 (head `9455c4c7`) are open and unmerged.

**Correction to C8.** On PyPI the newest `cognee-community-hybrid-adapter-falkor` is **0.4.0**, which pins `cognee==1.4.2` and `litellm==1.89.2`. Version 0.4.1, which pins `cognee==1.6.1` and `litellm==1.96.2`, exists only in the repository: `packages/hybrid/falkordb/pyproject.toml` at cognee-community `ff1324ec7586de8299e4a21fc777c021476af3f4`. Row R3 installs 0.4.1 from git at that commit [gh] [measured: install].

### 1.2 Read at the pin in M3

Paths are relative to the repository root, at `069f3cc` unless a line says otherwise.

| # | Fact | Tag |
|---|---|---|
| C10 | `GRAPH_DATABASE_PROVIDER="kuzu"` (the `.env.template` value, L223) selects **Ladybug**: `create_graph_engine` sends `"ladybug"` and `"kuzu"` to `LadybugAdapter` (`cognee/infrastructure/databases/graph/get_graph_engine.py` L446–465). It also keeps a legacy `cognee_graph_kuzu` file name when one exists (`graph/config.py` L95–103). | [code] |
| C11 | LanceDB also runs in a **subprocess worker by default**: `vector_db_subprocess_enabled: bool = True` (`vector/config.py` L37; `create_vector_engine.py` L294). With the graph worker (C1) a default Cognee process starts two database worker processes. | [code] |
| C12 | **Backend access control is on by default** when the graph and vector handlers support it, which Ladybug and LanceDB do (`cognee/context_global_variables.py` L98–107). Each dataset then has its own `.lbug` file and its own `.lance.db` directory under `databases/<user id>/` [measured: smoke, store layout]. #5254's shape, datasets sharing one LanceDB store, therefore needs `ENABLE_BACKEND_ACCESS_CONTROL=false` at v1.6.8. | [code] |
| C13 | Neo4j's default dataset handler creates one database per dataset with `CREATE DATABASE`, which Neo4j Community cannot do (`graph/neo4j_driver/Neo4jDatasetDatabaseHandler.py` L35). The community FalkorDB adapter registers its own handlers (`falkor_graph_local`, `falkor_vector_local`), which the default derivation does not pick. Rows R2 and R3 therefore run with access control off. | [code] |
| C14 | `LanceDBAdapter.VECTOR_DB_LOCK` is a `LoopAgnosticLock` per adapter instance (`LanceDBAdapter.py` L224). At v1.6.8 `delete_data_points` **does** take it, per batch of ids (L1724–1749); the lock is still process-local. `create_data_points` deduplicates ids within one call and upserts with `merge_insert("id")` under the lock (L572–656). | [code] |
| C15 | The structured-output default is `litellm_native` (`infrastructure/llm/config.py` L107). For a model litellm does not list as schema-capable it takes the JSON-object path: `response_format={"type": "json_object"}` with the Pydantic schema in a fenced block in the system prompt, plus up to three self-correcting retries (`structured_output_framework/litellm_native/native_adapter.py` L316–386, routing L388–475). The stub's model name is not listed, so that is the path the runs exercise. | [code], confirmed in every run's ledger |
| C16 | The default cognify makes **one model call per chunk**: `KnowledgeGraph` extraction. Summaries are built from the extraction (`summary_method="from_extraction"`, `modules/cognify/config.py` L22). Before the first pipeline Cognee runs a connection test that asks for the literal string `"test"` (`infrastructure/llm/utils.py` L175–190), plus an embedding test. | [code] |
| C17 | `cognify(data_per_batch=20)` is the default (`api/v1/cognify/cognify.py` L150): up to 20 data items of one call are processed concurrently in one process. C0 measures what that does to the vector store. | [code] |
| C18 | `remember` runs `add`, then `cognify`, then `improve` when `self_improvement=True`, its default (`api/v1/remember/remember.py` L1092, L1275, L1333). The harness drives `add` and `cognify` directly, as the issue repros do; `improve`'s stages need model prompts the fixture does not script. | [code] |
| C19 | **#6559's window is closed in-process at v1.6.8.** `infrastructure/files/stored_file_claims.py` keeps a file that an operation stored, and has not yet committed a row for, from removal. `remove_data_file_if_unreferenced` (`infrastructure/databases/relational/sqlalchemy/SqlAlchemyAdapter.py` L460–475) honours these claims. The module says so itself: "Process-local, like the dataset lock: two processes sharing one data root are not covered." `ingest_data` still writes the stored file (L447) well before its row commits (L649). | [code] |
| C20 | `datasets.delete_data` takes "the same per-dataset lock as pipeline runs" (`api/v1/datasets/datasets.py` L525–527; `infrastructure/locks/dataset_lock.py` L111). It returns a receipt with `deleted_nodes`, `deleted_edges` and a verified `data_remaining` (L490–506). The receipt is the extent of what it documents about derived artefacts. | [code] [docs] |
| C21 | **Support levels** come from Cognee's own words. The in-repo performance guide says: "Open-source cognee scales **vertically, in one process** … More workers or replicas against the same data are not coordinated" (`.agents/skills/cognee-performance/SKILL.md` L118–125). The API server is started with `gunicorn -w 1` (`entrypoint.sh` L57–62). The same guide describes processing several datasets at once in one process, capped by `DATASET_QUEUE_MAX_CONCURRENT` (L104–116). So: multi-process scenarios are **boundary**; concurrency across datasets in one process is **supported**; C6 is **none**. No document promises that several workers can share one dataset. | [docs] |
| C22 | Telemetry: `send_telemetry` returns at once when `TELEMETRY_DISABLED` is set (`shared/utils.py` L575). The same switch defaults dlt's own telemetry off (`tasks/ingestion/dlt_utils.py` L166). The adapter sets it before `import cognee`, and `envsetup.assert_telemetry_off` refuses to run unless the switch is set and `send_telemetry` still reads it. | [code] |
| C23 | **No network.** Every Cognee process the harness starts installs a socket guard: any connection or DNS lookup that is not loopback raises. In the first probe the guard caught tiktoken fetching `cl100k_base` from `openaipublic.blob.core.windows.net`. litellm bundles that file, but the Windows wheel (litellm 1.109.1 and 1.96.2) ships it with CRLF line endings, so tiktoken's hash check fails, it deletes the file and downloads a fresh copy. The harness keeps an LF copy whose SHA-256 matches tiktoken's expected value (`223921b7…`), and points `TIKTOKEN_CACHE_DIR` and `CUSTOM_TIKTOKEN_CACHE_DIR` at it. The guard does not reach the Ladybug and LanceDB worker processes, which do only local file I/O. | [code] [measured: probe] |
| C24 | **The FalkorDB hybrid adapter ignores the vector port.** cognee 1.6.1 passes `vector_db_port` to a registered community vector adapter (`infrastructure/databases/vector/create_vector_engine.py` L176–185 @ `eb90d03`). `FalkorDBAdapter.__init__` reads only `graph_database_port` and falls back to 6379 (`falkor_adapter.py` L87–106 @ cognee-community `ff1324ec`). So with FalkorDB on any other port, the graph instance connects and the vector instance gets "connection refused" [measured: smoke]. For R3 the harness re-registers the adapter behind a shim that copies `vector_db_port` into `graph_database_port` and changes nothing else; every run records `falkor_vector_port_shim: true`. This is a candidate finding for `topoteretes/cognee-community`. | [code] [measured] |
| C25 | **cognee 1.6.1 makes a second model call per chunk.** Before `summary_method` existed, `summarize_text` called `extract_summary(chunk.text, SummarizedContent)` once per chunk (`cognee/tasks/summarization/summarize_text.py` L55–58 @ `eb90d03`; schema `cognee/shared/data_models.py` L270). The stub answers it with a fixed string that names the chunk's tags (`stub.py`). Without that handler every R3 cognify fails with an unknown-prompt error (HTTP 400, trial invalid). | [code] |
| C26 | **Cognee's Neo4j adapter needs APOC.** It calls `apoc.create.addLabels`, `apoc.coll.toSet` and `apoc.merge.relationship` (`graph/neo4j_driver/adapter.py` L329–337, L386–395, L1245 @ `069f3cc`); without the plugin, cognify fails with `ProcedureNotFound`. The pinned `neo4j:5.26.2` image bundles APOC core (`/var/lib/neo4j/labs/apoc-5.26.2-core.jar`), and the baseline's compose file now switches it on with `NEO4J_PLUGINS=["apoc"]`; nothing is downloaded. The `neo4j` driver (5.28.8, the `neo4j` extra's range `>=5.28.0,<6`) is installed into the v1.6.8 venv and frozen in `requirements/v1.6.8.txt`. | [code] |
| C27 | **At cognee 1.6.1 on FalkorDB, `delete_data` of a document that was never cognified raises.** With no ledger rows for the document, `datasets.delete_data` falls to `legacy_delete` (`api/v1/datasets/datasets.py` L282–295 @ `eb90d03`), which calls the adapter's `get_document_subgraph` and raises `DocumentSubgraphNotFoundError` when it returns nothing (`modules/graph/methods/legacy_delete.py` L72–74). The adapter's query matches `CHUNK_OF` / `HAS_ENTITY` / `IS_INSTANCE_OF` (`falkor_adapter.py` L1498–1534 @ `ff1324ec`), which is not what Cognee 1.6.1 writes (`contains`, `is_part_of`, `is_a`), so it returns nothing. The ledger path (`delete_from_graph_and_vector.py`) deletes graph nodes with `DETACH DELETE` and no edges, so an edge whose both endpoints survive stays. Both are candidate adapter / 1.6.1 findings; §12 states what the batch measured. | [code] |
| C28 | **FalkorDB 6.0.4 truncates every result set at 10,000 rows by default** (`GRAPH.CONFIG GET RESULTSET_SIZE` returns 10000 on the pinned image), and the community adapter's `get_graph_data` asks for all nodes in one query and all edges in another (`falkor_adapter.py` L1212–1247 @ `ff1324ec`), so it returns at most 10,000 nodes and at most 10,000 edges without an error. Cognee calls `get_graph_data` where it needs the whole graph, for example to find the edge texts that remain after a delete (`modules/graph/methods/delete_from_graph_and_vector.py` L130 @ `eb90d03`). R3's first two ladders reported 10,000 nodes from the 2,500-document rung up, and 2 of 5 rungs as I2 OBSERVED (runs `20261114T191423Z-43cd092f`, `20261114T221148Z-fdf4571e`; §12). The cause was the dump, not a loss: the harness's first fix keyed on the adapter's class name, and cognee 1.6.1 hands out a `_GraphEngineHandle` that forwards attribute access (`graph/get_graph_engine.py` L61 @ `eb90d03`), so it never paged. `engine._graph_data` now keys on the row's provider and reads in pages of 5,000. On the graph the second ladder left behind, the adapter's call returned 10,000 nodes and 10,000 edges, the paged read returned 32,304 nodes and 53,905 edges, and FalkorDB's own `count()` returned the same 32,304 and 53,905. | [code] [measured] |

## 2. How the pipeline works, and where it can race

**The pipeline.** Sources are cited inline; M3 confirms the details in code.

- **`add`.** Writes the content-addressed file under the data root for the tenant or owner, runs the loader, and inserts the `Data` row at the final commit (#6559).
- **`cognify`.** Chunks the text, extracts a graph with model calls, writes graph nodes and edges, writes vectors (LanceDB `merge_insert`), and writes summaries.
- **`datasets.delete_data`.** Removes the `Data` row, deletes the stored file if nothing references it, and removes the derived graph and vector artefacts.

**Locks that exist today.**

- A per-dataset `asyncio.Lock`, effective within one process only (C7).
- A LanceDB lock per adapter instance; `delete_data_points` did not take it (C4).
- The Ladybug subprocess worker (C1).
- SQLite's own file locking.

**Race windows and limits.**

| Window | Where | Evidence |
|---|---|---|
| V1 | LanceDB writers and deletes in different processes, on one store | #5254 |
| V2 | `add` and `delete` meeting on one shared content-addressed file, across datasets | #6559 |
| V3 | Pipelines in different workers on one dataset | #4167 |
| V4 | Ladybug checkpoints and the WAL as the graph grows. This is a scale ceiling, not a race. | #6170 |

## 3. The matrix

| Row | Graph | Vector | Relational | Why |
|---|---|---|---|---|
| R1 | Ladybug 0.22.3, subprocess worker on | LanceDB 0.39.0, subprocess worker on (C11) | SQLite | the v1.6.8 default; access control at its default (on, C12) |
| R1i | Ladybug 0.22.3, `GRAPH_DATABASE_SUBPROCESS_ENABLED=false` | LanceDB | SQLite | in-process mode, as in #6170 |
| R2 | Neo4j 5.26.2 over Bolt 127.0.0.1:17687 | LanceDB | SQLite | changes only the graph store; access control off (C13) |
| R3 | FalkorDB 6.0.4 via cognee-community-hybrid-adapter-falkor 0.4.1 (git `ff1324ec`) | FalkorDB, on the graph nodes | SQLite | changes the graph and vector stores together; **cognee 1.6.1** (tag `eb90d03`), ladybug 0.19.0, lancedb 0.41.0, litellm 1.96.2, the versions the adapter's pins resolve to; access control off (C13) |
| R4 | Ladybug | LanceDB | PostgreSQL | **deferred**: M3 adds no Postgres service (master §7). #4167's advisory-lock path also needs its PR head, which is pending approval (§11). |

**Access control.** `--access-control off` sets `ENABLE_BACKEND_ACCESS_CONTROL=false`; the evidence directory then ends in `-acoff`. C2 always runs that way, because only then do datasets share a store (C12).

**R3 on 1.6.8.** Whether the adapter installs on 1.6.8 is not tested: overriding its `cognee==1.6.1` pin would be a build nobody publishes. It stays an open question (§10).

### The invariants table

The reporter builds this table from evidence ("Invariants by backend" in `evidence/M3_COGNEE.md`). It has one row per run, and each cell is k of T valid trials with a violation; the run id is in the last column. Trials that a validity gate made invalid, and what their operations raised, are in the report's next two tables.

| Row | Duplicate entities (I1 Form B) | Duplicate vector IDs (I1 Form B) | Orphan edges and dangling vectors (I4 across stores) | Lost acknowledged items (I2) | Deletion permanence (I5) | Crash ceiling (documents) | Store reopens after a crash |
|---|---|---|---|---|---|---|---|
| R1 | 0 of 14 valid disjoint trials (`20261114T141347Z-b025f668`) | C0 default: 1 of 2 cases (`20261114T131142Z-daa65b09`); with `data_per_batch=1`, 0 | 0 of 14 | 0 of 14; 0 of 5 ladder rungs (`20261114T153402Z-d2bf713f`) | 0 of 2 (`20261114T152659Z-66cfc612`); 0 of 36 (`20261114T145945Z-0fdd119f`) | none up to 5,401 | no crash to reopen; reopens read-only and read-write after the run |
| R1i | 0 of 19 (`20261114T191301Z-63ab727b`) | C0 default: 1 of 2 (`20261114T181918Z-b9974e3e`) | 0 of 19 | 0 of 19; 0 of 5 (`20261114T202544Z-f23205b5`) | 0 of 2 (`20261114T201915Z-d2b863b9`); 0 of 36 (`20261114T195002Z-d40746c3`) | none up to 5,401 | as R1 |
| R2 | 0 of 20 (`20261114T131236Z-6344cb3f`) | k4: 2 of 2 valid (`20261114T133423Z-70f45910`); `c2.writers`: 13 of 14 (`20261114T214705Z-8a40b975`); C0 default 1 of 2 (`20261114T131148Z-0fb02db6`) | 0 of 20; 0 of 14 | 0 of 20; 0 of 5 (`20261114T154821Z-2a544933`) | 0 of 14; 0 of 2 (`20261114T154636Z-4a6b3bf3`); 0 of 36 (`20261114T151804Z-ffa7ede5`) | none up to 5,401 | n/a (no Ladybug store) |
| R3 | 0 of 20 (`20261114T174759Z-d5488c9a`) | none: vectors are graph nodes, so the dump reports `_unsupported` | 0 of 20 | 0 of 20; 0 of 5 ladder rungs (`20261114T233713Z-ea3ee4af`; the two earlier R3 ladders, `20261114T191423Z-43cd092f` and `20261114T221148Z-fdf4571e`, show 2 of 5 because the dump was capped, C28) | `c6.deletion` 0 of 2 (`20261114T191322Z-30040411`); `c2.writers` and `c3.cross_process` invalid (C27) | none up to 5,401 | n/a |

## 4. Stub contract

- **Endpoint.** A single OpenAI-compatible HTTP endpoint, shared by every worker process. It serves chat completions with JSON output and an embeddings route (master §8).
- **Wiring.**
  - Model calls: `LLM_PROVIDER`, `LLM_ENDPOINT`, `LLM_MODEL`, and a dummy `LLM_API_KEY`.
  - Embeddings: `EMBEDDING_PROVIDER`, `EMBEDDING_ENDPOINT`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`.

  #6170's reporter ran this way against an OpenAI-compatible endpoint.
- **Structured output.** The stub must answer in whatever structured-output mode Cognee's LLM gateway uses at the pin (JSON schema or tool calls through litellm). M3 confirms the mode before any run. **Confirmed:** the JSON-object path, with the schema in the system prompt (C15).
- **Fixtures.** Each document carries an id tag. The fixture holds its chunks' graph extraction: entities with canonical keys, plus relations. Summaries are fixed strings. At v1.6.8 summaries come from the extraction, so no summary prompt is scripted (C16).
- **Realism check, not used for verdicts.** Cognee's local extraction path (the `gliner` extra in the README) runs once per scenario, to show that the stubbed results are not an artefact of the stub. **Not run in M3:** the GLiNER runtime and its model download from the network, which the no-network rule forbids. Open question §10.

**As built (M3).**

| Part | Where | What it does |
|---|---|---|
| Server | `core/witnessmark/stub_server.py` (standard library) | `ThreadingHTTPServer` on 127.0.0.1, serving `/v1/chat/completions`, `/v1/embeddings` and `/v1/models`. Every answer is validated against the schema the request carries (in `response_format.json_schema`, or as a fenced `json` block in the system prompt) by a small JSON-schema validator. An unknown prompt gets HTTP 400; an answer that breaks its schema gets HTTP 500. Every call, answered or not, goes in a ledger, and the run drains it. |
| Handlers | `witnessmark_cognee/stub.py` | The connection test gets `"test"`. `KnowledgeGraph` gets the fixture entities (ids are canonical names) and relations of every tagged document in the chunk. Anything else is unknown. |
| Embeddings | core | `stubs.embed(text, 256)`; the dimension is set by `EMBEDDING_DIMENSIONS=256`, and a request for any other dimension is refused |
| Wiring | `witnessmark_cognee/envsetup.py` | `LLM_PROVIDER=openai`, `LLM_MODEL=openai/witnessmark-stub`, a dummy `LLM_API_KEY`; `EMBEDDING_PROVIDER=openai_compatible` (Cognee's engine for local OpenAI-compatible servers), `EMBEDDING_MODEL=witnessmark-embed`; both endpoints point at the stub |
| Gates | `core/witnessmark/memory.py` | A trial with a stub error is invalid, and a sequential control with one is not met |

**Attribution.** HTTP calls carry no client id, so ledger entries name the document tags they served, not the operation. The overlap control counts the operations themselves.

## 5. Scenarios

### 5.0 As built in M3 (amends the designs below)

**Runner shape.** The coordinator never imports cognee: it drives a helper process over two pipes (`helper.py`). `reset` starts a fresh store root, `.state/runs/<run>/gNNNN/`, for every trial. Before every process-mode trial the runner calls the adapter's new `release()` hook (master §4.2), which stops the helper. Ladybug holds an exclusive file lock while a process has the store open, so a coordinator holding it would keep the workers out. Worker processes read the current root from a pointer file and run Cognee in-process.

**Why `data_per_batch=1`.** C0 below shows that one `cognify` call over several documents that share entities stores duplicate vector rows by itself, in one process, with nobody racing it. That happens because the call's data items run concurrently. The cross-process scenarios C1, C2, C3, C5 and C6 therefore cognify with `data_per_batch=1`, so that what they measure is the concurrency they create. C0 measures Cognee's default, and C4 keeps the default as #6170's reporter did.

**Shared store, rows R2 and R3.** With access control off every dataset reads one graph, so A's dump shows B's chunks. C3's I5 check therefore counts A's rows only when the two dumps hold the same graph: A is only ever added, never cognified, so it owns no chunk (an earlier version of the check read B's chunk as a leftover of A and failed R2's sequential control; fixed before the batch). The same cause spoiled two more checks, found in batch `m3-20261114T131136Z`: `c1.disjoint.k4`'s per-dataset exact-graph control, and `c2.writers`' relational rows (B's rows were not merged into the store it checked). Both now judge the shared store once, with every dataset's rows, and R2 and R3 re-ran them in a second batch; the first batch's runs stay in `evidence/` and the report lists both.

**Corpus sizes.** C1 uses 24 documents, not 200, to keep a 20-trial run under about half an hour. Six people, four companies and four cities recur across them. Worker i adds slice i plus the first two documents of slice i+1, so every slice overlaps the next.

| ID | Mode | Clients | Support (C21) | Basis | Trials |
|---|---|---|---|---|---|
| `c0.single_call` | one helper, one call per case | 1 | supported | documented: `create_data_points` upserts and dedups (C14) | 2 cases: `data_per_batch=1` and the default (20) |
| `c1.k{2,4,8}` | process | K adds, then K cognifies, one worker each | boundary | documented (C21) | 20 |
| `c1.disjoint.k4` | process | the same, each worker on its own dataset | boundary | documented | 20 |
| `c2.writers` | process, access control off | add+cognify A; add+cognify B; delete C (cognified in setup) | boundary | issue #5254 | 20 |
| `c3.cross_process` | process, no pause | delete A's copy; add the same bytes to B, then cognify B | boundary | issue #6559 | 36: one per declared offset, −50 to +125 ms in steps of 5 |
| `c3.in_process` | one helper | `paused` (the reporter's method) and `gather` (no pause) | supported | issue #6559 | 2 cases |
| `c5.visibility` | writer helper + reader helper (separate processes) | 10 documents, `search(CHUNKS)` | none | inferred | 10 writes |
| `c6.deletion` | one helper | `delete`, and `delete_during_cognify` (another dataset cognified meanwhile) | none | documented receipt (C20) | 2 cases |
| `c4.ladder` | one helper | 448, 1000, 1650, 2500, 5401 documents, batches of 16, `chunks_per_batch=16`, pinned `data_id`s | none | issue #6170 | 5 rungs |

**Checks that are not invariants** are kept in every trial and tabulated by the reporter:
- `ERR`: the error class of every operation that raised (Ladybug file lock, LanceDB writer conflict, SQLite locked, file not found, …).
- `C2W`: writer conflicts.
- `C2P`: partially indexed documents.
- `CRASH`: crashes on the ladder.

**Not run in M3:** memify in C2. At v1.6.8 `memify` is a deprecated shim, and its replacement `improve` needs prompts the fixture does not script. Also not run: every build that needs a pull request's code (§11).

### C0. One call, one process (new in M3; I1 Form B)

- **Procedure.** `add` and then one `cognify` over 8 documents of the C1 corpus, which share entities. Two cases, each on a fresh store: `data_per_batch=1`, and Cognee's default.
- **Why.** It separates what Cognee's own in-call concurrency does from what concurrent callers do.

### C1. Several workers ingesting one dataset (I1 Form B, I2, consistency across stores)

- **Setup.** K ∈ {2, 4, 8} worker processes share one `SYSTEM_ROOT_DIRECTORY` and `DATA_ROOT_DIRECTORY`. Each adds an overlapping slice of a 200-document corpus whose documents share entities, then runs `cognify` on the same dataset. A process barrier releases them together.
- **Controls.**
  - One worker doing all the work (sequential control).
  - K workers on disjoint datasets that use disjoint stored files.
- **Builds.** v1.6.8, the #4167 head (rows R1 and R4), and the #5253 head.
- **Checks.**
  - One graph node per canonical entity, and one vector row per id (I1 Form B).
  - Every chunk and every scripted fact of every acknowledged document is present (I2).
  - No edge has a missing endpoint, and every vector has its graph node and every graph node its vector (I4 across stores).
- **Expected.** The sequential control reproduces the fixture exactly. Concurrent runs: [unmeasured].

### C2. Concurrent vector writers (#5254)

- **Setup.** The issue's shape: two processes run `cognify` and `memify` on different datasets that share one local LanceDB store, while a third deletes data (the delete path the issue says was unlocked).
- **Checks.**
  - The count of `Too many concurrent writers` errors.
  - Documents left partially indexed.
  - Duplicate ids per collection, found by scanning the `id` column.
- **Rows.** R1 and R2 (both use LanceDB), compared with R3 (vectors in FalkorDB).
- **Builds.** v1.6.8 and the #5253 head.
- **Expected.** On #5253, zero writer conflicts and zero duplicates on a clean store, as the issue states [gh].

### C3. Add and delete racing on a shared file (I2 with `cause = delete`; #6559)

- **Setup.** The same bytes are added to dataset B while being deleted from dataset A. The race runs two ways:
  - **In-process,** reusing the reporter's pause-injection method, credited to its author.
  - **Across processes,** with two processes, no injected pause, and a declared sweep of start offsets.
- **Checks.**
  - B's acknowledged row points at files that exist, and `cognify(B)` succeeds.
  - Every artefact that belonged only to A is gone (I5).
- **Builds.** v1.6.8, then the fix pull request once it exists. #6571's test runs as published, next to ours.
- **Expected.** The issue's expected behaviour: B's add either keeps the file or fails loudly, and never commits a row that points at nothing [gh].

### C4. Scale ceiling (#6170)

- **Setup.** The issue's corpus shape: one dated sentence of about 100 characters per document, naming a business, an address and a phone number. It comes from a seeded generator, is ingested in batches of 16 `DataItem`s with pinned `data_id`s, and is cognified incrementally with `chunks_per_batch=16`.
- **Ladder.** 448, 1,000, 1,650, 2,500 and 5,401 documents. 448 is the issue's completed run and 5,401 its full corpus.
- **Measured.**
  - Crash or no crash: the signal, the size of the `.lbug` store and the node count.
  - Resident memory.
  - Time per batch.
  - Whether the store reopens afterwards, read-only and read-write.
- **Rows.** R1 and R1i on v1.6.8 with Ladybug 0.22.3. Optionally, v1.6.2 with Ladybug 0.19.0, to reproduce the original report. R2 and R3 at the same sizes.
- **Why the stub matters.** The stub makes the ladder free and deterministic, which also answers the bot's request in #6170 for minimal code.
- **Expected.** [unmeasured]. Both outcomes matter: a crash on 0.22.3, or none up to 5,401 documents.

### C5. Read your writes on `recall` and `search` (I3)

- **Procedure.** After `remember` (or `add` then `cognify`) returns, query the new facts from the same worker and from another worker.
- **Measured.** The visibility lag λ for each row.

### C6. Deletion permanence (I5)

- **Procedure.** Delete one document. In every store, check that no chunk, vector, graph node or edge derived only from it remains, while shared entities that other documents still reference stay.
- **Repeat.** Run it again with a concurrent `cognify` of another dataset that shares entities with the deleted document.
- **Note.** A delete that removes something a live document still references is reported under I2 with `cause = delete` (master §5.5).

## 6. Checks

**Canonical dumps, per store.**

| Store | What is dumped |
|---|---|
| Relational | `Data` rows: id, dataset, content hash, stored locations, and whether each file exists |
| Graph | Nodes by type and canonical key, and edges |
| Vector | Ids per collection, with a count of rows per id |
| Provenance | The document → chunks → entities mapping, so every artefact traces to its source document |

**Predicates.**

| Check | Predicate |
|---|---|
| I1 Form B | One graph node per canonical key, and one vector row per id |
| I2 | Fixture facts ⊆ the graph dump, and every acknowledged row's files exist |
| I4 across stores | The graph and vector stores hold the same set of artefacts |
| I5 | Nothing derived only from a deleted document remains |

## 7. Deliverables

| ID | Deliverable |
|---|---|
| E1 | The invariants table in §3, every cell linked to its run_id |
| E2 | Scenario tables for C1 to C6 |
| E3 | A single-file repro for each new FAIL, needing only the standard library, cognee and the stub, with the sequential control printed |
| Drafts | Kept in `drafts/` and never committed: comments for #5254, #6559, #6170 and #4167, plus one issue for each new finding |

## 8. Contribution plan (non-competing)

1. **Re-run first.** Before drafting anything, check the trackers again and re-run on `dev`.
2. **#5254 and #5253.** Post the C2 results on v1.6.8 and on the #5253 head. They cover the cross-process writers and deletes the reporter asked tests to cover.
3. **#6559 and #6571.** Offer the cross-process variant, which needs no injected pause, as extra coverage. The reporter is writing the fix, so there is no fix pull request from us.
4. **#6170.** Post the C4 ladder on v1.6.8 with Ladybug 0.22.3 and the stub, as runnable minimal code that needs no API key.
5. **#4167.** Post the C1 results for `dev` and for the #4167 head, covering the SQLite file lock (R1) and the PostgreSQL advisory lock (R4).
6. **Adapter findings.** Anything specific to the FalkorDB adapter goes to `topoteretes/cognee-community`, with a note about its `cognee==1.6.1` pin.
7. **New findings.** Open one issue per finding, each with a minimal repro. Open a pull request only against `dev`, with DCO sign-off, and only after a maintainer asks (C9; master §11).

## 9. Exit and drop rule

- **All clean.** If C1 to C3 come out clean on R1 with valid controls, publish the invariants table and credit the project.
- **C4 stands on its own.** Its result is useful either way.
- **Sequential control fails.** If C1's sequential control does not reproduce the fixture on some row, that row is INVALID until the fixture or stub is fixed.

## 10. Open questions

| Question | Settled in |
|---|---|
| Does `remember` at v1.6.8 wrap `add` and `cognify`, or does it take a different path? | **Answered (C18):** `add`, `cognify`, then `improve` |
| Which adapter does `GRAPH_DATABASE_PROVIDER="kuzu"` (the `.env.template` value) select at v1.6.8: Kuzu or Ladybug? | **Answered (C10):** Ladybug |
| How does the provided Docker Compose run several API workers? This decides whether the FastAPI-worker setup is a fifth execution mode. | **Answered (C21):** it does not; `entrypoint.sh` runs `gunicorn -w 1`. No fifth mode. |
| Which structured-output mode does the LLM gateway use? | **Answered (C15)** |
| Does Cognee's conflict handling (`api/v1/conflicts`) make I7 applicable? Until shown otherwise, I7 is NOT_APPLICABLE. | Still open: conflict review is an `improve` stage that needs scripted prompts. I7 stays NOT_APPLICABLE. |
| Does the community FalkorDB adapter install on cognee 1.6.8? | Open, for the maintainer: testing it means overriding the adapter's `cognee==1.6.1` pin, a build nobody publishes. M3 ran the pinned 1.6.1. |
| Should the GLiNER realism check run? It needs the `gliner` runtime and a model download. | Open, for the maintainer: it conflicts with the no-network rule |
| R4 (PostgreSQL) | Deferred: needs a pinned Postgres service in `baselines/` and #4167's head |
| Should C3 on R3 cognify A in its setup, so that `delete_data` takes the ledger path and R3 yields a cross-process measurement of #6559? Today the delete of a never-cognified document raises on cognee 1.6.1 + the FalkorDB adapter (C27), so the control is not met | Open, for the maintainer: it changes C3's fixture on one row only |
| Should C2's fixture give the deleted documents an entity of their own, so that R3's control is not tripped by the edge that 1.6.1's delete leaves between two shared entities (C27)? That would hide the behaviour from C2; C6 does not exercise it | Open, for the maintainer |
| Are the R2 `AfterRunHookError`s (LanceDB compaction commit conflicts across processes) a finding for `topoteretes/cognee`, and does #5253 change them? | Open: needs the #5253 head (§11) |

## 11. Pull-request builds pending approval

Installing or running third-party pull-request code needs the maintainer's explicit yes. None of these builds was installed or run in M3. Heads as of 2026-11-14:

| PR | Head | Would run | Status |
|---|---|---|---|
| [#5253](https://github.com/topoteretes/cognee/pull/5253) | `599ae0110bf5ddf4d6865f586e1887ea5f99a1fa` | C2 on R1 and R2, C1 | pending approval |
| [#4167](https://github.com/topoteretes/cognee/pull/4167) | `87301c704d1a8b660b481e3b12e5796d91ae44f4` | C1 on R1 (SQLite file lock) and R4 (advisory lock) | pending approval |
| [#6571](https://github.com/topoteretes/cognee/pull/6571) | `9455c4c7043d8b59a28921fcdd3947ccb4867a7e` | its own regression test, next to C3 | pending approval |

## 12. Results (M3)

**Provenance.** Four batches on this host (Windows 11, 11th Gen i5-11320H, 8 logical cores, 23.8 GB), 20 trials per race, 36 for the cross-process C3. Every number below is [measured] and comes from a report that is regenerated from `evidence/` and cmp-verified:

| Batch | Report | Harness commit | What it holds |
|---|---|---|---|
| `m3-20261114T131136Z` | [evidence/M3_COGNEE.md](../../evidence/M3_COGNEE.md) | `1fd4dd0` | the matrix: C0 to C6 on R1, R1i, R2, R3 |
| `m3b-20261114T204628Z` | [evidence/M3_COGNEE_B2.md](../../evidence/M3_COGNEE_B2.md) | `f3dbe98` | re-runs after a harness bug on shared stores (below) |
| `m3c-20261114T221140Z` | [evidence/M3_COGNEE_B3.md](../../evidence/M3_COGNEE_B3.md) | `84dcdb7` | R3 ladder, first fix of the FalkorDB dump (did not take effect) |
| `m3d-20261114T233706Z` | [evidence/M3_COGNEE_B4.md](../../evidence/M3_COGNEE_B4.md) | `5747966` | R3 ladder with the dump paging as intended |

**Why there are four batches.** Nothing was re-run to change a result; every re-run followed a harness fix that was committed first, and the earlier runs stay in `evidence/` and in the reports.

| Re-run | Cause | Where |
|---|---|---|
| R2 `c1.k8` | Batch 1's run crashed at the dump of trial 19: Cognee's LanceDB worker subprocess exited before it signalled ready (60 s). `ERROR.md` is kept at `evidence/cognee/v1.6.8.R2-acoff/c1.k8.process/20261114T140306Z-9f88c9a1/`. Not a harness bug; re-run with the same code | batch 2 |
| R2 and R3 `c1.disjoint.k4`, R2 and R3 `c2.writers` | Harness bug: with access control off every dataset reads one graph, so the per-dataset control of `c1.disjoint.k4` saw every slice and `c2.writers` read B's relational rows as missing. R2's batch-1 `c2.writers` "I2 BOUNDARY 12/12" and R3's "I2 INVALID 16/16" are that bug, not findings. Fixed in `f3dbe98` | batch 2 |
| R3 `c4.ladder` | Harness bug in the dump: FalkorDB 6.0.4 truncates result sets at 10,000 rows and the adapter's `get_graph_data` does not page (C28), so the dump showed 10,000 nodes from the 2,500-document rung up and I2 OBSERVED on 2 of 5 rungs. The first fix (`84dcdb7`) keyed on a class name that cognee 1.6.1's `_GraphEngineHandle` hides, so it still showed 10,000; fixed in `5747966` | batches 3 and 4 |

Earlier in the session the harness also gained, before any batch: the `SummarizedContent` stub handler for cognee 1.6.1 (C25), APOC for Neo4j and the `neo4j` driver in the v1.6.8 environment (C26), and a fix to C3's I5 check on shared stores (`1fd4dd0`).

**Ladybug support boundary.** [measured] Every multi-process run here that put concurrent workers on one Ladybug store reached a BOUNDARY. Each had 0 of 20 valid trials and ERR class `ladybug file lock`. In scenario order `c1.k2`, `c1.k4`, `c1.k8`, then `c2.writers` (access control off), the runs were R1 `20261114T131228Z-5b47435a`, `20261114T132931Z-134a3280`, `20261114T134920Z-186e234c`, `20261114T143808Z-c442cc14` and R1i `20261114T182011Z-03b8761e`, `20261114T183831Z-97e05ac3`, `20261114T185431Z-95507ca8`, `20261114T193043Z-188df5a9`. The reports show `INVALID` because the lock errors took the unknown-outcome rate above the 5% validity gate. [code] Cognee's performance guide scopes open-source use against one store to one process (C21, `.agents/skills/cognee-performance/SKILL.md:118–125@069f3cc`).

### Controls

The sequential control is the exit criterion (master §9): with nothing racing, the fixture graph comes out exactly as specified.

| Scenario | R1 | R1i | R2 | R3 |
|---|---|---|---|---|
| `c1.k2`, `c1.k4`, `c1.k8` | met | met | met | met |
| `c1.disjoint.k4` | met | met | met (batch 2) | met (batch 2) |
| `c2.writers` | met | met | met (batch 2) | **NOT met** |
| `c3.cross_process` | met | met | met | **NOT met** |

22 of the 24 final race runs met their control, and the primary scenario `c1.k2` met it on all four rows. The two that did not are R3 under cognee 1.6.1, and both come from Cognee's behaviour, not the harness:

- **R3 `c2.writers`** (runs `20261114T183825Z-c97d0d06` before the fix, `20261114T210439Z-c2c55f16` after): the control observes `relations 14 (want 13, one each)` in both. After the delete of C, one relation between two entities that A and B still reference stays in the graph. At 1.6.1 the ledger path deletes graph nodes with `DETACH DELETE` and no edges (C27), so an edge whose endpoints both survive is not removed. On R1, R2 at 1.6.8 the same control is met.
- **R3 `c3.cross_process`** (`20261114T185051Z-97edaf64`) and one `c3.in_process` case (`20261114T191258Z-e09326c6`): `delete_data` of a document that was only added raises `DocumentSubgraphNotFoundError` (C27). R3 therefore has no cross-process C3 measurement; it is INVALID by rule (master §9), and a variant that cognifies A in setup is an open question (§10).

### Results

| Scenario | R1 (Ladybug) | R1i (Ladybug, in process) | R2 (Neo4j + LanceDB) | R3 (FalkorDB, 1.6.1) | Verdict |
|---|---|---|---|---|---|
| C0, one call, `data_per_batch=1` | 0 duplicates | 0 | 0 | 0 | PASS |
| C0, one call, default (20) | duplicate vector ids: `EntityType_name` up to 4 rows per id, `Entity_name` and `EdgeType_relationship_name` up to 2 | same | `EntityType_name` up to 8, the others up to 2 | none (vectors are graph nodes) | FAIL on a supported path (C0's basis is documented, §5.0): in one process with nothing racing |
| C1, K workers, one dataset (k2, k4, k8) | 0 of 20 trials valid in each: the second worker fails with `Could not set lock on file ….lbug` | same | k2: 20 of 20 valid, 0 violations. k4: 2 of 20 valid, both with duplicate vector ids (up to 3 rows per id); 18 of 20 raised `AfterRunHookError`. k8: 0 of 20 valid, `AfterRunHookError` in all 20 | k2: 20 of 20, k4: 20 of 20, k8: 17 of 20 valid; 0 violations | R1, R1i: BOUNDARY (C21), no measurement. R2: BOUNDARY. R3: PASS |
| C1 disjoint (4 datasets) | 14 of 20 valid, 0 violations | 19 of 20, 0 | 5 of 20 valid, 0 (the rest `AfterRunHookError`) | 15 of 20, 0 | PASS |
| C2, two writers and a delete | 0 of 20 valid (lock) | 0 of 20 (lock) | 14 of 20 valid: duplicate vector ids in 13 (up to 2 rows per id in `Entity_name`, `EntityType_name`, `EdgeType_relationship_name`); I2, I4, I5 hold; no `Too many concurrent writers`; 6 of 20 `AfterRunHookError` | control not met | R2: BOUNDARY. R1, R1i: no measurement |
| C3 cross-process, 36 offsets (−50 to +125 ms) | 36 of 36 valid; B's row and files exist, A's copy gone, in all | 36 of 36, same | 36 of 36, same | control not met | no violation at any declared offset on the three rows that ran it |
| C3 in process (`paused`, `gather`) | both cases PASS | both PASS | both PASS | `paused` invalid (its delete raises); `gather`: I2 holds, but its delete raised too, so I5 was not checked | PASS (R1, R1i, R2) |
| C5, read your writes | same instance 10 of 10; a second process: 0 of 10 within 30 s, its searches raised the file lock | same | 10 of 10 on both | 10 of 10 on both | OBSERVED (R1, R1i); PASS (R2, R3) |
| C6, deletion permanence | I5 and I2 hold, both cases | same | same | same | PASS |
| C4, ladder to 5,401 documents | no crash, no I2 loss | no crash, no I2 loss | no crash, no I2 loss | no crash, no I2 loss; node counts equal R1's and R2's at every rung | PASS |

**Credit.** On the supported path the project's code holds up in these runs: 14 and 19 valid disjoint-dataset trials with no duplicate and nothing lost on the Ladybug rows; C3's cross-process window found nothing at any of 36 declared offsets on three rows (consistent with, and not proof of, v1.6.8's in-process claim registry, C19) [inference]; deletion leaves nothing behind and keeps shared entities on all four rows; and the 5,401-document ladder completed on every row, with each reopened Ladybug store (R1, R1i) readable and writable afterwards.

### Findings

Each is [measured] with the run id; causes are [code] or [inference] as marked.

1. **One `cognify` over documents that share entities stores duplicate vector rows, with nothing racing** (C0; runs `20261114T131142Z-daa65b09` (R1), `20261114T181918Z-b9974e3e` (R1i), `20261114T131148Z-0fb02db6` (R2)). With `data_per_batch=1` there are none. The default is 20 (C17); the duplicates sit in LanceDB (`merge_insert` upsert, C14) [inference: the call's concurrently processed data items upsert the same ids]. This is why the other scenarios use `data_per_batch=1`.
2. **Ladybug allows one process per store.** Every multi-worker scenario on one dataset fails with `IO exception: Could not set lock on file …` (R1 and R1i, `c1.k2`/`k4`/`k8`, `c2.writers`), and a second process cannot search while the writer holds the store (C5). Cognee's own guide scopes open source to one process (C21), so this is a support boundary, not a defect.
3. **R2 (Neo4j + LanceDB), several processes on one dataset: `cognify` raises after the data is stored.** The error is `AfterRunHookError … LanceDB compaction failed … OSError('Retryable commit conflict … This Rewrite transaction was preempted by concurrent transaction Rewrite')` (runs `20261114T204652Z-d5f2e1c9` and `20261114T133423Z-70f45910`, 20 of 20 and 18 of 20 trials). The harness scores those operations as unknown outcomes and the trials as invalid; the trials that are valid show duplicate vector ids (`c1.k4`, 2 of 2) [inference: the same process-local LanceDB lock gap as #5254, C14].
4. **R2 `c2.writers`: duplicate vector ids with concurrent writers on a shared LanceDB store** (`20261114T214705Z-8a40b975`, 13 of 14 valid trials). I2, I4 and I5 hold, and there is no `Too many concurrent writers` error, which is the symptom #5254 reports.
5. **cognee 1.6.1 on FalkorDB: delete leaves an edge, and delete of a never-cognified document raises** (C27; runs above). Candidate findings for `topoteretes/cognee` and `cognee-community`.
6. **FalkorDB 6.0.4's result limit silently truncates the adapter's `get_graph_data`** (C28). On the graph the second ladder left behind, the adapter's call returned 10,000 nodes and 10,000 edges; FalkorDB held 32,304 and 53,905.
7. **The vector-port shim** (C24) was needed and recorded in every R3 run (`falkor_vector_port_shim: true`).
8. **#6170 (SIGSEGV near 1,650 documents) did not reproduce** on v1.6.8 with Ladybug 0.22.3, either as the subprocess worker (R1) or in process (R1i), up to 5,401 documents, with the stub and the issue's corpus shape. Total elapsed: R1 9,838.7 s, R1i 9,487.8 s, R2 7,126.6 s, R3 4,275.3 s (`20261114T233713Z-ea3ee4af`); worker memory at 5,401 documents: 2,694 MB (R1), 2,331 MB (R1i), 2,193 MB (R2); the helper's peak was 604 MB (R1), 984 MB (R1i), 629 MB (R2) and 445 MB (R3). Every row counted the same 32,304 nodes and 16,098 entities at 5,401 documents. The original build (cognee 1.6.2, Ladybug 0.19.0) was not run, so whether 0.22.3 fixed it or the stub's shape differs is [unmeasured]. Both reopened Ladybug stores (R1, R1i) read 32,306 nodes against 32,304 counted by the ladder; the two extra are unexplained [unmeasured].

### The invariants table (§3)

The table in §3 is filled from these reports; each cell names its run.

### Not run, and open

- **Deferred:** R4 (PostgreSQL), memify in C2 (§5.0), the GLiNER realism check (§4). Nothing that needs a pull request's code ran (§11).
- **E3 (single-file repros) was not written in M3.** The candidates are C27 (R3 delete), the R2 `AfterRunHookError` under concurrent processes, and C0's default-path duplicates.
- **Invalid trials.** The reports' "Invalid trials" tables list, per run, the trials a validity gate removed (release spread over 1 ms for processes, an operation with an unknown outcome) and why. Verdict cells count valid trials only.
