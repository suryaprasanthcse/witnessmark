# Target 01: Graphiti (getzep/graphiti)

Part of Witnessmark. Read it together with the [master blueprint](../../MASTER_BLUEPRINT.md). "Master §n" refers to that document.

| | |
|---|---|
| Status | Specification v0.2, 2026-11-13. Implemented in M2. Results are in §11 and [evidence/M2_GRAPHITI.md](../../evidence/M2_GRAPHITI.md). A finding counts only when a run in `evidence/` backs it. |
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

### G6–G8 (not yet implemented)

- **G6:** index readiness at startup (#2119, #1643).
- **G7:** persistence across restarts (#2117, K11).
- **G8:** deletion permanence.

The v0.1 designs stand. They come after M2.

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
| When do Neo4j fulltext and vector indexes reflect a committed write? | G4 on Neo4j |
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
