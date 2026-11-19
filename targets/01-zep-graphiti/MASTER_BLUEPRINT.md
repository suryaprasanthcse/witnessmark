# Target 01: Graphiti (getzep/graphiti)

Part of Witnessmark. Read it together with the [master blueprint](../../MASTER_BLUEPRINT.md). "Master §n" refers to that document.

| | |
|---|---|
| Status | Specification v0.2, 2026-11-13. Implemented in M2. Results are in §11 and [evidence/M2_GRAPHITI.md](../../evidence/M2_GRAPHITI.md). M5 Phase C: the G6–G8 run plan and its amendments are in §5; the results are in §12 and [evidence/M5_GRAPHITI.md](../../evidence/M5_GRAPHITI.md), with [evidence/M5_GRAPHITI_B1.md](../../evidence/M5_GRAPHITI_B1.md) for the G7 control. Phase C is signed off (maintainer, 2026-11-16); M5 reviewed and signed off on 2026-11-16. A finding counts only when a run in `evidence/` backs it. |
| Project | [getzep/graphiti](https://github.com/getzep/graphiti), Apache-2.0. A Python framework that keeps a temporal knowledge graph in Neo4j, FalkorDB, Kuzu or Neptune. |
| Line under test | graphiti-core v0.31.x. Primary pin: **v0.31.2**, tag commit `d72407dcedac911e1be9fc15b55e8c05a3efcc36` (2026-10-20), which is also the current PyPI release. |
| Other builds | main at `ebef986a0b2360211b65751c111cacb4a7d790eb` (2026-11-11); [#1867](https://github.com/getzep/graphiti/pull/1867) at head `a30934e18b9582fbea3aca742269fc2174b67f07`; [#2119](https://github.com/getzep/graphiti/pull/2119) at head `b2b727e05467346b6516e2c68e193f8142ef208b` |
| Backends | FalkorDB 6.0.4 and Neo4j 5.26.2 (master §7) |
| Models | Deterministic stubs (§4); no API keys, no network calls |
| Code | `witnessmark_graphiti/` (adapter, stubs, fixtures, scenarios), `wm_graphiti.py` (entry point), `requirements/` (frozen environments) |
| Out of scope | Kuzu (archived upstream), Neptune, the hosted Zep service |

All source links point at the v0.31.2 tag.

## 1. What is already known

### 1.1 Before M2

| # | Fact | Tag |
|---|---|---|
| K1 | The README describes the ingestion pipelines as designed for high concurrency. It sets the default concurrency low to avoid LLM rate limits; `SEMAPHORE_LIMIT` defaults to 10 ([README.md L255–264](https://github.com/getzep/graphiti/blob/v0.31.2/README.md#L255-L264)). | [docs] |
| K2 | The MCP server processes one group's episodes sequentially; the code comment says this avoids race conditions ([graphiti_mcp_server.py L421](https://github.com/getzep/graphiti/blob/v0.31.2/mcp_server/src/graphiti_mcp_server.py#L421)). The queue is an in-process `asyncio.Queue` per `group_id` ([queue_service.py L12–49](https://github.com/getzep/graphiti/blob/v0.31.2/mcp_server/src/services/queue_service.py#L12-L49)). | [code] |
| K4 | A concurrency fix already exists in this code path. `_resolve_request_scope` ([graphiti.py L1304–1332](https://github.com/getzep/graphiti/blob/v0.31.2/graphiti_core/graphiti.py#L1304-L1332)) replaced the reassignment of a shared driver. According to its docstring, that reassignment let concurrent calls for different groups persist episodes in the wrong graph (#1676). | [code] |
| K5 | `_apply_temporal_invalidation` sets `expired_at = now` for any edge that has an `invalid_at` ([edge_operations.py L727–728](https://github.com/getzep/graphiti/blob/v0.31.2/graphiti_core/utils/maintenance/edge_operations.py#L727-L728)). The loop over later candidates runs only while `expired_at` is still unset (L731–743). | [code] |
| K6 | [getzep/graphiti#2012](https://github.com/getzep/graphiti/issues/2012) (open) reports that edges with a future `invalid_at` are created already expired. A community member (Adam13y) published known-answer cases R1–R4. On v0.31.1 the results were R1 pass, R2 fail, R3 pass, R4 fail. On #1867 at `a30934e` only R3 passed. Maintainers have not yet said what `expired_at` should mean when a future end of validity is known. | [gh] |
| K7 | [getzep/graphiti#1867](https://github.com/getzep/graphiti/pull/1867) (open; GitHub reports merge conflicts) closes [#1865](https://github.com/getzep/graphiti/issues/1865): temporal deduplication collapses disjoint occurrences. | [gh] |
| K8 | [getzep/graphiti#1166](https://github.com/getzep/graphiti/issues/1166) (open): node attributes have no temporal versioning. | [gh] |
| K9 | `FalkorDriver` starts `build_indices_and_constraints` as a background task in its constructor (falkordb_driver.py L178–184), and every `clone(database=…)` constructs a new driver. [getzep/graphiti#2119](https://github.com/getzep/graphiti/pull/2119) (open, fixes #1643) awaits that task before queries. | [code] [gh] |
| K10 | On FalkorDB, each non-default `group_id` is a separate graph (falkordb_driver.py L334–347). On Neo4j every group lives in one database, as a property (the base driver's `clone` returns the same driver). | [code] |
| K11 | The root [docker-compose.yml](https://github.com/getzep/graphiti/blob/v0.31.2/docker-compose.yml) mounts the FalkorDB volume at `/data` (L56). The MCP compose file mounts it at `/var/lib/falkordb/data` ([docker-compose-falkordb.yml L11](https://github.com/getzep/graphiti/blob/v0.31.2/mcp_server/docker/docker-compose-falkordb.yml#L11)). G7 measures which one keeps data. | [code] [inference] |
| K12 | [getzep/graphiti#2117](https://github.com/getzep/graphiti/issues/2117) (open): FalkorDB data is lost when the MCP containers restart. | [gh] |
| K13 | [getzep/graphiti#2142](https://github.com/getzep/graphiti/issues/2142) (open): a FalkorDB fulltext query fails on a lone `_` token. [getzep/graphiti#2021](https://github.com/getzep/graphiti/issues/2021) (open): FalkorDB reads return the full embedding, which the parser then discards. | [gh] |
| K14 | Contribution rules: file an issue first; feature pull requests need `rfc-approved`; a CLA is signed when the bot asks ([CONTRIBUTING.md](https://github.com/getzep/graphiti/blob/v0.31.2/CONTRIBUTING.md)). | [docs] |

### 1.2 Learned while building M2

| # | Fact | Tag |
|---|---|---|
| K15 | `add_episode`'s docstring asks callers to add episodes sequentially, each awaited before the next ([graphiti.py L1410–1413](https://github.com/getzep/graphiti/blob/v0.31.2/graphiti_core/graphiti.py#L1410-L1413)). Concurrent ingest into **one group** is therefore outside the documented contract. Concurrent calls for **different groups** are supported: the #1676 fix exists for them (L1427–1429). | [docs] [code] |
| K16 | `add_triplet` reads, searches and writes through `self.driver` and `self.clients` (L2047–2171), not through the request scope that `add_episode` uses. On FalkorDB, where a group is its own graph, a triplet for group g would therefore land in the default graph. | [code], measured in G3 |
| K17 | `Graphiti.search` sets `.limit = num_results` on the module-level `EDGE_HYBRID_SEARCH_RRF` object ([graphiti.py L1955–1958](https://github.com/getzep/graphiti/blob/v0.31.2/graphiti_core/graphiti.py#L1955-L1958)). `add_episode`'s duplicate and contradiction searches read the same object ([edge_operations.py L532, L564](https://github.com/getzep/graphiti/blob/v0.31.2/graphiti_core/utils/maintenance/edge_operations.py#L532)). A read can therefore change how later writes detect contradictions. | [code], measured in G5 |
| K18 | `FalkorDriver` builds the falkordb client with redis-py's defaults: a pool of 100 connections that raises `MaxConnectionsError` ("Too many connections") when all are busy, instead of waiting. Neo4j's driver waits for a free connection. | [code], observed in G1 |
| K19 | graphiti-core 0.31.2 imports `httpx` (llm_client/client.py) without declaring it. With openai 3.x, which no longer depends on httpx, `import graphiti_core` fails until httpx is installed by hand. A commenter on #2012 hit the same thing. | [code] [measured: install] |
| K20 | Graphiti sends anonymous telemetry (PostHog) unless `GRAPHITI_TELEMETRY_ENABLED` is off. The adapter switches it off before importing graphiti_core, and refuses to run if the switch did not take. | [code] |

### 1.3 Learned while preparing M5 Phase C (2026-11-16)

| # | Fact | Tag |
|---|---|---|
| K21 | [#2119](https://github.com/getzep/graphiti/pull/2119) (open, fixes #1643; author Tyagiquamar) still had head `b2b727e05467346b6516e2c68e193f8142ef208b` on 2026-11-16, the pinned head; it had not moved. Its diff against its base `7e0342a4` changes two files. `graphiti_core/driver/falkordb_driver.py` gains 22 lines: `execute_query` now first awaits `_await_initialized()` ([falkordb_driver.py L239](https://github.com/getzep/graphiti/blob/b2b727e05467346b6516e2c68e193f8142ef208b/graphiti_core/driver/falkordb_driver.py#L239)), and that helper ([L273–292](https://github.com/getzep/graphiti/blob/b2b727e05467346b6516e2c68e193f8142ef208b/graphiti_core/driver/falkordb_driver.py#L273-L292)) returns at once when there is no build task, when the task is the one running (the build's own queries), or when it is done (it then retrieves the task's exception). Otherwise it awaits the task and logs a failed build instead of raising. `tests/driver/test_falkordb_driver.py` gains one unit test (34 lines). Nothing else changes, so the change stays on K9's path. | [gh] [code] |
| K22 | #2119's head is a merge of its base into the branch. GitHub's compare of `b2b727e0…ebef986a` lists one changed file, `signatures/version1/cla.json` [gh], and the installed trees agree: graphiti_core at #2119's head is main `ebef986a` plus `falkordb_driver.py` alone [code: diff of the two environments' graphiti_core]. Between v0.31.2 and main, graphiti_core differs only in four `llm_client/` files: a removed `DEFAULT_TEMPERATURE` constant and Anthropic model names [code: diff of the v0.31.2 and main environments]. The stubs replace the model clients, so G6–G8 run the same driver and pipeline code on v0.31.2 and main [inference]. | [gh] [code] [inference] |
| K23 | `Neo4jDriver`'s constructor also schedules `build_indices_and_constraints` as a background task ([neo4j_driver.py L92–97](https://github.com/getzep/graphiti/blob/v0.31.2/graphiti_core/driver/neo4j_driver.py#L92-L97)). Neo4j's `clone` is the base class's, which returns the same driver ([driver.py L131–133](https://github.com/getzep/graphiti/blob/v0.31.2/graphiti_core/driver/driver.py#L131-L133)), so a Neo4j group never starts a build of its own. | [code] |
| K24 | `Graphiti.search` is wrapped by `handle_multiple_group_ids` ([graphiti.py L1912](https://github.com/getzep/graphiti/blob/v0.31.2/graphiti_core/graphiti.py#L1912)). On FalkorDB a single group id is routed to a call-scoped `driver.clone(database=gid)` ([decorators.py L60–67](https://github.com/getzep/graphiti/blob/v0.31.2/graphiti_core/decorators.py#L60-L67)), so every search for a group constructs a `FalkorDriver`, which starts an index build on that group's graph (K9). | [code] |
| K25 | `remove_episode` reads and deletes through `self.driver` ([graphiti.py L2174–2213](https://github.com/getzep/graphiti/blob/v0.31.2/graphiti_core/graphiti.py#L2174-L2213)), not through the request scope `add_episode` uses. On FalkorDB that reaches only the driver's own graph, so G8 binds the driver to the group's graph there. | [code] |
| K26 | The pinned FalkorDB 6.0.4 image starts `redis-server --dir /var/lib/falkordb/data --loadmodule … ${FALKORDB_ARGS}`, with `FALKORDB_ARGS` defaulting to `MAX_QUEUED_QUERIES 25 TIMEOUT 1000 RESULTSET_SIZE 10000`. Its `/data` is a symbolic link to `/var/lib/falkordb/data`. The running baseline reports `appendonly no`, `appendfsync everysec` and `save 3600 1 300 100 60 10000`. G7 records these settings in every run. | [code: `/var/lib/falkordb/bin/run.sh` and the image's environment, read from the pinned image] |

## 2. How ingestion works, and where it can race

`add_episode` resolves a per-call driver for the group, retrieves previous episodes, then runs these steps:

1. **`extract_nodes`.** Model call `extract_nodes.extract_message`.
2. **`resolve_extracted_nodes`.** It looks for candidates by exact name, then by embedding similarity. If exactly one existing node has the same normalised name, it resolves deterministically. If two or more do, or a short name has no exact match, it asks the model (`dedupe_nodes.nodes`).
3. **`extract_edges`.** Model call `extract_edges.edge`, which carries `valid_at` and `invalid_at`.
4. **`resolve_extracted_edges`.** Two hybrid searches (BM25 and cosine), both through the shared `EDGE_HYBRID_SEARCH_RRF` config:
   - related edges: the same endpoint pair;
   - invalidation candidates: anywhere in the group.

   Then one model call, `dedupe_edges.resolve_edge`, followed by `_apply_temporal_invalidation`.
5. **Summaries.** Edge facts are appended to node summaries. The model (`extract_nodes.extract_summaries_batch`) is called only when a summary grows too long.
6. **`add_nodes_and_edges_bulk`.** The write.

`add_episode_bulk` uses one combined prompt (`extract_nodes_and_edges.extract_message`) and one batched timestamps prompt. `add_triplet` skips extraction and calls only the dedupe prompts.

| Window | Steps | What can go wrong |
|---|---|---|
| W1, entities | 2 → 6 | Two episodes look for the same new entity, both find nothing, and both create it. |
| W2, facts | 4 → 6 | Two contradicting facts each search before the other is written. Neither invalidates the other. |

Neither backend's per-statement guarantee covers these windows, because the search, the model call and the write are separate statements.

## 3. Environment and pins

| Component | Pin |
|---|---|
| graphiti-core | v0.31.2 from PyPI; main and #1867 from git at the commits above. Each build lives in its own venv under `.state/venvs/`; `requirements/<build>.txt` freezes every package. |
| Extra dependency | `httpx` 0.28.1, which graphiti-core needs but does not declare (K19) |
| Python | CPython 3.12.14 (the package requires ≥3.10 and <4) |
| FalkorDB | 6.0.4 by digest (master §7.2). The adapter gives the falkordb client a **waiting** pool: 100 connections, like the default, but a caller waits instead of failing (K18). One G1 run uses Graphiti's own default pool, to record what that does. |
| Neo4j | 5.26.2 Community over Bolt (port 17687), with the driver's default pool |
| Telemetry | Off (K20) |

## 4. Stub contract

The stubs live in `witnessmark_graphiti/stubs.py`.

**LLM.** `StubLLM` subclasses `LLMClient` and overrides `generate_response`, which Graphiti calls with `prompt_name` and `response_model`.

- Each prompt has a handler. A handler reads the context Graphiti rendered into the prompt: the tagged sections such as `<CURRENT MESSAGE>`, `<ENTITIES>`, `<EXISTING FACTS>` and `<NEW FACT>`.
- Every answer is validated against `response_model` before it is returned.
- A prompt without a handler fails the run.

| Prompts at v0.31.2 | Answer |
|---|---|
| `extract_nodes.extract_message`, `extract_text`, `extract_json` | The current episode's fixture entities. Previous episodes in the prompt are ignored. |
| `extract_edges.edge` | The current episode's fixture facts, with their dates |
| `extract_nodes_and_edges.extract_message` | Entities and facts for every tagged episode in the current messages (bulk path) |
| `extract_edges.extract_timestamps`, `extract_timestamps_batch` | The fixture dates of the fact(s) named in the prompt |
| `dedupe_nodes.nodes`, `dedupe_nodes.node` | The candidate whose canonical key matches, otherwise none |
| `dedupe_edges.resolve_edge` | **Duplicates:** the same assertion. **Contradictions:** the same functional key with a different value. Both judged only among the facts the prompt lists. |
| Summary prompts | An empty list or an empty string: summaries are not checked |
| Attribute prompts | `{}`: the fixtures declare no custom types |

**Ideal-model policy.** The stub never errs about meaning, so every duplicate or temporal error comes from the pipeline (master §8).

**Embedder.** A hashed bag of words with 1,024 dimensions. Facts that share words get a positive cosine. For example, "Alice works at Company3" and "Alice works at Company5" score 0.75, above Graphiti's 0.6 floor.

**Reranker.** Word overlap.

**Ledger.** Every model call is recorded in the evidence: the prompt, its client, digests, and what the stub decided.

## 5. Scenarios

Support levels follow K15. A violation in a supported configuration is FAIL; in a configuration outside the contract it is BOUNDARY (master §5.8).

### G1. Concurrent ingest with shared entities (I1 Form B, I2)

- **G1, same group.** 20 episodes into one group. Each names Alice, Acme and Payments, repeats "Alice works at Acme", and adds one fact of its own.
  - **Modes:**
    - `asyncio`: one instance, 20 coroutines.
    - `process`: 4 processes × 5 episodes; each process has its own instance and works through its share in order, like one MCP server.
    - `queue`: one FIFO per group, as the MCP server does.
  - **Support:** boundary (K15).
  - **Sequential control:** 3 entities, 21 facts, the repeated fact once with 20 episodes, 20 episodes.
- **G1c, cross group.** 10 episodes at once, one per group, so no group sees concurrency of its own.
  - **Support:** supported (#1676).
  - **Checks:** each group holds exactly its own episode, 3 entities and 2 facts.
- **G1, default pool.** The same-group `asyncio` run, on FalkorDB, with Graphiti's own client pool (K18).
- **Checks:**
  - one entity per canonical key per group;
  - one copy of the repeated fact;
  - every fact of every acknowledged episode present.

  Duplicates are witnessed by the episodes that mention each copy.

### G2. Concurrent contradicting facts (I7a)

- **Setup.** 10 episodes give Alice ten successive employers, `valid_at` 30 days apart, released together.
- **Support:** boundary (K15).
- **Sequential control:** a chain with one current version, "Alice works at Company9".

### G3. Bitemporal known-answer suite (I7b, I7c, I2, MR1)

Each case runs in its own group: setup episodes first, then the case. All six cases run through one entry point: `add_episode`, `add_episode_bulk` or `add_triplet`. G3 runs on every build and backend.

**Three readings of `expired_at`.** The harness reports all three and takes no side:

| Reading | `expired_at` is set when |
|---|---|
| **issue** | The edge is superseded, or its end of validity has already passed at ingest. This is what #2012 expects. |
| **code** | The edge is superseded, or it arrives with any end of validity. This is v0.31.2's rule (K5). |
| **standard** | The edge is superseded. This is master §5.7 I7b. |

**Cases.**

| Case | Source | Setup → subject | issue | code | standard |
|---|---|---|---|---|---|
| R1 | #2012 | none → future end (+365 d) | open | expired | open |
| R2 | #2012 | an unrelated fact on the same pair → the same as R1 | open | expired | open |
| R3 | #2012 | an unrelated fact → past end (−45 d) | expired | expired | open |
| R4 | #2012 | Carol leads X from +16 d → Bob leads X −15 d to +7 d | open, end kept | expired, end kept | open, end kept |
| R5 | #1865 | Bob leads Y −100 d to −60 d → Bob leads Y again from −10 d | both intervals kept | both | both |
| R6 | this harness | Dana leads Z from −30 d → Erin leads Z from −5 d | Dana closed at −5 d and expired; Erin current | same | same |

**MR1, context independence.** R1 and R2 must agree, under any reading.

**Credit.** R1–R4 reuse the definitions Adam13y published in #2012. The implementation is written fresh and drives the public entry points.

### G4. Read your writes on search (I3)

- **Procedure.** After each `add_episode` returns, the run searches for its fact with `Graphiti.search(query, group_ids=[g])`. It searches twice:
  - from the writing instance;
  - from a second instance with its own connections.
- **Measured.** Whether the first search finds the fact; otherwise, the lag.
- **Change from v0.1.** The second reader is a second instance, not a second process, because visibility depends on the connection, not the process.

### G5. A read changes later writes (I7a; new in v0.2)

- **Procedure.** Search once, then ingest the G2 chain one episode at a time. There is no concurrency.
- **Cases.**
  - `default`: `num_results=10`, which is the default.
  - `limit1`: `num_results=1`.
- **Checks.** Each case records the shared limit after the read (K17) and checks I7a.

### G6–G8: the M5 Phase C run plan

Declared on 2026-11-16, before the first Phase C batch (master §10, no fishing). It follows the v0.1 designs (commit `80a5623`, §5), with the maintainer's rulings of 2026-11-16 (master §12.1, Phase C):

- G6, G7 and G8 run on the released pin v0.31.2;
- G6 also runs on main `ebef986a` and on #2119's head `b2b727e0`, the one approved pull-request build;
- only the digest-pinned FalkorDB 6.0.4 and Neo4j 5.26.2 are used;
- models are stubbed and telemetry is off.

**Builds.**

| Build label | Environment | Frozen requirements | Scenarios |
|---|---|---|---|
| `v0.31.2` | `.state/venvs/graphiti-v0.31.2` | `requirements/v0.31.2.txt` | G6, G7, G8 |
| `main-ebef986a` | `.state/venvs/graphiti-main-ebef986a` | `requirements/main-ebef986a.txt` | G6 |
| `pr2119-b2b727e0` | `.state/venvs/graphiti-pr2119-b2b727e0` | `requirements/pr2119-b2b727e0.txt`: v0.31.2's frozen set, with graphiti-core taken from git at `b2b727e0` (K21, K22). `uv pip freeze` of the environment matches the file. | G6 |
| `main-4ef979c7` (M6) | `.state/venvs/graphiti-main-4ef979c7` in the `m6` worktree | `requirements/main-4ef979c7.txt`: `main-ebef986a.txt` with graphiti-core taken from git at `4ef979c7`. `uv pip freeze` of the environment matches the file. | G8 repro (§12.5) |

**Rules for every cell.**

- The sequential control runs first (k = 0). A cell whose control is not met is INVALID by rule (master §9).
- The seed is 20261116 plus the cell's row in the command table below. No scenario draws random numbers; the seed is recorded.
- The two races, G6c and G8, run in `asyncio` mode with the 92 ms spread gate (master §6.3) and an overlap control. G6a, G6b and G7 release no clients together, so they have no gate.
- Evidence goes to `evidence/graphiti/<build>.<backend>/<scenario>.<mode>/<run_id>/` with all four §9.1 files. Container actions are `nemesis` records with invocation and return times; stub calls are records with phase `stub`.

#### G6. Index readiness at startup (I4 while indexes build; #2119, #1643, K9, KD-F4)

**Load for G6a and G6b.**

- Group `wm_g6` gets 400 episodes of 5 facts each: 2,000 facts and 800 entities. They are loaded through the stubbed `add_episode`, one episode at a time.
- Each fact has a token of its own (`INV<episode>x<k>`) and the shared word "invoice".
- **Why 2,000 facts and not v0.1's 20k.** Scratch timing done before this declaration (kept out of `evidence/`):
  - With 5 facts per episode, stubbed `add_episode` loaded 2,000 facts in 198 s on FalkorDB.
  - With 25 facts per episode, one `add_episode` failed with FalkorDB's `Max pending queries exceeded` (the pinned image's `MAX_QUEUED_QUERIES 25`, K26) once the group held about 650 facts. `add_episode_bulk` with 10 episodes failed the same way.
  - At the measured rate, 20k facts would take well over 30 minutes per load, and G6 loads twelve times.

  The size is fixed for every G6a and G6b run [inference from the scratch timing].

**Search suite.**

- Ten `Graphiti.search(query, group_ids=["wm_g6"])` calls with the default `num_results` (10). Each searches for one fact's own token, so its right answer is exactly that fact.
- A raw probe on the harness's own connection runs the fulltext procedure Graphiti uses and counts the group's facts that match "invoice". The control answer is 2,000.
  - FalkorDB: `db.idx.fulltext.queryRelationships('RELATES_TO', …)`.
  - Neo4j: `db.index.fulltext.queryRelationships('edge_name_and_fact', …)`.

**Control (k = 0).**

1. After the load, wait until every index is ready: on FalkorDB, every row of `db.indexes()` is `OPERATIONAL`; on Neo4j, every non-lookup index in `SHOW INDEXES` is `ONLINE`.
2. Record that index set as the expected set.
3. Run the suite and the probe, and dump the group.

The control is met when all 400 ingests succeed, the dump holds 800 entities, 2,000 facts and 400 episodes, every query returns exactly its fact, and the probe counts 2,000.

**Measured in every trial.**

- **Answers.** The suite runs at once and again after every expected index is ready. Each query's answer is classified against the control as identical, silently different or an error (master §5.4; answers are compared as multisets).
- **Errors.** Search exceptions, plus log records at ERROR or above from Graphiti and its clients.
- **Never-retrieved task exceptions.** The event loop's exception handler, read after a garbage collection at the end of the trial.
- **Index builds.** Every `build_indices_and_constraints` call: its database, start, end and outcome. A wrapper records them; it awaits the original and changes nothing else.
- **Index monitor.** On its own connection, the monitor samples the index state and the probe every 2 ms. It starts just before the trial's action and stops once every expected index is ready. Consecutive identical samples are recorded once, with their count.
- **UNDER CONSTRUCTION after creation returns** (KD-F4, FalkorDB): the time from the end of the first completed build on the group's graph to the first sample in which every expected index is ready. The trial also records whether any sample saw `UNDER CONSTRUCTION`, and the probe's rows while one did. This answers master §13's question.
- **State at the first query.** The index state when the first at-once query was invoked, so a clean cell says whether that query met an index that was not ready.
- **I2.** The group's data (a digest of its facts, entities and episodes, read on the harness's connection) is the same after the trial as in the control.

**Verdicts.** The invariants are I4.at_once, I4.ready and I2. The support level is none: no Graphiti document promises answers before the indexes are ready. The basis is issue #1643. A violation is OBSERVED, and a clean cell is PASS.

- **G6a, fresh.** T = 20. Each trial:
  1. Close the previous instance after its background work.
  2. Drop every index (FalkorDB: every index on the `wm_g6` graph; Neo4j: every non-lookup index), wait until none is listed, and check the data digest.
  3. Start the monitor.
  4. Construct a new Graphiti with a new driver and run the suite at once; the first search is called with no await after construction.
  5. Wait until every expected index is ready, then run the suite again.
- **G6b, populated.** T = 10, because each Neo4j restart takes tens of seconds. After the control, FalkorDB gets a `SAVE`, recorded as a setup record, because the pinned image runs `appendonly no` (K26). Each trial:
  1. Check the data digest and close the instance.
  2. Restart the test container (`docker restart wm-falkordb` or `wm-neo4j`, recorded as nemesis `restart`).
  3. Poll until the server answers: FalkorDB `PING`; Neo4j `RETURN 1`.
  4. Start the monitor, construct, and run the suite at once.
  5. Wait until every expected index is ready, then run the suite again.
- **G6c, many groups (FalkorDB only).** T = 20.
  - Eight groups, `wm_g6c_0` to `wm_g6c_7`, get one episode of 5 facts each.
  - Each trial deletes the eight graphs (`GRAPH.DELETE`, so no index exists). One Graphiti instance then releases eight `add_episode` calls together through an asyncio barrier, one per group. Each call's clone starts its own build on a new graph (K9).
  - Then quiesce, wait until every group's indexes are ready, dump, and search each group for one fact while the monitor samples all eight graphs.
  - Sequential control: the same eight ingests one at a time, from the same reset.
  - Checks: I2 (every fact of every acknowledged episode is present), I1B (one entity per key per group), I4 (each group's answer equals the control's), never-retrieved exceptions, errors, builds, and UNDER CONSTRUCTION after creation for each graph.
  - The support level is supported: concurrent calls for different groups are the case the #1676 fix covers (K15). The basis is documented, so a violation is FAIL.

**Cells (15 runs).**

- G6a and G6b run on FalkorDB and on Neo4j, and G6c on FalkorDB. Each runs on v0.31.2, main and #2119's head.
- The original design's checks apply on Neo4j to G6a (its driver also starts a background build, K23) and to G6b (restart, then wait for `ONLINE`).
- G6c on Neo4j is NOT_APPLICABLE: Neo4j's `clone` returns the same driver (K23), and every group shares one database (K10).
- #2119 changes only the FalkorDB driver, so its Neo4j cells are expected to match main [inference]. They run anyway, as ruled.

#### G7. Persistence across restarts (I2 across a restart; #2117, K11, K12)

**Compose file.** `targets/01-zep-graphiti/docker/compose-g7.yml` uses the project name `witnessmark-g7`. It runs the pinned FalkorDB 6.0.4 digest, with ports on 127.0.0.1 and named volumes. It reproduces two upstream volume layouts at v0.31.2 [code]:

| Variant | Service, container, port | Volume | Upstream layout reproduced |
|---|---|---|---|
| root | `falkordb-root`, `wm-g7-root`, 16391 | `g7_root_data` at `/data` | [docker-compose.yml L50–64](https://github.com/getzep/graphiti/blob/v0.31.2/docker-compose.yml#L50-L64): the volume at `/data` (L55–56), `FALKORDB_ARGS=--port 6379 --cluster-enabled no` (L57–58), and the `redis-cli ping` health check (L59–64) |
| mcp | `falkordb-mcp`, `wm-g7-mcp`, 16392 | `g7_mcp_data` at `/var/lib/falkordb/data` | [mcp_server/docker/docker-compose-falkordb.yml L2–17](https://github.com/getzep/graphiti/blob/v0.31.2/mcp_server/docker/docker-compose-falkordb.yml#L2-L17): the volume (L10–11), an empty `FALKORDB_PASSWORD` and `BROWSER=1` (L7–9), and the health check (L12–17). The web UI port 3000 is not published. |

- Upstream pins `falkordb/falkordb:latest`; the harness file uses the pinned digest instead.
- The combined image (`mcp_server/docker/docker-compose.yml`) is NOT_EXERCISED, because it needs an unpinned upstream image (`zepai/knowledge-graph-mcp:latest`, built upstream).

**Each trial.**

1. Remove the variant's container and volume, then start it with `docker compose up -d <service>`.
2. Wait for `PING`, and record `appendonly`, `appendfsync`, `save`, `dir` and the module's arguments.
3. Open Graphiti v0.31.2 (stubbed) and ingest K = 10 episodes into group `wm_g7`, one at a time, one fact each.
4. Dump, then close Graphiti.
5. Apply the cell's action.
6. Wait for `PING`, record the settings again, reopen, and dump.

**Actions**, all recorded as nemesis records:

- `compose_restart`: `docker compose restart <service>` (`restart`).
- `down_up`: `docker compose down` (`stop`; it removes the container and keeps the volume), then `docker compose up -d <service>` (`start`).
- `kill_start`: `docker kill <container>` (`kill`), then `docker start <container>` (`start`).

**Control (k = 0).** The same steps without the action. The control is met when the dump holds 10 episodes, 2 entities and 10 facts.

**Check.** I2: every episode, entity and fact in the dump before the action is in the dump after it. The magnitude is the number of items lost. The support level is none and the basis is issue #2117; that a declared named volume implies persistence is [inference]. Loss is reported as OBSERVED, with the persistence settings beside it.

**Cells (6 runs).** Two variants × three actions, on v0.31.2 only; the original design asks for no build comparison. T = 10.

#### G8. Deletion permanence (I5, with overreach reported under I2)

**Fixture (group `wm_g8`).**

- `G8S`: "Alice works at Acme" (entities Alice and Acme).
- `G8E`: repeats that fact and adds "Alice approved the Payments budget" (entities Alice, Acme and Payments). Before the race it is the only episode that names Payments.
- `G8N`: "Alice audited Payments" (entities Alice and Payments).

**Setup in every trial.** Reset the group, then add `G8S` and then `G8E`.

**Race** (`asyncio`, M2's shape). Two clients are released together: c00 runs `remove_episode(G8E)` and c01 runs `add_episode(G8N)`.

**Sequential control.** The same two operations one at a time: the remove, then the add. The expected state is:

- episodes `G8S` and `G8N`;
- entities Alice, Acme and Payments, one each;
- facts "Alice works at Acme" (carried by one episode) and "Alice audited Payments";
- no "Alice approved the Payments budget".

Running the two operations in the other order gives the same state.

**Checks (master §5.5).**

- **I5.** After an acknowledged remove, `G8E` and "Alice approved the Payments budget" are gone, and the concurrent ingest brought neither back.
- **I2 with `cause = delete`** (overreach): "Alice works at Acme" (still carried by `G8S`) and `G8S` itself remain. After an acknowledged add, `G8N`, "Alice audited Payments" and Payments are present.
- **I1B.** One entity per key.

**Backends.** FalkorDB, with the driver bound to the group's graph (K25), and Neo4j, both on v0.31.2. T = 20, with the 92 ms spread gate and an overlap control.

**Support.** None: no Graphiti document covers `remove_episode` running at the same time as `add_episode`, and K15's sequential requirement names `add_episode` only. The basis is inferred (master §5.5). A violation is reported as OBSERVED.

#### Amendments before the batch (2026-11-16)

Scratch smoke runs (kept out of `evidence/`) changed three details before the first batch. Nothing else in the plan changed.

1. **Which facts the queries name.** The stub embedder hashes each word into one of 1,024 signed buckets. Both engines score cosine similarity as (1 + cos) / 2, and Graphiti keeps scores above 0.6, so any fact with a word in the query word's bucket and sign is also returned. To keep exactly one right answer per query, query n starts at episode n × 40 and takes the first fact, in order, whose own token shares no bucket and sign with another word of the load (`fixtures.g6_queries`). G6c does the same within each group (`fixtures.g6c_query`). The rule depends only on the fixture and the stub, never on a result.
2. **Search timeout.** Every search carries the per-operation timeout τ_op = 60 s (master §6.6).
   - A search with no answer is recorded with an unknown outcome and error `unavailable.timeout`.
   - Its trial stops there and is invalid, with that reason. The instance is then closed, which ends its server transactions, and the next trial starts.
   - In one Neo4j G6a smoke trial, the at-once searches and two transactions opened as Graphiti was constructed were still open after ten minutes. Killing the client ended them. A second smoke run, already under this timeout, stopped one of its three trials the same way. A scratch repro without the harness's index monitor (six rounds) and with a 2 ms poller in its place (five rounds) did not repeat it, so its cause is unknown [unmeasured: G6a on Neo4j].
3. **G6b's own connection.** The harness's probe connection is closed before each restart and opened again after it. A pooled connection that the restart killed logs a client error under the same logger names Graphiti's driver uses.

#### Command table (one main batch, `m5g-<UTC time>`)

Every command runs from the repository root with the build's environment's Python, as `targets/01-zep-graphiti/wm_graphiti.py <command> … --seed <20261116 + row> --batch <id>`. Every G6 command for main or #2119 also passes `--build` and `--commit`.

| Rows | Command |
|---|---|
| 1–3 | `startup --scenario g6a.fresh --backend falkordb --trials 20` on v0.31.2, main, #2119 |
| 4–6 | `startup --scenario g6b.populated --backend falkordb --trials 10` on the three builds |
| 7–9 | `race --scenario g6c.many_groups --backend falkordb --trials 20` on the three builds |
| 10–12 | `startup --scenario g6a.fresh --backend neo4j --trials 20` on the three builds |
| 13–15 | `startup --scenario g6b.populated --backend neo4j --trials 10` on the three builds |
| 16–21 | `persistence --variant root\|mcp --action compose_restart\|down_up\|kill_start --trials 10` on v0.31.2 (root first, actions in that order) |
| 22–23 | `race --scenario g8.remove_vs_add --backend falkordb\|neo4j --trials 20` on v0.31.2 |

The batch brings the baselines up only through `baselines/docker-compose.yml`, and G7's containers only through its compose file.

#### Amendments after the main batch (2026-11-16), declared before they ran

Under the maintainer's rulings of 2026-11-16, recorded while the main batch ran:

1. **Re-run of row 11 (harness fix).** In the main batch `m5g-20261116T051149Z`, row 11 (G6a on Neo4j, main) hung. A search stalled and was timed out, but closing the instance in-process did not end its server transactions, and the next trial's data read waited behind them. The run was killed, so it left no `run.json`; the driver's note is in `evidence/graphiti/errors/`. Commit `425e22e` bounds every probe read. After a stall the harness now ends the leftover transactions (Neo4j `TERMINATE TRANSACTIONS`) and restarts the test container if any remain; each step is a setup or nemesis record.
   - Terminating first, with the restart as a fallback, is the conservative choice: it disturbs the next trial least and always leaves a clean server.
   - Row 11 alone is re-run, with its seed (20261127), in its own batch `m5h-<UTC time>`. Rows 10 and 12 completed and are not re-run.
2. **G7 explanatory control (ruling 4).** G7 `kill_start` on both layouts, with FalkorDB's append-only file on: `appendonly yes`, `appendfsync everysec`. `compose-g7-appendonly.yml` is layered over `compose-g7.yml` and sets `REDIS_ARGS`, which the pinned image's `run.sh` passes to `redis-server` (K26). Everything else is the main cell's procedure: v0.31.2, K = 10, T = 10.
   - Scenario ids `g7.<variant>.kill_start.appendonly.persistence`, seeds 20261140 (root) and 20261141 (mcp), in their own batch `m5i-<UTC time>`, reported next to the main cells.
   - Expectation [inference]: with `appendfsync everysec`, a kill can lose up to about a second of acknowledged writes, so some loss is possible. The harness does not control the gap between the last write and the kill.

| Batch | Rows | Command |
|---|---|---|
| `m5h-…` | 11 | `startup --scenario g6a.fresh --backend neo4j --trials 20 --build main-ebef986a --commit ebef986a… --seed 20261127` |
| `m5i-…` | 24–25 | `persistence --variant root\|mcp --action kill_start --appendonly --trials 10 --seed 20261140\|20261141` on v0.31.2 |

## 6. Checks

The canonical dump (`target.py: dump`) contains, per group:

- **Entities:** name, canonical key, and the episodes that mention each node.
- **Facts:** text, endpoint names, relation, `valid_at`, `invalid_at`, whether expired, and the number of episodes.
- **Episodes:** the episode names.
- **FalkorDB only:** the facts for this group that sit in the default graph instead (K16).

uuids and creation times are left out, so dumps compare across runs and backends.

## 7. Deliverables

| ID | Deliverable |
|---|---|
| D1 | Race matrix: G1 (modes × backends), G1c, the default-pool run, G2 |
| D2 | Temporal matrix: G3 cases × entry points × builds × backends, three readings plus MR1; G5 |
| D3 | Visibility table (G4) |
| D4 | One single-file repro for each finding that goes upstream |
| Drafts | In `drafts/`, never committed |

## 8. Contribution plan (non-competing)

The tracker was checked on 2026-11-13 (read-only).

1. **Before any draft:** search the tracker again, and re-run on the newest release.
2. **#2012.** Comment with D2 for #2012's cases, framed by the three readings and MR1. No pull request: the semantics are open and #1867 exists.
3. **#1865 and #1867.** Report, in those threads:
   - R5 on v0.31.2 and main: the second occurrence is lost.
   - R5 on #1867: fixed, and MR1 holds.
   - #1867 still differs from #2012's reading on R1, R2 and R4.
   - #1867 cannot run on FalkorDB 6.0.4 until it is rebased: index creation fails (run `20261113T175500Z-dce0eb46`).
4. **K16, `add_triplet` group scope.** [getzep/graphiti#1795](https://github.com/getzep/graphiti/issues/1795) (open) covers this code path in an older form, where `add_triplet` reassigned the shared driver. Comment there with the v0.31.2 and main measurement and `repros/repro_triplet_group_graph.py`: the reassignment is gone, and the triplet now goes to the default graph.
5. **K17, shared search limit.** Already fixed by the open one-line [getzep/graphiti#1594](https://github.com/getzep/graphiti/pull/1594) (`.model_copy(deep=True)` before `.limit` is set). Support it with G5's numbers rather than filing anything.
   - **Measured** (with the maintainer's approval to run the PR's code): on Neo4j, #1594's head keeps the shared limit at 10 after `search(num_results=1)`. It leaves 1 current version where v0.31.2 leaves 8 ([evidence/M2_PR1594.md](../../evidence/M2_PR1594.md)).
   - **FalkorDB:** its 0.29.2 base fails index creation on FalkorDB 6.0.4, as #1867's does.
6. **K18, the FalkorDB connection pool.** No issue was found. This is a candidate new issue, with `repros/repro_falkordb_pool.py` and the default-pool G1 run.
7. **K19, httpx.** [getzep/graphiti#1893](https://github.com/getzep/graphiti/issues/1893) and its fix [getzep/graphiti#1894](https://github.com/getzep/graphiti/pull/1894) already cover it. Nothing to add.
8. **G1 and G2.** These are boundary results (K15). Offer them as data on how much the documented sequential requirement matters, for example for several MCP replicas on one database, not as bugs.
9. **Rules.** The CLA comes before any pull request. Outreach follows master §11.

## 9. Exit and drop rule

- **Controls fail.** If a race run's sequential control fails, the run is INVALID. Fix the fixture before anything else.
- **G1 and G2 clean.** If they were clean in every mode with the overlap control met, they would be published as clean, with credit.

## 10. Open questions

| Question | Settled in |
|---|---|
| Is running several MCP server processes against one database supported? | Ask, if G1 `process` results go upstream |
| When do Neo4j fulltext and vector indexes reflect a committed write? | Answered in M2 by Graphiti G4 on Neo4j 5.26.2. Both the writing instance and a second instance saw 10 of 10 writes on the first search [measured: `20261113T175059Z-738c7f37`]. |
| Do main and #1867 keep the same prompt set? | Answered in M2: yes. The stubs ran unchanged on both. |

## 11. Results (M2)

**Provenance.** Batch `m2-20261113T174128Z`, harness commit `526e98f` (clean tree), 20 trials per race. Every number below is [measured] and comes from [evidence/M2_GRAPHITI.md](../../evidence/M2_GRAPHITI.md), which is regenerated from the runs named there. Every race's sequential control was met on both backends. That is M2's exit criterion: the fixture graph comes out exactly as specified when nothing races.

| Scenario | FalkorDB 6.0.4 | Neo4j 5.26.2 | Verdict |
|---|---|---|---|
| G1, one group, `asyncio` | Every episode created its own copy of each entity and of the repeated fact, in 20 of 20 trials (20 copies per key). Nothing lost. | Same | BOUNDARY (K15) |
| G1, one group, `process` (4 workers × 5) | Duplicates in 20 of 20 trials: median 4 copies per key, about one per worker; at most 16 | Same; at most 8 | BOUNDARY |
| G1, one group, `queue` | 0 of 20 | 0 of 20 | PASS: a per-group queue removes the race within one process |
| G1c, ten groups, one episode each | 0 of 20 | 0 of 20 | PASS: the #1676 fix holds |
| G1 with Graphiti's own FalkorDB pool | 117 of 400 calls (3 to 6 per trial) failed with `MaxConnectionsError`, so every trial was invalid | n/a | OBSERVED (K18) |
| G2, ten employers at once | All 10 versions stayed current, in 20 of 20 trials | Same | BOUNDARY |
| G3, v0.31.2 and main, all three entry points | R1 open (contrary to the code's own rule); R2 and R4 expired (contrary to #2012); R3 expired; R5 lost its second occurrence; R6 correct; MR1 broken | Same | OBSERVED |
| G3, `add_triplet` | Every case's facts were written to the default graph, not the group's graph (6 of 6) | Placed correctly | OBSERVED (K16) |
| G3, #1867 | Crashes at index creation on 6.0.4 | R5 fixed, MR1 holds, consistent with the code reading; still contrary to #2012 on R1, R2 and R4 | OBSERVED |
| G4 | 10 of 10 writes seen on the first search, from the same instance and from a second one | Same | PASS |
| G5 | `default`: 1 current version. `limit1`: 6 current versions after one `search(num_results=1)` | 1 and 8 | OBSERVED (K17); no concurrency involved |
| G5 on [#1594](https://github.com/getzep/graphiti/pull/1594)'s head (batch `m2-pr1594-20261113T191556Z`, harness `546c210`) | Fails index creation on 6.0.4 (its 0.29.2 base) | Both cases: 1 current version; the shared limit stays 10 | PASS: the PR's one-line fix removes K17 |

**Repros** (`repros/`, standard library plus graphiti-core, no API key), run on 2026-11-13 against the baselines:

| Repro | Expected | Observed |
|---|---|---|
| `add_triplet` on FalkorDB | 1 edge in the group's graph, 0 in the default graph | 0 in the group's graph, 1 in the default graph |
| One `search(num_results=1)` | the shared limit stays 10 | it moves from 10 to 1, on both backends |
| 60 concurrent searches, FalkorDB | 60 ok | 18 ok, 42 `MaxConnectionsError` |
| 60 concurrent searches, Neo4j | 60 ok | 60 ok |

## 12. Results (M5)

### 12.1 Provenance

| Batch | Harness | Commands | What it holds | Report |
|---|---|---|---|---|
| `m5g-20261116T051149Z` (main) | `8b9785a`, clean | 25, of which 24 exit 0 | The 2 baseline commands and the 23 declared rows (§5, command table). Row 11 hung and was ended (exit 4294967295); it left no `run.json` (§12.6). | [evidence/M5_GRAPHITI.md](../../evidence/M5_GRAPHITI.md) |
| `m5h-20261116T071955Z` (re-run) | `425e22e`, clean | 3, of which 2 exit 0 | The 2 baseline commands, then row 11 again after the stall-recovery fix. It hung again (exit 4294967295) and was ended under the maintainer's ruling. No `run.json`, so no report. | none (the reporter builds from manifests only) |
| `m5i-20261116T092138Z` (explanatory control) | `0395799`, clean | 4, all exit 0 | The 2 baseline commands and G7 `kill_start` on both layouts with `appendonly yes` (maintainer ruling 4) | [evidence/M5_GRAPHITI_B1.md](../../evidence/M5_GRAPHITI_B1.md) |

Command counts follow master §12.1's counting rule: every command the driver logs, baselines included (corrected at Phase E from 24 and 23, 1 and 2).

- **False start.** The first launch, `m5g-20261116T044019Z`, ran no runs. The batch driver, which is kept uncommitted under `.state` by design, passed a relative interpreter path that Windows `CreateProcess` could not resolve. It stopped before row 1 and wrote nothing to `evidence/`. The fixed driver launched the main batch.
- **Ended runs.** Two runs were ended while hung. Their partial directories are kept as written: `20261116T055056Z-3d69b1c9` (states 0–7; corrected at Phase E from "0–5" by its committed `state/` files) and `20261116T071959Z-74370fb1` (states 0–3). The driver wrote an ERROR.md for each under `evidence/graphiti/errors/<batch>/`.
- **Maintainer rulings, 2026-11-16.** The G6 size of 2,000 facts is accepted as declared. The #2119 review order is accepted: the diff was read before installing, and the review was written into this blueprint after the environment was built (K21, `886f4c6`).
- **Changes after the main batch.** Three harness commits, each declared in §5 before the batch that used it:
  - `425e22e` ends a stalled search's server transactions before the next G6 trial;
  - `e369a16` adds the G7 appendonly control;
  - `0395799` bounds searches and probe reads without waiting for cancellation.

  No completed cell was re-run, and no evidence was edited.
- Every number below is [measured] from the run named beside it, in batches `m5g-20261116T051149Z`, `m5h-20261116T071955Z` and `m5i-20261116T092138Z`, through the reports above or the run's own `run.json` and `history.jsonl`. The P5 repro's counts in §12.5 are the exception: they carry their own tag and come from the repro's console output, which is kept outside `evidence/`.

### 12.2 Controls first

- **Sequential controls.** Met in all 24 completed runs: 22 in the main batch `m5g-20261116T051149Z` and 2 in the control batch `m5i-20261116T092138Z`.
- **G6.** The control load reproduced 800 entities, 2,000 facts and 400 episodes. Every query returned exactly its fact, and the probe counted 2,000 [measured: batch `m5g-20261116T051149Z`, the sequential control of each of the 11 completed G6a and G6b runs in §12.3].
- **Races.** The overlap control was met in all five races: 20 of 20 valid trials had two or more operations in flight. Over the 100 valid race trials the release spread had p99 3.49 ms and max 5.87 ms, under the 92 ms gate [measured: batch `m5g-20261116T051149Z`, the three G6c runs in §12.3 and the two G8 runs in §12.5; `evidence/M5_GRAPHITI.md`, "Release spread by mode"].
- **Validity.** Every completed run had all its trials valid.

### 12.3 G6. Index readiness at startup

| Build | Backend | Cell | Valid | First query met an index that was not ready | At once: identical / different / error | After ready | Never-retrieved exceptions | Verdict | Run |
|---|---|---|---|---|---|---|---|---|---|
| v0.31.2 | FalkorDB | G6a | 20 of 20 | 20 of 20 | 200 / 0 / 0 | 200 / 0 / 0 | 0 | PASS | `20261116T051153Z-2e987ec0` |
| main | FalkorDB | G6a | 20 of 20 | 20 of 20 | 200 / 0 / 0 | 200 / 0 / 0 | 0 | PASS | `20261116T051801Z-c9fd6666` |
| #2119 | FalkorDB | G6a | 20 of 20 | 20 of 20 | 200 / 0 / 0 | 200 / 0 / 0 | 0 | PASS | `20261116T052409Z-5885a291` |
| v0.31.2 | FalkorDB | G6b | 10 of 10 | 0 of 10 | 100 / 0 / 0 | 100 / 0 / 0 | 0 | PASS | `20261116T053018Z-2290cc18` |
| main | FalkorDB | G6b | 10 of 10 | 0 of 10 | 100 / 0 / 0 | 100 / 0 / 0 | 0 | PASS | `20261116T053508Z-67de8ce9` |
| #2119 | FalkorDB | G6b | 10 of 10 | 0 of 10 | 100 / 0 / 0 | 100 / 0 / 0 | 0 | PASS | `20261116T053958Z-f4b4332f` |
| v0.31.2 | FalkorDB | G6c | 20 of 20 | – | I2, I1B, I4: 0 of 20 | – | 0 | PASS | `20261116T054448Z-74713339` |
| main | FalkorDB | G6c | 20 of 20 | – | 0 of 20 | – | 0 | PASS | `20261116T054508Z-0928df36` |
| #2119 | FalkorDB | G6c | 20 of 20 | – | 0 of 20 | – | 0 | PASS | `20261116T054530Z-07a4e09a` |
| v0.31.2 | Neo4j | G6a | 20 of 20 | 20 of 20 | 161 / 0 / 39 | 200 / 0 / 0 | 0 | OBSERVED: I4.at_once in 11 of 20 | `20261116T054555Z-85bc1662` |
| main | Neo4j | G6a | – | – | – | – | – | INVALID (§12.6) | `20261116T055056Z-3d69b1c9`, `20261116T071959Z-74370fb1` |
| #2119 | Neo4j | G6a | 20 of 20 | 20 of 20 | 174 / 0 / 26 | 200 / 0 / 0 | 0 | OBSERVED: I4.at_once in 8 of 20 | `20261116T064351Z-20ab7a28` |
| v0.31.2 | Neo4j | G6b | 10 of 10 | 0 of 10 | 100 / 0 / 0 | 100 / 0 / 0 | 0 | PASS | `20261116T064831Z-bea83c1a` |
| main | Neo4j | G6b | 10 of 10 | 0 of 10 | 100 / 0 / 0 | 100 / 0 / 0 | 0 | PASS | `20261116T065525Z-d552844d` |
| #2119 | Neo4j | G6b | 10 of 10 | 0 of 10 | 100 / 0 / 0 | 100 / 0 / 0 | 0 | PASS | `20261116T070159Z-af2cbe2f` |
| – | Neo4j | G6c | – | – | – | – | – | NOT_APPLICABLE: Neo4j's `clone` returns the same driver (K23) | – |

**Findings.**

- **G6-F1, master §13's question** [measured: `20261116T051153Z-2e987ec0`, `20261116T051801Z-c9fd6666`, `20261116T052409Z-5885a291`, `20261116T054555Z-85bc1662`, `20261116T064351Z-20ab7a28`; history monitor records, RELATES_TO fulltext index only]. On FalkorDB 6.0.4, a fulltext query against an index in `UNDER CONSTRUCTION` returned fewer rows than the control, or all of them, and never an error.
  - In G6a, counted in monitor samples:
    - v0.31.2: 3 samples with fewer rows, 5 with all 2,000 (`20261116T051153Z-2e987ec0`);
    - main: 1 and 4 (`20261116T051801Z-c9fd6666`);
    - #2119: 58 and 2 (`20261116T052409Z-5885a291`).
  - With the index not yet created, the same query returned 0 rows and no error: 154, 159 and 163 samples in those three runs.
  - On Neo4j 5.26.2 the same situations differ. A missing fulltext index is a typed error, `ProcedureCallFailed` ("There is no such fulltext schema index"). A `POPULATING` index returned all 2,000 rows: 11 samples in `20261116T054555Z-85bc1662`, 12 in `20261116T064351Z-20ab7a28`.
  - The status and the probe are read one after the other, so a sample may straddle a change.
  - **Reproduced without Graphiti (M6 Phase C, 2026-11-19).** A single-file, standard-library repro, `baselines/repros/repro_falkordb_fulltext_under_construction.py`, creates N `RELATES_TO` relationships, creates the fulltext index with the documented DDL, and samples `db.indexes()` and `db.idx.fulltext.queryRelationships` until the index is `OPERATIONAL`. On FalkorDB 6.0.4 it returned fewer than N rows, never an error, while the index was `UNDER CONSTRUCTION`:
    - N = 2,000: in 20 of 20 trials, 107 samples, counts 32 to 1,982 [measured: repro_falkordb_fulltext_under_construction.py at `48b113f`, command 1];
    - N = 20,000: in 20 of 20 trials, 1,257 samples, counts 0 to 19,980; every trial had a sample with 0 rows [measured: repro_falkordb_fulltext_under_construction.py at `48b113f`, command 2].

    The sequential control returned exactly N once the index was `OPERATIONAL`, in all 40 trials. The declaration, the full results and the plain Cypher steps are in master §12.2, Phase C. The C engine (v4.x) was not run.
- **G6-F2, awaiting the build is not enough on FalkorDB (KD-F4, #2119).** On #2119's head, every index was still not ready after the awaited build on the group's graph returned, in 20 of 20 trials, each time because one was `UNDER CONSTRUCTION`. The interval was at least 11.69 ms at the median and 17.18 ms at most, and at most 36.66 ms (`20261116T052409Z-5885a291`). Graphiti's answers were still identical, 200 of 200, because the cosine half of its hybrid search needs no index and finds each query's fact on its own [inference from the stub embedder: each query word scores above Graphiti's 0.6 floor against its fact]. A search that depends on fulltext matching alone would see the fewer rows of G6-F1 [inference].
- **G6-F3, every FalkorDB search starts an index build (K24).** G6a made 420 `build_indices_and_constraints` calls in 20 trials on every build: 21 per trial, one for the new root driver and one for each of the 20 searches (`20261116T051153Z-2e987ec0`, `20261116T051801Z-c9fd6666`, `20261116T052409Z-5885a291`). On #2119 each search awaits its own build first (K21).
- **G6-F4, Graphiti on Neo4j right after construction.** The Neo4j driver also builds indexes in the background (K23). In G6a the at-once searches raised `ProcedureCallFailed` because the fulltext index did not exist yet:
  - v0.31.2: 39 of 200 queries, in 11 of 20 trials (`20261116T054555Z-85bc1662`);
  - #2119: 26 of 200, in 8 of 20 (`20261116T064351Z-20ab7a28`).

  Once every index was `ONLINE`, all 200 answers were identical on both. This is OBSERVED: no document promises answers before the indexes are ready, and the basis is #1643. #2119 changes only the FalkorDB driver (K21).
- **Clean results, with credit to the project.**
  - No G6 run recorded a never-retrieved task exception, so #1643's "Task exception was never retrieved" did not appear under these conditions.
  - G6b was clean on both backends and all three builds. After a restart, every index was already `OPERATIONAL` or `ONLINE` when the first at-once query ran (no trial in any cell met an index that was not ready), and every answer was identical.
  - G6c was clean on all three builds. Eight concurrent ingests into eight new graphs lost nothing, duplicated nothing and answered as the control did, which is credit to the #1676 fix. Its 320 race-phase builds per run all completed. In the observe phase, 21 of 320 builds on v0.31.2 and on main, and 1 of 32 control builds on each, were still running when the run drained its build tracker (`target.running`, "the build ended running"), against none on #2119 [measured: `20261116T054448Z-74713339`, `20261116T054508Z-0928df36`, `20261116T054530Z-07a4e09a`; added at Phase E]. They are recorded, not explained; no G6c check depends on them.

### 12.4 G7. Persistence across container actions

| Layout | Action | Persistence settings | Valid | Trials with loss | Lost per trial | Verdict | Run |
|---|---|---|---|---|---|---|---|
| root (`/data`) | compose restart | appendonly no, appendfsync everysec, save 3600 1 300 100 60 10000 | 10 of 10 | 0 of 10 | 0 | PASS | `20261116T070849Z-c09d11b2` |
| root | down, then up | same | 10 of 10 | 0 of 10 | 0 | PASS | `20261116T070935Z-cdf2ec96` |
| root | kill, then start | same | 10 of 10 | 10 of 10 | 10 episodes, 2 entities, 10 facts | OBSERVED | `20261116T071025Z-e638bddf` |
| mcp (`/var/lib/falkordb/data`) | compose restart | same | 10 of 10 | 0 of 10 | 0 | PASS | `20261116T071106Z-079f03e1` |
| mcp | down, then up | same | 10 of 10 | 0 of 10 | 0 | PASS | `20261116T071148Z-932b738f` |
| mcp | kill, then start | same | 10 of 10 | 10 of 10 | 10 episodes, 2 entities, 10 facts | OBSERVED | `20261116T071238Z-cfee79ff` |
| root, control | kill, then start | **appendonly yes**, appendfsync everysec, same save | 10 of 10 | 0 of 10 | 0 | PASS | `20261116T092142Z-a5ceedc5` |
| mcp, control | kill, then start | **appendonly yes**, appendfsync everysec, same save | 10 of 10 | 0 of 10 | 0 | PASS | `20261116T092229Z-98725745` |

- **G7-F1.** With the settings the pinned image runs by default, `appendonly no` and `save 3600 1 300 100 60 10000`, killing the container lost every episode, entity and fact ingested since the last snapshot, in 10 of 10 trials on both layouts. The graph itself was gone afterwards. The explanatory control turned the append-only file on and kept everything in 10 of 10 trials on both layouts.
  - Per the maintainer's ruling, the loss is OBSERVED and tied to that persistence configuration. It is not reported as a Graphiti defect or a volume-path defect.
- **G7-F2, credit.** Both layouts kept everything across `docker compose restart` and across `down` then `up`, which recreates the container and keeps the volume. That held in 10 of 10 trials each.
  - The root layout mounts its volume at `/data`. In the pinned image that path is a symbolic link to the data directory (K26), so the volume does hold the data [inference from K26 and these runs].
  - Whether `falkordb:latest`, which upstream pins, has the same link was not checked.
- **G7-F3, OBSERVED.** The root layout's `FALKORDB_ARGS=--port 6379 --cluster-enabled no` replaces the image's default module arguments: the graph module reported no arguments, where the mcp layout reported `MAX_QUEUED_QUERIES 25 TIMEOUT 1000 RESULTSET_SIZE 10000` (every G7 root run against every mcp run).
- The combined image (`mcp_server/docker/docker-compose.yml`) is NOT_EXERCISED: it needs an unpinned upstream image.

### 12.5 G8. Deletion permanence

| Backend | Sequential control | Overlap | I5 | I2 (`cause = delete`) | I1B | Run |
|---|---|---|---|---|---|---|
| FalkorDB, driver bound to the group's graph | met | 20 of 20 | 0 of 20 | 0 of 20 | 0 of 20 | `20261116T071319Z-334d816c` |
| Neo4j | met | 20 of 20 | 0 of 20 | **20 of 20** OBSERVED | 0 of 20 | `20261116T071325Z-4bc1eaa9` |

- **G8-F1, possible Graphiti defect, for the maintainer's review.** On Neo4j, in 20 of 20 trials, `remove_episode(G8E)` and `add_episode(G8N)` ran concurrently and both were acknowledged.
  - Afterwards G8N's own fact, "Alice audited Payments", and the entity Payments were gone. Two items that a live, acknowledged episode references were lost to the delete (I2, `cause = delete`).
  - The sequential control, the remove and then the add, kept both (`20261116T071325Z-4bc1eaa9`).
  - A plausible reading [inference from K25 and graphiti.py L2174–2213]: `remove_episode` counts Payments' mentions before G8N's mention is written, so Payments looks orphaned, and it deletes the node with the edge G8N had just attached.
  - On FalkorDB the same race kept everything in 20 of 20 trials.
  - The support level is none, so the result is OBSERVED, not FAIL. No ad hoc runs followed it. The single-file repro (P5) waits for Phase E.
  - **P5 repro, declared run (M5 Phase E, 2026-11-16, declared before it ran).** `repros/repro_g8_remove_vs_add.py` uses the standard library and graphiti-core only, with telemetry off. The model, embedder and reranker are inline fakes that subclass graphiti-core's client bases and answer from the G8 fixture; nothing calls a model provider and nothing imports witnessmark. It seeds G8S and G8E, runs the sequential control once (the remove, then the add), then the concurrent case once per iteration through an `asyncio.Barrier`. For each, it prints the expected and observed episodes, entities and facts. On FalkorDB the driver is bound to the group's graph (K25). The declared run is four commands, each run once, from the repository root, with the baselines brought up only through `baselines/docker-compose.yml` and outputs saved under `.state/scratch/m5e-repro/` (not committed):

    | # | Build (existing venv) | Command |
    |---|---|---|
    | 1 | v0.31.2 (`.state/venvs/graphiti-v0.31.2`) | `python targets/01-zep-graphiti/repros/repro_g8_remove_vs_add.py neo4j 20` |
    | 2 | v0.31.2 | `… repro_g8_remove_vs_add.py falkordb 20` |
    | 3 | main `ebef986a` (`.state/venvs/graphiti-main-ebef986a`) | `… repro_g8_remove_vs_add.py neo4j 20` |
    | 4 | main `ebef986a` | `… repro_g8_remove_vs_add.py falkordb 20` |

    Counts are recorded per build and backend as [measured: repro_g8_remove_vs_add.py at <commit>, <build>, <backend>, k of 20], with the sequential control beside each. If the repro does not reproduce in 20 of 20 on Neo4j, as G8 did, the counts are recorded and it is not chased.
  - **P5 repro, results (2026-11-16).** The four declared commands ran once each, at harness commit `37aefe8`, on the pinned Neo4j 5.26.2 and FalkorDB 6.0.4 from `baselines/docker-compose.yml`, on the host of §12.1. Both operations were acknowledged in every iteration.

    | Build | Backend | Sequential control | Concurrent iterations that differed | What differed | G8 (harness, v0.31.2) |
    |---|---|---|---|---|---|
    | v0.31.2 | Neo4j | as expected | 19 of 20 [measured: repro_g8_remove_vs_add.py at `37aefe8`, v0.31.2, neo4j, 19 of 20] | Payments and "Alice audited Payments" missing in all 19; nothing unexpected present | 20 of 20 (`20261116T071325Z-4bc1eaa9`) |
    | v0.31.2 | FalkorDB, bound | as expected | 0 of 20 [measured: repro_g8_remove_vs_add.py at `37aefe8`, v0.31.2, falkordb, 0 of 20] | – | 0 of 20 (`20261116T071319Z-334d816c`) |
    | main `ebef986a` | Neo4j | as expected | 19 of 20 [measured: repro_g8_remove_vs_add.py at `37aefe8`, main-ebef986a, neo4j, 19 of 20] | the same two items in all 19 | not run on main |
    | main `ebef986a` | FalkorDB, bound | as expected | 0 of 20 [measured: repro_g8_remove_vs_add.py at `37aefe8`, main-ebef986a, falkordb, 0 of 20] | – | not run on main |

    - **What happened.** On Neo4j, with `remove_episode(G8E)` and `add_episode(G8N)` released together, the acknowledged episode G8N survived, but its own fact "Alice audited Payments" and the entity Payments did not. That held in 19 of 20 iterations on both builds. G8S, G8N, Alice, Acme and "Alice works at Acme" (carried by one episode) were present every time, and G8E and its own fact were gone every time. The one iteration per build that kept everything was iteration 8 on v0.31.2 and iteration 11 on main. On FalkorDB, with the driver bound to the group's graph, all 20 iterations on both builds ended in the expected state. The sequential control, the remove and then the add, reached the expected state in all four runs.
    - **Against the declared rule.** The repro did not reproduce in 20 of 20 on Neo4j, where G8 did: it gave 19 of 20 on each build. Per the declaration, the counts are recorded and the gap is not chased.
    - **Console output.** The Neo4j driver logged `Neo.TransientError.Transaction.DeadlockDetected` and retried the transaction 11 times in the v0.31.2 run and 7 times in the main run, with none on FalkorDB [measured: repro_g8_remove_vs_add.py at `37aefe8`, v0.31.2 and main-ebef986a, neo4j, console output]. The retries are recorded, not explained.
    - **Likely mechanism** [inference from K25 and the code]. `remove_episode` counts each mentioned entity's `MENTIONS` edges and marks an entity with a count of 1 for deletion ([graphiti.py L2193–2202](https://github.com/getzep/graphiti/blob/v0.31.2/graphiti_core/graphiti.py#L2193-L2202)). It deletes the marked entities a few statements later ([L2211–2213](https://github.com/getzep/graphiti/blob/v0.31.2/graphiti_core/graphiti.py#L2211-L2213)). On Neo4j that delete is a `DETACH DELETE` run `IN TRANSACTIONS`, which removes every relationship of the node ([nodes.py L285–309](https://github.com/getzep/graphiti/blob/v0.31.2/graphiti_core/nodes.py#L285-L309)); FalkorDB's branch is a plain `DETACH DELETE` (L247–256). If G8N's mention of Payments and its fact edge are written after the count and before the delete, Payments looks orphaned, and deleting it also takes the edge G8N attached to it. Why FalkorDB kept everything is not established. FalkorDB serialises write queries to one graph (master §7.2, S3), but the count and the delete are separate queries, so that alone does not explain it [inference].
    - **Documentation at v0.31.2** [docs]. No document at the tag says anything about running `remove_episode` concurrently with `add_episode`. `remove_episode` has no docstring ([graphiti.py L2174](https://github.com/getzep/graphiti/blob/v0.31.2/graphiti_core/graphiti.py#L2174)). `add_episode`'s docstring asks for episodes to be added sequentially and names `add_episode` only (K15). The README's concurrency section is about `SEMAPHORE_LIMIT` and model rate limits ([README.md L255–264](https://github.com/getzep/graphiti/blob/v0.31.2/README.md#L255-L264)). The MCP server's README describes its `delete_episode` tool as one that deletes "the entities/facts it solely created" ([mcp_server/README.md L578](https://github.com/getzep/graphiti/blob/v0.31.2/mcp_server/README.md#L578)), which states the intended scope of a delete but not its behaviour under concurrency. So the behaviour is undocumented, and the support level stays none (OBSERVED).
    - **Documentation after the pin** [docs], read on 2026-11-16 for the Phase E drafts. main moved to `869c1b27` (2026-11-15), 5 commits after `ebef986a`. It adds opt-in concurrent ingestion for one graph (#2154) and [spec/concurrent-group-ingestion.md](https://github.com/getzep/graphiti/blob/869c1b279e01a2767a464581e1cb657ce0e39271/spec/concurrent-group-ingestion.md). The spec's §12.2, "Writers outside the sequence" (L1095–1133), lists `remove_episode` among them. For the opt-in path it states that a delete of a node that is an endpoint of a created edge loses the unit's fact (L1117). It says `remove_episode` of an episode whose unit is in progress is not supported (L1130), and that a host needing a strict order runs such writers when no unit is in progress (L1132). It does not state the default serial path's outcome, which is what G8 and the repro measured. `remove_episode` is unchanged between `ebef986a` and `869c1b27` apart from the Kuzu removal [gh: compare]. `869c1b27` was not run. The classification stays OBSERVED; the draft for the maintainer asks whether serial overlap is in scope.
  - **M6 run on main `4ef979c7`, plain and held write: declaration (2026-11-19, committed before any command ran).** Master §12.2 Phase D; asked on #2159 for the full add path.
    - **Build.** getzep/graphiti main at `4ef979c74e1e68d08217cf0af4022ddbc89c257f` (2026-11-17, #2163), read with `gh api` on 2026-11-19. Its only change after `869c1b27` is a release workflow [gh: compare], and its declared dependencies match `ebef986a`'s apart from the removed Kuzu extra. The venv `.state/venvs/graphiti-main-4ef979c7` (CPython 3.12.14) was installed with `uv pip install --no-deps` from `requirements/main-4ef979c7.txt`: `main-ebef986a.txt` with graphiti-core taken from git at that commit. `uv pip freeze` matches the file. No pull-request code is installed.
    - **Repro.** `repros/repro_g8_held_write.py` at `0ea7470`, with its hook tests in `core/tests/test_m6_g8_hold.py`. The fixture, fakes and sequential control are P5's. Variant `gather` is P5's concurrent case unchanged. Variant `held` runs the same two calls, but holds `add_episode`'s bulk write (`add_nodes_and_edges_bulk`, [graphiti.py L1147](https://github.com/getzep/graphiti/blob/4ef979c74e1e68d08217cf0af4022ddbc89c257f/graphiti_core/graphiti.py#L1147), reached from `add_episode` at L1823) until `remove_episode` has run its `MENTIONS` count for every entity it found (L2542–2550). The deletes follow at L2560–2562. The hold is the repro's own wrapper around `graphiti_core.graphiti.add_nodes_and_edges_bulk`, `get_mentioned_nodes` and the instance driver's `execute_query`, installed for the concurrent case only, with a 60 s timeout. Nothing else in either call is changed. Concurrent ingestion stays off, its default.
    - **Before this declaration.** One smoke check per backend of the held variant with 0 iterations: the sequential control only, plus installing and removing the hook on the real package (`.state/scratch/m6-g8/smoke-<backend>-held-0.txt`, both exit 0, control as expected). No concurrent iteration ran.
    - **Commands.** From the root of the `m6` worktree, with only `wm-falkordb` (FalkorDB 6.0.4) and `wm-neo4j` (Neo4j 5.26.2) up through `baselines/docker-compose.yml`. Each runs once, in this order, with stdout and stderr to `.state/scratch/m6-g8/cmd<k>-<backend>-<variant>.txt` and the exit status beside it (not committed). `py` stands for `.state/venvs/graphiti-main-4ef979c7/Scripts/python.exe`.

      | # | Backend | Variant | Command |
      |---|---|---|---|
      | 1 | FalkorDB, bound | gather | `py targets/01-zep-graphiti/repros/repro_g8_held_write.py falkordb gather 20` |
      | 2 | FalkorDB, bound | held | `py targets/01-zep-graphiti/repros/repro_g8_held_write.py falkordb held 20` |
      | 3 | Neo4j | gather | `py targets/01-zep-graphiti/repros/repro_g8_held_write.py neo4j gather 20` |
      | 4 | Neo4j | held | `py targets/01-zep-graphiti/repros/repro_g8_held_write.py neo4j held 20` |

    - **Recording.** Counts as [measured: repro_g8_held_write.py at `0ea7470`, main-4ef979c7, <backend>, <variant>, k of 20], with the sequential control and, for `held`, in how many iterations the bulk write reached the hold before the count had run. Whatever the counts, they are recorded and not chased, and no command is re-run except as a new declared command after a harness bug.
    - **Commands 2 and 4 failed on a harness bug (2026-11-19).** Both ran once and exited 1 with the sequential control as expected, but in all 20 iterations of each the add raised `TypeError: ... execute_query() got multiple values for argument 'query'` before its bulk write. The hold's `execute_query` wrapper named its first parameter `query`, and graphiti-core passes a Cypher parameter `query=` on the add path. The bulk write never reached the hold, so neither command says anything about the interleaving; their counts are not results. Fixed in `6efae63` (the parameter is positional-only), with a unit test that fails on the old wrapper. Commands 1 and 3 installed no hook and are unaffected.
    - **Declaration of commands 5 and 6 (2026-11-19, committed before either ran).** The held variant again, at `6efae63`, the same way as above, with outputs to `.state/scratch/m6-g8/cmd5-falkordb-held.txt` and `cmd6-neo4j-held.txt`. Each runs once.

      | # | Backend | Variant | Command |
      |---|---|---|---|
      | 5 | FalkorDB, bound | held | `py targets/01-zep-graphiti/repros/repro_g8_held_write.py falkordb held 20` |
      | 6 | Neo4j | held | `py targets/01-zep-graphiti/repros/repro_g8_held_write.py neo4j held 20` |

  - **M6 run on main `4ef979c7`: results (2026-11-19).** All six declared commands ran once each, in order, on the pinned FalkorDB 6.0.4 and Neo4j 5.26.2 from `baselines/docker-compose.yml`, with graphiti-core installed from git at `4ef979c7` (the repro prints the commit it found). Commands 1 to 4 ran at `0ea7470`, and 5 and 6 at `6efae63`. Both calls were acknowledged in every iteration of commands 1, 3, 5 and 6.

    | # | Backend | Variant | Sequential control | Concurrent iterations that differed | What differed | Bulk write reached the hold before the count had run | Exit |
    |---|---|---|---|---|---|---|---|
    | 1 | FalkorDB, bound | gather | as expected | 0 of 20 [measured: repro_g8_held_write.py at `0ea7470`, main-4ef979c7, falkordb, gather, 0 of 20] | – | – | 0 |
    | 2 | FalkorDB, bound | held | as expected | not a result: harness bug, the add raised `TypeError` in all 20 | – | – | 1 |
    | 3 | Neo4j | gather | as expected | 19 of 20 [measured: repro_g8_held_write.py at `0ea7470`, main-4ef979c7, neo4j, gather, 19 of 20] | Payments and "Alice audited Payments" missing in all 19; nothing unexpected present | – | 1 |
    | 4 | Neo4j | held | as expected | not a result: the same harness bug | – | – | 1 |
    | 5 | FalkorDB, bound | held | as expected | 0 of 20 [measured: repro_g8_held_write.py at `6efae63`, main-4ef979c7, falkordb, held, 0 of 20] | – | 0 of 20: the count had always run first | 0 |
    | 6 | Neo4j | held | as expected | 20 of 20 [measured: repro_g8_held_write.py at `6efae63`, main-4ef979c7, neo4j, held, 20 of 20] | the same two items in all 20; nothing unexpected present | 2 of 20 (held 2.4 and 94.5 ms) | 1 |

    - **What happened.** On main `4ef979c7`, plain concurrency gave the same picture as P5 on `ebef986a`. On Neo4j, G8N survived but its own fact "Alice audited Payments" and the entity Payments did not, in 19 of 20 iterations; iteration 8 kept everything. On FalkorDB, with the driver bound to the group's graph, all 20 ended in the expected state. With the add's bulk write held until `remove_episode`'s count had run, Neo4j lost the same two items in 20 of 20, and FalkorDB lost nothing in 20 of 20.
    - **Where the add's write landed** [measured: commands 5 and 6, the repro's per-iteration timeline]. In every held iteration on both backends, the bulk write started after `remove_episode`'s last count and returned before `remove_episode` returned. It started 17.4 to 43.2 ms after the count on FalkorDB and 0.5 to 10.3 ms after it on Neo4j. On FalkorDB the add had not reached its write by the time the count finished in any iteration, so the hold never had to wait. The repro does not timestamp `remove_episode`'s deletes, so whether each write landed before or after them is not measured.
    - **Neo4j console output.** The driver logged `Neo.TransientError.Transaction.DeadlockDetected` and retried 14 times in command 3 and 4 times in command 6, with none on FalkorDB [measured: commands 1, 3, 5 and 6, console output]. Recorded, not explained.
    - **Reading.** The full add path, `add_episode` through its bulk write, reproduces G8-F1 on Neo4j on current main, with or without the hold. On FalkorDB neither variant lost anything in these 40 iterations. That is a measured count on this fixture and this host, not a guarantee: why FalkorDB kept everything is still not established (see "Likely mechanism" above), and the deletes' order relative to the write is not known. The classification stays OBSERVED, support level none.
  - **Why `held` is not the interleaving asked on #2159** (recorded 2026-11-19, master §12.2 amendment 2). `held` orders the write after the count, but nothing makes `remove_episode`'s deletes wait for the write. In command 5 the hold never waited, and the deletes were not timestamped. So commands 5 and 6 do not test count → write → delete.
  - **Declaration of commands 7 and 8, `pinned` (2026-11-19, committed before either ran).**
    - **Repro.** `repros/repro_g8_held_write.py` at `73dc7ef`, with its tests in `core/tests/test_m6_g8_hold.py` (17, with fakes). Variant `pinned` forces the order from both sides:
      - the add's bulk write waits until `remove_episode`'s last `MENTIONS` count has returned, as in `held`;
      - `remove_episode`, inside the wrapper of that last count, waits until the bulk write has returned before it goes on to its saves (L2556–2558) and its deletes (L2560–2562).

      Each wait has the 60 s timeout, notes "hold timed out" and goes on. `Edge.delete_by_uuids` and `Node.delete_by_uuids`, called only by `remove_episode`, are timestamped from this commit in every variant. Each iteration prints its order (count done, write start, write returned, the delete starts and returns) and whether it ran count → write → delete. The build, venv, fixture and baselines are as for commands 1 to 6.
    - **Before this declaration.** One smoke check per backend of `pinned` with 0 iterations: the sequential control only, plus installing and removing all five wrappers on the real package (`.state/scratch/m6-g8/smoke-<backend>-pinned-0.txt`, both exit 0, control as expected).
    - **Commands.** Each runs once, in this order, with stdout and stderr to `.state/scratch/m6-g8/cmd7-falkordb-pinned.txt` and `cmd8-neo4j-pinned.txt` and the exit status beside them.

      | # | Backend | Variant | Command |
      |---|---|---|---|
      | 7 | FalkorDB, bound | pinned | `py targets/01-zep-graphiti/repros/repro_g8_held_write.py falkordb pinned 20` |
      | 8 | Neo4j | pinned | `py targets/01-zep-graphiti/repros/repro_g8_held_write.py neo4j pinned 20` |

    - **Recording.** Counts as [measured: repro_g8_held_write.py at `73dc7ef`, main-4ef979c7, <backend>, pinned, k of 20], with the sequential control, the number of iterations that ran count → write → delete, and each iteration's order. They are recorded and not chased.
  - **Commands 7 and 8, `pinned`: results (2026-11-19).** Each ran once, at `73dc7ef`, on the same baselines and build. Both exited 1. The sequential control was as expected, both calls were acknowledged in every iteration, and no hold timed out.

    | # | Backend | Concurrent iterations that differed | What differed | Ran count → write → delete | Write reached the hold before the count | Remove waited for the write |
    |---|---|---|---|---|---|---|
    | 7 | FalkorDB, bound | **20 of 20** [measured: repro_g8_held_write.py at `73dc7ef`, main-4ef979c7, falkordb, pinned, 20 of 20] | Payments and "Alice audited Payments" missing in all 20; G8N present; nothing unexpected | 20 of 20 | 0 of 20 | 20 of 20, 24.1 to 50.5 ms |
    | 8 | Neo4j | **20 of 20** [measured: repro_g8_held_write.py at `73dc7ef`, main-4ef979c7, neo4j, pinned, 20 of 20] | the same two items in all 20 | 20 of 20 | 8 of 20 | 20 of 20, 27.7 to 65.2 ms |

    **Per-iteration order** [measured: commands 7 and 8, the repro's timeline]. Milliseconds from just before the release; "count" is when the last `MENTIONS` count returned. In every row the write started at or after the count and returned before the remove resumed, and the first delete started after that.

    | k | FalkorDB: count | write starts | write returned | remove resumes | edge delete starts | node delete starts | node delete returned | remove returned | Neo4j: count | write starts | write returned | remove resumes | edge delete starts | node delete starts | node delete returned | remove returned |
    |---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
    | 1 | 147.1 | 179.0 | 197.5 | 197.6 | 205.7 | 207.2 | 211.7 | 239.0 | 42.4 | 42.8 | 71.1 | 71.2 | 89.6 | 100.0 | 114.6 | 156.0 |
    | 2 | 60.5 | 78.1 | 90.9 | 91.0 | 100.7 | 103.0 | 108.9 | 131.1 | 53.3 | 54.0 | 84.7 | 84.8 | 102.0 | 113.5 | 127.3 | 169.7 |
    | 3 | 62.3 | 77.6 | 93.6 | 93.8 | 101.2 | 102.6 | 107.2 | 129.0 | 47.8 | 48.6 | 81.2 | 81.3 | 99.7 | 113.1 | 137.1 | 183.5 |
    | 4 | 44.6 | 63.9 | 76.1 | 76.2 | 84.8 | 86.0 | 91.0 | 110.1 | 41.9 | 42.6 | 73.6 | 73.7 | 91.6 | 105.2 | 118.2 | 161.2 |
    | 5 | 48.3 | 70.7 | 81.9 | 82.0 | 90.0 | 91.7 | 95.9 | 114.3 | 45.5 | 45.5 | 74.5 | 74.6 | 96.0 | 139.0 | 152.6 | 197.8 |
    | 6 | 53.5 | 72.0 | 83.7 | 83.8 | 90.7 | 92.0 | 95.6 | 115.5 | 50.0 | 50.0 | 88.2 | 88.3 | 107.2 | 118.4 | 131.6 | 168.9 |
    | 7 | 47.1 | 62.3 | 71.2 | 71.3 | 78.6 | 80.6 | 84.2 | 100.6 | 42.3 | 42.9 | 73.5 | 73.5 | 91.9 | 104.0 | 117.7 | 174.2 |
    | 8 | 44.1 | 63.6 | 72.6 | 72.7 | 79.9 | 81.1 | 85.5 | 103.9 | 67.8 | 67.8 | 125.0 | 125.1 | 145.3 | 161.3 | 177.9 | 224.0 |
    | 9 | 45.7 | 64.5 | 77.8 | 77.9 | 85.8 | 87.7 | 92.2 | 109.5 | 42.4 | 42.4 | 70.2 | 70.3 | 87.2 | 98.6 | 110.9 | 156.4 |
    | 10 | 49.3 | 68.3 | 80.2 | 80.4 | 86.5 | 87.6 | 90.5 | 105.7 | 63.1 | 63.1 | 95.5 | 95.6 | 115.5 | 129.1 | 150.8 | 195.8 |
    | 11 | 53.8 | 73.6 | 86.1 | 86.2 | 92.8 | 93.9 | 96.5 | 112.0 | 51.7 | 52.5 | 116.9 | 116.9 | 166.4 | 178.6 | 221.8 | 265.3 |
    | 12 | 50.9 | 66.2 | 76.3 | 76.4 | 83.2 | 84.8 | 88.9 | 105.5 | 39.0 | 40.4 | 66.6 | 66.7 | 83.7 | 96.6 | 108.6 | 146.4 |
    | 13 | 47.5 | 61.3 | 72.9 | 73.1 | 81.6 | 82.9 | 88.2 | 104.6 | 42.1 | 42.6 | 72.6 | 72.7 | 89.3 | 101.3 | 116.3 | 159.8 |
    | 14 | 41.9 | 57.8 | 66.7 | 66.8 | 72.9 | 74.3 | 78.1 | 92.1 | 50.9 | 51.0 | 83.8 | 83.9 | 104.3 | 116.6 | 130.7 | 174.4 |
    | 15 | 41.7 | 56.6 | 65.7 | 65.8 | 71.8 | 73.2 | 77.1 | 91.4 | 40.8 | 42.2 | 69.6 | 69.6 | 88.9 | 101.3 | 114.2 | 154.9 |
    | 16 | 45.3 | 65.7 | 79.5 | 79.7 | 88.6 | 90.2 | 94.2 | 118.4 | 52.2 | 52.3 | 81.0 | 81.1 | 101.3 | 115.9 | 130.0 | 172.5 |
    | 17 | 47.0 | 62.5 | 74.1 | 74.2 | 80.0 | 80.9 | 84.8 | 107.0 | 52.2 | 52.2 | 91.7 | 91.8 | 122.8 | 137.4 | 156.6 | 212.6 |
    | 18 | 39.4 | 59.2 | 70.2 | 70.2 | 77.1 | 78.3 | 81.4 | 99.7 | 51.1 | 53.3 | 88.0 | 88.1 | 109.5 | 121.8 | 137.1 | 217.1 |
    | 19 | 46.1 | 63.4 | 72.1 | 72.2 | 78.7 | 80.4 | 85.3 | 102.7 | 53.4 | 55.6 | 113.6 | 113.6 | 148.9 | 160.5 | 174.4 | 229.2 |
    | 20 | 40.8 | 60.3 | 71.1 | 71.2 | 78.2 | 79.5 | 82.9 | 100.1 | 48.5 | 50.4 | 79.4 | 79.5 | 98.4 | 111.4 | 129.7 | 180.4 |

    - **What happened.** With the order forced, the outcome no longer depends on the backend. G8N's own fact "Alice audited Payments" and the entity Payments were gone in 20 of 20 iterations on FalkorDB as on Neo4j, while G8N itself survived. That fits the "Likely mechanism" above [inference from the forced order and the code]: the count saw Payments mentioned only by G8E, the add then attached G8N's mention and fact to Payments, and the delete removed Payments with them. The loss under this order is now measured on FalkorDB too.
    - **Reading, corrected.** The 0 of 20 on FalkorDB in commands 1 and 5 does not mean FalkorDB avoids the loss. In those runs nothing forced the delete to wait for the write; a likely reason they kept everything is that the deletes ran before the add's write [inference: command 7 loses whenever the write lands between the count and the delete, and command 5's write returned before `remove_episode` returned without the deletes being timed]. Commands 1 to 6 remain the counts for unforced concurrency. G8-F1 stays OBSERVED, support level none, now on both backends when the interleaving occurs.
    - **No Neo4j retries.** Neither pinned run logged a `DeadlockDetected` retry.
- I5 held on both backends: G8E and its own fact were gone after every acknowledged remove, and no concurrent ingest brought them back.

### 12.6 INVALID cell: G6a, fresh, on main `ebef986a` with Neo4j

- **INVALID: the harness could not bound a stalled search on this build.** Runs `20261116T055056Z-3d69b1c9` (main batch) and `20261116T071959Z-74370fb1` (re-run batch `m5h`).
  - The first wrote states 0–7, so trials 1 to 7 completed, about 6 s apart, and then it hung [measured: the committed `state/` files of `20261116T055056Z-3d69b1c9`]. A search stalled, and closing the instance did not end its server transactions; the next trial's data read waited behind them. At `8b9785a` a trial whose search stalls writes no state [code: `targets/01-zep-graphiti/witnessmark_graphiti/g6.py:296,308` @ `8b9785a`], so the stall was most likely in trial 8 and the wait in trial 9 [inference]. Corrected at Phase E from "hung in its sixth trial, after writing states 0–5".
  - After the fix in `425e22e`, the re-run hung in its fourth trial, after writing states 0–3. This time the 60 s search timeout itself never fired, and the process showed no CPU change.
  - Both were ended (driver notes in `evidence/graphiti/errors/m5g-20261116T051149Z/` and `evidence/graphiti/errors/m5h-20261116T071955Z/`), and `wm-neo4j` was restarted afterwards with no transaction left open. Row 11 is not run a third time (maintainer ruling).
- In the batches it reproduced on main only: v0.31.2 and #2119 completed G6a on Neo4j. Two scratch smoke runs on v0.31.2 before the batch, kept out of `evidence/`, also saw a stalled search (§5, amendments).
- The cause is not established [inference]. `asyncio.wait_for` waits for a timed-out call to finish cancelling, so a call that answers cancellation with more waiting would hold it forever without using CPU. A unit test shows this mechanism with a fake, and `0395799` replaces the wait. A call that blocks the event loop outright would explain it too. Neither was confirmed, and no further Neo4j G6 cell ran.
- The Neo4j driver's console output during G8 also showed `DeadlockDetected` transient errors that the driver retried. They are not part of any run's evidence.

### 12.7 Not run, and choices made without the maintainer

- **Not run.**
  - G6 at v0.1's 20k facts (§5).
  - G6c on Neo4j (NOT_APPLICABLE).
  - The combined MCP image (NOT_EXERCISED).
  - A third run of G6a on Neo4j with main.
  - Single-file repros: G8-F1's ran in Phase E (§12.5). G6 and G7 have none; their findings are OBSERVED behaviour of the engine or of the deployment configuration, not candidate Graphiti defects.
  - Nothing was posted. No outreach drafts were written in Phase C; any comment on #2119 or #2117 would be a draft for the maintainer under master §11.1.
- **Choices taken as the most conservative option** (maintainer ruling 1, 2026-11-16):
  1. After a stall, end the leftover server transactions and fall back to restarting the test container. This disturbs the next trial least and always leaves a clean server.
  2. Give the `m5h` batch no report, because it has no manifest to build one from.
  3. Restart `wm-neo4j` after ending the `m5h` run, although no transaction was left.
  4. Record the two G6a Neo4j/main runs as one INVALID cell rather than reporting their partial trials.
  5. Report G6-F1 from the monitor records for the RELATES_TO index alone. The report's column counts samples taken while any index was under construction.
