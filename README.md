# Witnessmark

Witnessmark checks seven concurrency and temporal invariants, I1 to I7, on graph databases and agent-memory layers. Every verdict comes with a witness: the raw, replayable record of the operations that produced it.

> **M1 to M6 are reviewed and signed off. M5 results: [evidence/M5_OMNIGRAPH.md](evidence/M5_OMNIGRAPH.md), [evidence/M5_GRAPHITI.md](evidence/M5_GRAPHITI.md) and [evidence/M5_COGNEE.md](evidence/M5_COGNEE.md), and the M5 summary in [MASTER_BLUEPRINT.md](MASTER_BLUEPRINT.md), §12.1. M6 is in §12.2.**
> - M1 calibrated the core runner and the two baseline adapters against FalkorDB 6.0.4 and Neo4j 5.26.2.
> - M2 added the memory-layer runner and the Graphiti adapter. Results: [evidence/M2_GRAPHITI.md](evidence/M2_GRAPHITI.md), and the Graphiti blueprint's §11.
> - M3 added the Cognee adapter and its HTTP stub endpoint. Results: [evidence/M3_COGNEE.md](evidence/M3_COGNEE.md) (with three re-run reports), and the Cognee blueprint's §12.
> - M4 added the Omnigraph adapter and its cost, failover-boundary and visibility runs. Results: [evidence/M4_OMNIGRAPH.md](evidence/M4_OMNIGRAPH.md) (with four more reports for the earlier batches and the re-run), and the Omnigraph blueprint's §10.
> - M5 ran Graphiti G6–G8 across a matrix covering v0.31.2, main and the #2119 head, recorded the Cognee #5253 regression bar on released builds, and ran Omnigraph O1–O6 across v0.15.0 and the pinned edge build. The Cognee #5253 head was NOT_EXERCISED.
> - M6 enforced the §9.7 valid-trials rule in the verdict code, added a standalone FalkorDB fulltext repro, and re-ran Graphiti G8 on main `4ef979c7` with the count → write → delete order forced. The Omnigraph O2a re-run on v0.16.0 is carried forward.
>
> The blueprints below are the contract the code is built against.

## Findings so far

