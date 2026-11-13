# Target 02: Cognee (topoteretes/cognee)

Part of Witnessmark. Read it together with the [master blueprint](../../MASTER_BLUEPRINT.md); "master §n" refers to a section there.

| | |
|---|---|
| Status | Specification v0.1, 2026-11-13. Nothing has been measured, so every expectation below is [unmeasured] until a run says otherwise. |
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
| R1 | Ladybug 0.22.3, subprocess worker on | LanceDB 0.39.x | SQLite | the v1.6.8 default |
| R1i | Ladybug 0.22.3, `GRAPH_DATABASE_SUBPROCESS_ENABLED=false` | LanceDB | SQLite | in-process mode, as in #6170 |
| R2 | Neo4j 5.26.2 | LanceDB | SQLite | changes only the graph store |
| R3 | FalkorDB 6.0.4 (community hybrid adapter) | FalkorDB | SQLite | changes the graph and vector stores together. The adapter pins cognee 1.6.1, so this row runs on 1.6.1, unless an override of that pin installs cleanly on 1.6.8; whichever version runs is recorded. |
| R4 | Ladybug | LanceDB | PostgreSQL | needed to test #4167's advisory-lock path |

### The invariants table

C1 to C6 in §5 fill this table: one row per matrix row, one cell per check, each cell holding k of T plus its run_id.

| Row | Duplicate entities (I1 Form B) | Duplicate vector IDs (I1 Form B) | Orphan edges and dangling vectors (I4 across stores) | Lost acknowledged items (I2) | Deletion permanence (I5) | Crash ceiling (documents) | Store reopens after a crash |
|---|---|---|---|---|---|---|---|
| R1 … R4 | | | | | | | |

## 4. Stub contract

- **Endpoint.** A single OpenAI-compatible HTTP endpoint, shared by every worker process. It serves chat completions with JSON output and an embeddings route (master §8).
- **Wiring.**
  - Model calls: `LLM_PROVIDER`, `LLM_ENDPOINT`, `LLM_MODEL`, and a dummy `LLM_API_KEY`.
  - Embeddings: `EMBEDDING_PROVIDER`, `EMBEDDING_ENDPOINT`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`.

  #6170's reporter ran this way against an OpenAI-compatible endpoint.
- **Structured output.** The stub must answer in whatever structured-output mode Cognee's LLM gateway uses at the pin (JSON schema or tool calls through litellm). M3 confirms the mode before any run.
- **Fixtures.** Each document carries an id tag. The fixture holds its chunks' graph extraction: entities with canonical keys, plus relations. Summaries are fixed strings.
- **Realism check, not used for verdicts.** Cognee's local extraction path (the `gliner` extra in the README) runs once per scenario, to show that the stubbed results are not an artefact of the stub.

## 5. Scenarios

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
| Does `remember` at v1.6.8 wrap `add` and `cognify`, or does it take a different path? | Read in M3 |
| Which adapter does `GRAPH_DATABASE_PROVIDER="kuzu"` (the `.env.template` value) select at v1.6.8: Kuzu or Ladybug? | Read in M3 |
| How does the provided Docker Compose run several API workers? This decides whether the FastAPI-worker setup is a fifth execution mode. | M3 |
| Which structured-output mode does the LLM gateway use? | M3 |
| Does Cognee's conflict handling (`api/v1/conflicts`) make I7 applicable? Until shown otherwise, I7 is NOT_APPLICABLE. | M3 |
| Does the community FalkorDB adapter install on cognee 1.6.8? | M3 |
