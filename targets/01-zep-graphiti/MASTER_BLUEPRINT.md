# Target 01: Graphiti (getzep/graphiti)

Part of Witnessmark. Read it together with the [master blueprint](../../MASTER_BLUEPRINT.md). "Master §n" refers to that document.

| | |
|---|---|
| Status | Specification v0.1, 2026-11-13. Nothing has been measured. Every expectation below is [unmeasured] until a run says otherwise. |
| Project | [getzep/graphiti](https://github.com/getzep/graphiti), Apache-2.0. A Python framework that keeps a temporal knowledge graph in Neo4j, FalkorDB, Kuzu or Neptune. |
| Line under test | graphiti-core v0.31.x. Primary pin: **v0.31.2**, tag commit `d72407dcedac911e1be9fc15b55e8c05a3efcc36` (2026-10-20), which is also the current PyPI release. Before filing anything, re-run on main: `ebef986a0b2360211b65751c111cacb4a7d790eb` (2026-11-11) or newer. |
| Pull requests under regression | [#1867](https://github.com/getzep/graphiti/pull/1867) at head `a30934e18b9582fbea3aca742269fc2174b67f07`; [#2119](https://github.com/getzep/graphiti/pull/2119) at head `b2b727e05467346b6516e2c68e193f8142ef208b` |
| Backends | FalkorDB 6.0.4 and Neo4j 5.26.2 (master §7) |
| Models | Deterministic stubs (§4 below); no API keys |
| Out of scope | Kuzu (archived upstream), Neptune, the hosted Zep service |

All source links point at the v0.31.2 tag.

## 1. What is already known

| # | Fact | Tag |
|---|---|---|
| K1 | The README describes the ingestion pipelines as designed for high concurrency. It sets the default concurrency low to avoid LLM rate limits, with `SEMAPHORE_LIMIT` defaulting to 10 ([README.md L255–264](https://github.com/getzep/graphiti/blob/v0.31.2/README.md#L255-L264)). | [docs] |
| K2 | The MCP server processes one group's episodes sequentially; the code comment says this is to avoid race conditions ([graphiti_mcp_server.py L421](https://github.com/getzep/graphiti/blob/v0.31.2/mcp_server/src/graphiti_mcp_server.py#L421)). The queue is an in-process `asyncio.Queue` per `group_id` ([queue_service.py L12–49](https://github.com/getzep/graphiti/blob/v0.31.2/mcp_server/src/services/queue_service.py#L12-L49)). | [code] |
| K3 | `Graphiti.add_episode` ([graphiti.py L1334](https://github.com/getzep/graphiti/blob/v0.31.2/graphiti_core/graphiti.py#L1334)) shows no per-group guard of its own. M2 confirms this. | [inference] |
| K4 | A concurrency fix already exists in this code path. `_resolve_request_scope` ([graphiti.py L1304–1332](https://github.com/getzep/graphiti/blob/v0.31.2/graphiti_core/graphiti.py#L1304-L1332)) replaced the reassignment of a shared driver. According to its docstring, that reassignment let concurrent calls for different groups persist episodes in the wrong graph (#1676). | [code] |
| K5 | `_apply_temporal_invalidation` sets `expired_at = now` for any edge that has an `invalid_at` ([edge_operations.py L727–728](https://github.com/getzep/graphiti/blob/v0.31.2/graphiti_core/utils/maintenance/edge_operations.py#L727-L728)). The loop over later candidates runs only while `expired_at` is still unset (L731–743). | [code] |
| K6 | [getzep/graphiti#2012](https://github.com/getzep/graphiti/issues/2012) (open) reports that edges with a future `invalid_at` are created already expired. A community member (Adam13y) published four known-answer cases, R1–R4. On v0.31.1 the results were R1 pass, R2 fail, R3 pass, R4 fail. On #1867 at `a30934e` only R3 passed, so R1 regresses there. Maintainers have not yet said what `expired_at` should mean when a future end of validity is known. Another commenter notes that `resolve_extracted_edge` is reached through several call sites, `add_triplet` among them. | [gh] |
| K7 | [getzep/graphiti#1867](https://github.com/getzep/graphiti/pull/1867) (open; last updated 2026-09-10; GitHub reports merge conflicts) closes [#1865](https://github.com/getzep/graphiti/issues/1865): temporal deduplication collapses disjoint occurrences. Its CLA is signed. Its description cites a separate Neo4j datetime correction in #1866. | [gh] |
| K8 | [getzep/graphiti#1166](https://github.com/getzep/graphiti/issues/1166) (open): node attributes have no temporal versioning. | [gh] |
| K9 | `FalkorDriver` starts `build_indices_and_constraints` as a background task in its constructor ([falkordb_driver.py L178–184](https://github.com/getzep/graphiti/blob/v0.31.2/graphiti_core/driver/falkordb_driver.py#L178-L184)). Every `clone(database=…)` constructs a new driver (L334–347), so each group's driver starts its own index build. [getzep/graphiti#2119](https://github.com/getzep/graphiti/pull/2119) (open, fixes #1643) awaits that task before queries. | [code] [gh] |
| K10 | On FalkorDB, each non-default `group_id` is a separate graph (falkordb_driver.py L334–347; the MCP server's comment at L1132). | [code] |
| K11 | The root [docker-compose.yml](https://github.com/getzep/graphiti/blob/v0.31.2/docker-compose.yml) pins `neo4j:5.26.2` (L30) and `falkordb/falkordb:latest` (L51), and mounts the FalkorDB volume at `/data` (L56). The MCP compose file mounts the same image's volume at `/var/lib/falkordb/data` ([docker-compose-falkordb.yml L11](https://github.com/getzep/graphiti/blob/v0.31.2/mcp_server/docker/docker-compose-falkordb.yml#L11)). The root file's mount may therefore not hold FalkorDB's data; G7 measures it. | [code] [inference] |
| K12 | [getzep/graphiti#2117](https://github.com/getzep/graphiti/issues/2117) (open) reports FalkorDB data lost when the MCP containers restart. In the combined image, Redis is daemonized and then the MCP server is exec'd, so stopping the container kills Redis before it saves; the RDB schedule is the default and `appendonly` is off. The two-container setup has no AOF and no restart policy. | [gh] |
| K13 | [getzep/graphiti#2142](https://github.com/getzep/graphiti/issues/2142) (open): a FalkorDB fulltext query fails on a lone `_` token. [getzep/graphiti#2021](https://github.com/getzep/graphiti/issues/2021) (open): FalkorDB reads return the full embedding, which the record parser then discards. | [gh] |
| K14 | Contribution rules: file an issue first; feature pull requests need `rfc-approved`; a CLA is signed when the bot asks ([CONTRIBUTING.md](https://github.com/getzep/graphiti/blob/v0.31.2/CONTRIBUTING.md)). | [docs] |

## 2. How ingestion works, and where it can race

`add_episode(name, episode_body, source_description, reference_time, source, group_id, …)` runs these steps:

1. **Request scope.** Resolves a per-call driver for the group (L1304).
2. **Context.** Retrieves previous episodes.
3. **`extract_nodes`.** One model call (L1471).
4. **`resolve_extracted_nodes`.** Searches existing candidates (fulltext and embedding similarity), then a model call deduplicates (L1480).
5. **`extract_edges`.** One model call.
6. **`resolve_extracted_edges`.** Searches related edges and invalidation candidates, then makes model calls to deduplicate and to detect contradictions. It also extracts dates and applies `_apply_temporal_invalidation` ([edge_operations.py L424](https://github.com/getzep/graphiti/blob/v0.31.2/graphiti_core/utils/maintenance/edge_operations.py#L424), L715, L834).
7. **`add_nodes_and_edges_bulk`.** The write, inside `_process_episode_data` (L984, L1037).

The other entry points are `add_episode_bulk` (L1588), `add_triplet` (L2033, which calls `resolve_extracted_edge` at L2156) and `remove_episode` (L2174).

**Race windows** (both [inference] until G1 and G2 measure them):

| Window | Steps | What can go wrong |
|---|---|---|
| W1, entities | 4 → 7 | Two episodes name the same new entity. Both search, both find nothing, and both create it. |
| W2, facts | 6 → 7 | Two contradicting facts each look for invalidation candidates before the other has been written. Neither invalidates the other, so two versions stay current (I7a). |

Neither backend's per-statement guarantees cover these windows, because the search, the model call and the write are separate statements. FalkorDB serialises writes to one graph, which orders the writes but does not re-run the search. Neo4j at read committed behaves the same way for this purpose.

## 3. Environment and pins

| Component | Pin |
|---|---|
| graphiti-core | 0.31.2 wheel from PyPI. Also git installs of main at `ebef986a`, `refs/pull/1867/head` at `a30934e1` and `refs/pull/2119/head` at `b2b727e0`. |
| Python | 3.12; the package requires ≥3.10 and <4 |
| FalkorDB | 6.0.4 by digest (master §7.2). The Python driver version is whatever the pin resolves, and it is recorded. |
| Neo4j | 5.26.2 Community (master §7.3) |
| Concurrency setting | `SEMAPHORE_LIMIT` is recorded with every run; it runs at 10 (the default) and at 1 (a control) |
| Models | In-process stubs (§4) |

## 4. Stub contract

| Client | Implementation |
|---|---|
| LLM | A subclass of `LLMClient` that overrides `_generate_response(messages, response_model, max_tokens, model_size, *, model)` ([client.py L153–162](https://github.com/getzep/graphiti/blob/v0.31.2/graphiti_core/llm_client/client.py#L153-L162)). The public `generate_response` passes `group_id` and `prompt_name` (L208–219). The stub dispatches on `prompt_name` where one is given, and otherwise on the class name of `response_model`. Every answer is a dict that validates against `response_model`. |
| Embedder | `EmbedderClient.create` and `create_batch` ([embedder/client.py L30–38](https://github.com/getzep/graphiti/blob/v0.31.2/graphiti_core/embedder/client.py#L30-L38)), returning deterministic vectors (master §8). |
| Reranker | `CrossEncoderClient.rank(query, passages)`, returning `[(passage, score)]` ([cross_encoder/client.py L28](https://github.com/getzep/graphiti/blob/v0.31.2/graphiti_core/cross_encoder/client.py#L28)). |

**Ideal-model deduplication.** Answers to the deduplication and contradiction prompts are computed from the candidates shown in the prompt and the fixture's canonical keys (master §8).

**Clock.** Fixtures give `valid_at` and `invalid_at` relative to a fixed "now" captured at the start of the run, as the #2012 cases do.

**Prompt inventory.** M2 lists every `prompt_name` used at the pin. A prompt that has no fixture fails the run.

## 5. Scenarios

### G1. Concurrent ingest into one group (I1 Form B, I2): the headline

- **Setup.** An empty group g and a corpus of 20 short episodes. Every episode names the same three entities, with canonical keys `alice`, `acme` and `payments`, and carries one fact found in no other episode.
- **Modes.**

  | Mode | How the 20 episodes run |
  |---|---|
  | G1a, asyncio | One Graphiti instance runs 20 `add_episode` coroutines, released together by an `asyncio.Barrier`. |
  | G1b, process | 4 processes × 5 episodes. Each process has its own Graphiti instance and its own driver. |
  | G1c, cross-group regression (#1676) | One instance ingests 20 episodes spread over 4 groups. Every episode must land in its own group's graph. |
  | G1-SC, sequential control | One at a time. |
  | G1-Q, queue control | Through a FIFO queue per group, the way the MCP server does it. Expected to match G1-SC. |

- **Checks.**
  - Exactly one entity node per canonical key per group (I1 Form B).
  - All 20 unique facts present, each exactly once (I2).
  - Every episode linked to its entities.
- **Contention evidence.** The overlap control (master §6.2). The stub log must show that clients' search-to-write windows (W1, W2) overlapped.
- **Expected.**
  - G1-SC and G1-Q: 3 entities and 20 facts.
  - G1a and G1b: [unmeasured].
  - G1c: PASS, because #1676 is fixed in code (K4).
- **Expectation basis.** Deduplication is a documented feature. The MCP server itself says per-group serialisation avoids races (K2). If concurrent duplicates appear, the finding is about scope. Uniqueness then depends on per-group serialisation, which graphiti_core does not provide, and which a single MCP process provides only within itself.

### G2. Concurrent contradicting facts (I7a)

- **Setup.** 10 episodes. Each asserts `alice WORKS_AT company_i`, with distinct `valid_at` times t₁ < … < t₁₀, and all are released together.
- **Sequential control.** A chain: each version i < 10 ends at tᵢ₊₁, and exactly one version is current.
- **Checks.**
  - No two current versions with overlapping valid intervals (I7a).
  - The number of current versions.
  - The chain is consistent.
- **Expected.** [unmeasured].

### G3. Bitemporal known-answer suite, end to end (I7b, I7c)

**Two readings of `expired_at`.** The harness takes no side between them (master §5.7):

- **Reading A** is the standard bitemporal model and what #2012 expects. Transaction time ends only when a fact is superseded, and a known end of validity does not set `expired_at`.
- **Reading B** is the rule in the current code (comment at L726). An edge that arrives with any end date is already historical, so it is expired at ingest.

**Cases.**

| Case | Source | Situation | Reading A expects | Reading B expects |
|---|---|---|---|---|
| R1 | #2012 | Future `invalid_at` (+365 d), no candidates | `expired_at` null | `expired_at` set |
| R2 | #2012 | Future `invalid_at`, one unrelated candidate | null | set |
| R3 | #2012 | Past `invalid_at` (−45 d), one unrelated candidate | set (control) | set |
| R4 | #2012 | Interval −15 d to +7 d, a later contradiction at +16 d | `invalid_at` stays +7 d; `expired_at` null | `invalid_at` stays +7 d; `expired_at` set |
| R5 | #1865 | An assignment repeated after its earlier occurrence ended | both intervals kept | both intervals kept |
| R6 | this harness | An open-ended fact contradicted by a later one | `invalid_at` = the new `valid_at`; `expired_at` set | same |

**Metamorphic relation MR1, context independence.** An edge's temporal fields must not depend on whether unrelated edges exist. R1 and R2 differ only by an unrelated candidate, so they must give the same `expired_at`. MR1 holds under either reading. K6 suggests v0.31.x breaks it: R1 is unexpired only because the no-candidate path returns early.

**Matrix.**

- **Entry points:** `add_episode`, `add_episode_bulk` and `add_triplet`. All three reach `resolve_extracted_edge` (K6).
- **Builds:** v0.31.2, main and #1867.
- **Backends:** FalkorDB and Neo4j. Because the backends are real, this also tests how datetimes round-trip through storage.

**Relation to the published cases.** The community script calls `resolve_extracted_edge` directly, without a database. G3 reuses its case definitions, credited to Adam13y, but writes its own implementation and drives it through the public entry points.

### G4. Read your writes on search (I3)

- **Procedure.** After `add_episode` returns, search for its unique fact at once:
  - from the same process, using the hybrid, fulltext-only and similarity-only search recipes;
  - from a second process.
- **Measured.** The visibility lag λ per backend and per path.
- **Expected.** [unmeasured].

### G5. Backend parity (I4)

- **Setup.** The G1-SC corpus plus 50 more scripted episodes, ingested sequentially on both backends.
- **Compared.**
  - Canonical dumps: entities, facts, temporal fields (including time zones) and episodic links.
  - A fixed suite of 30 search queries, including `_` (#2142), hyphens, quotes and non-ASCII text.
- **Classification.** Each query is identical, rejected or silently different.

### G6. Index readiness at startup (I4 while indexes build; #2119, #1643)

- **Cases.**
  - **G6a, fresh.** Construct the driver and query at once. This is the race #2119 describes.
  - **G6b, populated.** Load 20k facts, restart the container, then query. Do it once straight away, and once after `db.indexes()` reports every index `OPERATIONAL`.
  - **G6c, many groups.** 8 groups ingest concurrently, and each clone starts its own index build (K9).
- **Measured.**
  - Answers, compared with a control taken after every index is operational.
  - Errors.
  - Task exceptions that were never retrieved.
- **Builds.** v0.31.2 and #2119.
- **If indexes are still building when creation returns.** If FalkorDB still reports indexes `UNDER CONSTRUCTION` after the creation call returns, record for how long (master KD-F4). That shows whether awaiting the task is enough.

### G7. Persistence across restarts (I2 across a restart; #2117)

- **Variants.**
  - The root `docker-compose.yml`, with the FalkorDB volume at `/data`.
  - `mcp_server/docker/docker-compose-falkordb.yml`, with the volume at `/var/lib/falkordb/data`.
  - The combined image, `mcp_server/docker/docker-compose.yml`.
- **Actions.** After ingesting K episodes, try each of:
  - `docker compose restart`;
  - `down` then `up`, which recreates the container and keeps the volume;
  - `docker kill` then start.
- **Checks.**
  - Episodes, entities and facts survive each action.
  - FalkorDB's persistence settings are recorded.
- **Expectation basis.** A compose file that declares a named volume implies persistence [inference]. #2117 states the expected behaviour [gh].

### G8. Deletion permanence (I5; lower priority)

- **Procedure.** Run `remove_episode(e)` concurrently with an `add_episode` whose episode shares e's entities.
- **Checks.** After both return:
  - the facts unique to e are gone;
  - the shared entities remain;
  - the concurrent ingest has brought nothing back.

## 6. Checks

**Canonical dump, per group.**

| Element | Fields |
|---|---|
| `EntityNode` | name, canonical key (from the fixture tag), labels. The uuid is not compared. |
| `EntityEdge` | endpoints by canonical key, name, fact, `valid_at`, `invalid_at`, `expired_at`, episodes. `created_at` is used only for ordering. |
| Episodes | `EpisodicNode` and its mention links |

**Predicates.**

| Check | Predicate |
|---|---|
| I1 Form B | One node per canonical key |
| I2 | The fixture's facts are a subset of the dump |
| I7a | No pair of current versions of one functional key overlaps |
| I7b, Reading A | Every expired edge has a superseding edge recorded when it expired |
| MR1 | R1 and R2 give the same `expired_at` |
| I4 | Dumps are equal across backends, and so are the search-suite answers |

## 7. Deliverables

| # | Deliverable |
|---|---|
| D1 | Concurrency matrix: G1 (modes × backends × builds), plus G2 |
| D2 | Temporal matrix: G3 cases × entry points × builds × backends, under Readings A and B, plus MR1 |
| D3 | Startup and persistence tables: G6 and G7 |
| D4 | One single-file repro per FAIL: standard library, graphiti-core, the driver and the stub, with the sequential control printed |
| Drafts | In `drafts/`, never committed: one issue for any new concurrency finding, and comments for #2012, #2119 and #2117 |

## 8. Contribution plan (non-competing)

1. Before drafting anything, check the trackers again and re-run on the newest release.
2. **#2012.** Comment with D2, framed by both readings and MR1. No pull request: the semantics are not settled, #1867 is open, and the project works issue-first.
3. **#1867.** Report its results in the #2012 thread, where the cases were defined.
4. **New concurrency findings (G1, G2).** Search for an existing issue. If there is none, file one with the bug template. Include:
   - a minimal repro using the stub;
   - results on both backends;
   - the sequential control;
   - the MCP queue (K2) as context.

   Offer options without a pull request: document per-group serialisation, add a per-group lock in core, or key entities so that writes merge.
5. **#2119.** A supportive comment with the G6 data.
6. **#2117.** A comment with the G7 matrix. Mention the `/data` mount only if it was measured.
7. **Engine root causes** go to FalkorDB's tracker (master §11.3).
8. **CLA.** Sign it before any pull request (K14). All outreach follows master §11.

## 9. Exit and drop rule

- **G1 and G2 clean.** If both are clean in every mode, with the overlap control met, publish the clean matrix and credit the project. G3, G6 and G7 stand on their own either way.
- **Controls fail.** If G1-SC or G1-Q fails, the run is INVALID. Fix the fixture before anything else.

## 10. Open questions

| Question | Settled in |
|---|---|
| Does `add_episode_bulk` invalidate and deduplicate across the items of one batch? | Read in M2 |
| Is running several MCP server processes against one database a supported deployment? This decides whether multi-process results are BOUNDARY or FAIL. | Ask, or read the docs, in M2 |
| When do Neo4j fulltext and vector indexes reflect a committed write? | Master §13 |
| What is the full `prompt_name` inventory at the pin? | M2 |
| How do datetimes round-trip on each backend? #1867 cites a separate Neo4j datetime fix, #1866. | G3, G5 |