- **Graphiti G8.** On v0.31.2 with Neo4j 5.26.2, an overlapping `remove_episode` and `add_episode` lost the acknowledged add's fact and entity in 20 of 20 harness trials [measured: `20261116T071325Z-4bc1eaa9`]. On FalkorDB 6.0.4 it happened in 0 of 20 with the harness timing [measured: `20261116T071319Z-334d816c`]. @ptimizeroracle observed the loss on the same FalkorDB version with Graphiti main `869c1b2` under a different timing [gh]. With the count → write → delete order forced on main `4ef979c7`, both FalkorDB and Neo4j lost them in 20 of 20 iterations [measured: repro_g8_held_write.py at `73dc7ef`, commands 7 and 8]. Open PR #2177 re-checks mentions and fact episodes in the statements that delete; on FalkorDB and Neptune it narrows the entity window rather than closing it [gh]. [Graphiti #2159](https://github.com/getzep/graphiti/issues/2159), [#2177](https://github.com/getzep/graphiti/pull/2177)
- **Omnigraph O2a.** On v0.15.0 and edge `b2dbaff`, every valid contested claim trial had one winner. Losing claims returned two different typed refusals [measured: `20261115T231454Z-7f2e75a3`, `20261115T231539Z-c7be08c9`]. The refusal type was fixed upstream in #1426 [gh]. [Omnigraph #1424](https://github.com/ModernRelay/omnigraph/issues/1424), [#1426](https://github.com/ModernRelay/omnigraph/pull/1426)
- **Graphiti G7.** With FalkorDB 6.0.4, a kill followed by a start lost writes since the last snapshot in 10 of 10 trials on each tested Compose layout with `appendonly no` [measured: `20261116T071025Z-e638bddf`, `20261116T071238Z-cfee79ff`]. Both layouts retained the writes with `appendonly yes` [measured: `20261116T092142Z-a5ceedc5`, `20261116T092229Z-98725745`]. Open PR #2118 enables the append-only file on all three Compose paths and cites the measurement [gh]. [Graphiti #2117](https://github.com/getzep/graphiti/issues/2117), [#2118](https://github.com/getzep/graphiti/pull/2118)
- **Cognee.** On v1.6.8 with Neo4j and LanceDB, concurrent writers left duplicate vector IDs in 13 of 14 valid C2 trials [measured: `20261114T214705Z-8a40b975`]. The proposed fix's head was NOT_EXERCISED because its patch did not apply to v1.6.8. [Cognee #5253](https://github.com/topoteretes/cognee/pull/5253)
- **FalkorDB fulltext.** Through Graphiti, FalkorDB 6.0.4 returned fewer rows or the full set while the fulltext index was `UNDER CONSTRUCTION` [measured: `20261116T051153Z-2e987ec0`, `20261116T051801Z-c9fd6666`, `20261116T052409Z-5885a291`]. A standalone Cypher repro, `baselines/repros/repro_falkordb_fulltext_under_construction.py`, saw fewer rows and no error in 20 of 20 trials at 2,000 and at 20,000 relationships [measured: repro at `48b113f`, commands 1 and 2]. [FalkorDB #3931](https://github.com/FalkorDB/FalkorDB/issues/3931)
- **FalkorDB LIMIT/SKIP.** GNOMON identified the planner deviation retained in Witnessmark's baseline as KD-F1 [ours]. [FalkorDB #3694](https://github.com/FalkorDB/FalkorDB/issues/3694), [proposed fix #3699](https://github.com/FalkorDB/FalkorDB/pull/3699)

## Quick start

You need Python 3.10 or newer and Docker. The core uses only the Python standard library. Each target adapter needs the pinned packages or builds listed in its setup section. See [Graphiti §3](targets/01-zep-graphiti/MASTER_BLUEPRINT.md#3-environment-and-pins), [Cognee §3](targets/02-cognee/MASTER_BLUEPRINT.md#3-the-matrix) and its [frozen requirements](targets/02-cognee/requirements/), and [Omnigraph §4](targets/03-omnigraph/MASTER_BLUEPRINT.md#4-environment-and-pins).

```bash
python wm.py selftest
```

```bash
docker compose -f baselines/docker-compose.yml up -d
```

```bash
python wm.py env
```

```bash
python wm.py calibrate --write M1_CALIBRATION_LOCAL.md
```

```bash
docker compose -f baselines/docker-compose.yml down
```

`calibrate` runs the control matrix (master blueprint, section 7.6) and writes raw evidence under `evidence/`. In the [committed M1 calibration](evidence/M1_CALIBRATION.md), Neo4j's `KNOWN_DEVIATION` rows are the positive control for the naive claim pattern under Neo4j's documented read-committed isolation.

## Reproduce the committed reports

The report command reads existing evidence and needs only the core. Run these examples from the repository root in a shell with `cmp`, such as Git Bash on Windows.

```bash
python wm.py report --calibration --batch m1-20261113T162442Z --write M1_CALIBRATION_REBUILT.md
cmp evidence/M1_CALIBRATION.md M1_CALIBRATION_REBUILT.md

python wm.py report --memory --batch m2-20261113T174128Z --title "M2: Graphiti" --write M2_GRAPHITI_REBUILT.md
cmp evidence/M2_GRAPHITI.md M2_GRAPHITI_REBUILT.md
```

For each other memory-layer report, take the title and batch ID from its first line, dropping the leading `# ` and passing the text before `: batch` as the title. `cmp` exits successfully when the files match byte for byte.

I ran the measurements on one Windows 11 laptop with Docker Desktop. Timings are host-specific. The verdicts transfer within the stated builds, workloads and support boundaries. [Master blueprint §10](MASTER_BLUEPRINT.md#10-reporting-rules)

## What it checks

| ID | Invariant | In one line |
|---|---|---|
| I1 | Single winner | Of N concurrent guarded claims or creates of one thing, at most one succeeds |
| I2 | No lost writes | Every acknowledged write survives, unless a later acknowledged write replaces it |
| I3 | Read your writes | A read after an acknowledged write sees it; the visibility lag is measured |
| I4 | Equivalence | The same question on the same data gets the same answer across engines and index states |
| I5 | Deletion permanence | Deleted data never comes back, and a delete never takes live data with it |
| I6 | Snapshot integrity and cost | A branch or copy is one point in time and stays isolated; its cost is measured |
| I7 | Bitemporal integrity | One current version per single-valued fact; valid time and transaction time stay separate |

The formal definitions are in [MASTER_BLUEPRINT.md](MASTER_BLUEPRINT.md), section 5.

## How it works

- **Races with controls.** Clients are released together by a barrier. Every concurrent trial is paired with a sequential control, a negative control and, where one exists, a positive control, so a clean result means something.
- **Two reference engines.** FalkorDB 6.0.4 serializes write queries per graph. Neo4j 5.26.2 runs at read committed by default. Between them they give a negative control, a positive control and a semantic oracle.
- **No models in the loop.** The LLM, embedder and reranker are replaced by deterministic stubs. No API keys are needed, and every expected value is known before the run.
- **Raw evidence.** Every run writes raw JSON. Every published number is regenerated from it.

## Targets

| Project | Blueprint | Pinned builds run | Results | Focus |
|---|---|---|---|---|
| getzep/graphiti | [Graphiti blueprint](targets/01-zep-graphiti/MASTER_BLUEPRINT.md) | v0.31.2, main `ebef986a`, #2119 head `b2b727e0`, and #1594 head for G5 | [M2](evidence/M2_GRAPHITI.md), [G5 addendum](evidence/M2_PR1594.md), [M5](evidence/M5_GRAPHITI.md), [G7 control](evidence/M5_GRAPHITI_B1.md) | Concurrent episode ingest, bitemporal expiry, startup indexing, persistence and deletion |
| topoteretes/cognee | [Cognee blueprint](targets/02-cognee/MASTER_BLUEPRINT.md) | v1.6.8 and v1.6.1 with FalkorDB adapter `ff1324ec` | [M3](evidence/M3_COGNEE.md), [M5](evidence/M5_COGNEE.md) | Multi-worker ingest and delete, LanceDB writers, Ladybug scale ceiling |
| ModernRelay/omnigraph | [Omnigraph blueprint](targets/03-omnigraph/MASTER_BLUEPRINT.md) | v0.15.0 `373834b4c1` and edge `b2dbaff` | [M4](evidence/M4_OMNIGRAPH.md), [M5](evidence/M5_OMNIGRAPH.md) | Branch and claim costs, traversal parity, and the writer epoch fence |

The O1 and O2b vendor-first notices follow [master blueprint §11.5](MASTER_BLUEPRINT.md#115-comparative-benchmarks). FalkorDB received the numbers on 2026-11-19 in [Discussion #3866](https://github.com/orgs/FalkorDB/discussions/3866). Omnigraph received them on 2026-11-19 in [a comment on #1397](https://github.com/ModernRelay/omnigraph/issues/1397#issuecomment-7010803143).

## Ground rules

- Only measured claims, each stated with its scope and an evidence tag.
- Never compete with an open pull request. Contribute the test that shows whether it works.
- Every outward message is drafted first, in the gitignored `drafts/` folder, and a person sends it.
- The clean-room boundary below always applies.

## Clean-room boundary

This repository is built only from public inputs: public source at pinned commits, public documentation, public issues and pull requests, and workloads and synthetic data written here.

It contains no confidential material of any third party. That rules out client query shapes, schemas, data, results, contract terms, and anything received under a non-disclosure agreement. Client-specific work, if there is any, runs in separate private checkouts and is never copied here. Details are in [MASTER_BLUEPRINT.md](MASTER_BLUEPRINT.md), section 11.7.

## Lineage

Witnessmark generalizes the audit invariants of [GNOMON](https://github.com/suryaprasanthcse/gnomon), a multi-agent kernel built on FalkorDB. It reuses GNOMON's lease checks, its no-overlap rule for bitemporal facts, and its method for weighing what branch copies cost. GNOMON is not a dependency.

## AI assistance

These blueprints were drafted with AI assistance (Anthropic's Claude) and reviewed by the maintainer. The maintainer runs every measurement and approves every outward message.

## License

Apache-2.0. See [LICENSE](LICENSE).
