# Witnessmark

Witnessmark checks seven concurrency and temporal invariants, I1 to I7, on graph databases and agent-memory layers. Every verdict comes with a witness: the raw, replayable record of the operations that produced it.

> **Status: milestone M2.**
> - M1 calibrated the core runner and the two baseline adapters against FalkorDB 6.0.4 and Neo4j 5.26.2.
> - M2 adds the memory-layer runner and the Graphiti adapter. Results: [evidence/M2_GRAPHITI.md](evidence/M2_GRAPHITI.md), and the Graphiti blueprint's §11.
> - The Cognee and Omnigraph adapters come next.
>
> The blueprints below are the contract the code is built against.

## Quick start

You need Python 3.10 or newer, and Docker. Nothing needs installing: the core uses only the standard library.

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
python wm.py calibrate --write evidence/M1_CALIBRATION.md
```

```bash
docker compose -f baselines/docker-compose.yml down
```

`calibrate` runs the control matrix (master blueprint, section 7.6) and writes raw evidence under `evidence/`. `python wm.py report --calibration` rebuilds the report from that evidence alone. The committed M1 calibration is [evidence/M1_CALIBRATION.md](evidence/M1_CALIBRATION.md).

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

## Targets (planned)

| # | Project | Blueprint | Focus |
|---|---|---|---|
| 01 | getzep/graphiti, v0.31.x | [targets/01-zep-graphiti](targets/01-zep-graphiti/MASTER_BLUEPRINT.md) | Concurrent `add_episode` ingest, bitemporal `expired_at`, FalkorDB and Neo4j parity |
| 02 | topoteretes/cognee, v1.6.x | [targets/02-cognee](targets/02-cognee/MASTER_BLUEPRINT.md) | Multi-worker add, cognify and delete; LanceDB writers; Ladybug scale ceiling |
| 03 | ModernRelay/omnigraph | [targets/03-omnigraph](targets/03-omnigraph/MASTER_BLUEPRINT.md) | Branch cost against `GRAPH.COPY`, 50-agent claims, the writer epoch fence |

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
