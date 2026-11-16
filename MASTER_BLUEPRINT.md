# Witnessmark: master blueprint

| | |
|---|---|
| Status | Specification v0.1, 2026-11-13. No code exists yet. |
| Scope | The engine-neutral core, the baselines, the evidence format and the contribution rules. Each target has its own blueprint under `targets/`. |
| Change rule | Code follows this document. A change of behaviour changes this document first, in the same commit or an earlier one. |

**Contents.** 0 Name and lineage · 1 Purpose and non-goals · 2 Principles · 3 System architecture · 4 Adapter contract · 5 The invariants, formally · 6 The barrier-synchronised runner · 7 Baseline and oracle contracts · 8 Deterministic model stubs · 9 Evidence: the raw JSON schema · 10 Reporting rules · 11 Contribution and outreach rules · 12 Build sequence · 13 Open questions · Appendix A Glossary

---

## 0. Name and lineage

**Witnessmark.** In consistency checking, a *witness* is the concrete history that proves a violation. In clock repair and machining, a *witness mark* is the small reference mark that records how parts really sat. The harness makes one promise, and the name carries it: no verdict without a witness, and every witness is kept as raw, replayable evidence.

**Lineage.** Witnessmark generalises the audit invariants of [GNOMON](https://github.com/suryaprasanthcse/gnomon), a multi-agent kernel that runs on FalkorDB. It takes four things from there:

- the lease checks;
- the no-overlap rule for bitemporal facts (audit K5b);
- the optimistic view check;
- the copy-weight method for branch costs (hazard S28).

GNOMON's code is not a dependency.

**Name check (2026-11-13).** No package by this name exists on PyPI or crates.io. One unrelated GitHub account uses the word; no repository has the name.

## 1. Purpose and non-goals

**Purpose.** Find out, with minimal reproducible evidence, whether a graph store or an agent-memory layer keeps seven invariants under concurrency, time and snapshots. Then give its maintainers a runnable test rather than an opinion.

The questions it answers:

| | Question |
|---|---|
| I1 | When N agents race for one task, how many win? |
| I2 | Does every acknowledged write survive? |
| I3 | When does a write become visible, and to whom? |
| I4 | Do two engines, or one engine in two index states, give the same answer? |
| I5 | Does deleted data stay deleted, and does a delete take only what it should? |
| I6 | Is a branch or copy one point in time, and what does it cost the rest of the server? |
| I7 | Are valid time and transaction time kept apart? |

**Non-goals.**

- **No leaderboard.** Timings appear only as cost curves beside a correctness result or a documented claim.
- **No replacement.** It is not a general Cypher fuzzer, and it does not replace Jepsen-style checkers or a project's own deterministic simulation. It adds cross-engine baselines and real-process faults.
- **No LLM quality evaluation.** Models are replaced by stubs (section 8).
- **No private material of any kind** (section 11.7).

## 2. Principles

| | Principle | In practice |
|---|---|---|
| P1 | Evidence first | Every claim carries a tag (section 9.4). Every number comes from raw JSON in `evidence/`. |
| P2 | Controls before findings | A concurrent result counts only next to a passing sequential control and a passing negative control. Where a positive control exists, it must pass too (section 6.2). |
| P3 | Test what the project promises | Each check names its expectation basis: the project's docs, a standard, a baseline or an open issue. Behaviour outside a documented support boundary is reported as such, not as a defect. |
| P4 | Determinism | Images are pinned by digest and target commits are pinned. Randomness is seeded. Models are stubbed. |
| P5 | Minimal repro | Every FAIL reduces to one file. That file uses the standard library plus the target's own package, includes a sequential control, and prints expected values next to observed ones. |
| P6 | Engine-neutral core | The core uses only the Python standard library. Target adapters may import the target's own client packages, and nothing else. |
| P7 | Non-competing contribution | Add the test that shows a fix works. Never race someone else's fix (section 11.2). |
| P8 | Draft first | Nothing leaves this repository until a person has read the exact text and sends it (section 11.1). |

## 3. System architecture

### 3.1 Components

| Component | Responsibility | Lives in |
|---|---|---|
| Runner | Barrier-synchronised trials, controls, validity gates (section 6) | `core/` |
| History recorder | One record per operation, with monotonic and wall-clock times | `core/` |
| Checkers | One per invariant; pure functions of the history and the final state | `core/` |
| Oracle comparator | Normalises and compares results across engines (section 7) | `core/` |
| Stubs | Deterministic LLM, embedder and reranker (section 8) | `core/` |
| Fault injector | Fault actions on the harness's own test containers: pause, resume, stop, restart (section 3.4); recorded under the schema name `nemesis` | `core/` |
| Evidence writer | Writes `run.json`, `history.jsonl` and state dumps (section 9) | `core/` |
| Reporter | Builds every table from evidence alone (section 10) | `core/` |
| Baseline adapters | FalkorDB 6.0.4 and Neo4j 5.26.2 (section 7) | `core/` |
| Target adapters | One per target; implements section 4 | `targets/<nn-name>/` |
| Scenarios and fixtures | Workloads, stub fixtures, expected final states | `targets/<nn-name>/` |

### 3.2 Data flow

```text
 scenario + fixtures ──► runner ──► N clients ──► adapter ──► system under test
                          │   ▲                                    │
                  faults  │   │ barrier                  final-state read
                          ▼   │                                    ▼
                    history.jsonl                           state/<k>.json
                          │                                        │
                          └─────────────► checkers ◄───────────────┘
                                             │
                                 run.json (verdicts) ──► reporter ──► tables
```

### 3.3 Layout

```text
gnomon-b2b-harness/          repository root; the project is Witnessmark
├── MASTER_BLUEPRINT.md      this document
├── README.md
├── LICENSE                  Apache-2.0
├── wm.py                    entry point: python wm.py <command>; nothing to install
├── baselines/
│   └── docker-compose.yml   FalkorDB 6.0.4 and Neo4j 5.26.2, pinned by digest
├── core/
│   ├── witnessmark/         the engine-neutral package (standard library only)
│   └── tests/               unit tests: python wm.py selftest
├── targets/
│   ├── 01-zep-graphiti/     blueprint; witnessmark_graphiti/ (adapter, stubs, fixtures,
│   │                        scenarios); wm_graphiti.py; requirements/ (frozen builds)
│   ├── 02-cognee/
│   └── 03-omnigraph/
├── evidence/                committed raw evidence of published runs
├── drafts/                  outreach drafts; gitignored, never committed
└── .state/                  live stores, scratch, and one venv per target build; gitignored
```

A target's adapter imports the target's own package, so it runs in that build's venv (for example `.state/venvs/graphiti-v0.31.2`). The core it imports still uses only the standard library.

### 3.4 Execution modes and faults

| Mode | Clients are | Use when |
|---|---|---|
| `thread` | threads in one process, one connection each | the system under test (SUT) is a server reached over the network |
| `asyncio` | coroutines on one event loop | the target library is async, and the question is in-process concurrency |
| `queue` | coroutines on one event loop, with one FIFO per group | the question is whether a per-group queue, such as Graphiti's MCP server keeps, removes the race |
| `process` | OS processes (spawn start method), each building its own client and library instance and working through its share in order | per-process locks or queues are part of the question |
| `container` | clients or servers in separate containers | pausing, stopping and failing over test containers |

**Which milestone adds each mode.**

- M1: `thread`.
- M2 (Graphiti): `asyncio`, `queue` and `process`.
- M5 (maintainer decision, 2026-11-16): Run the O2 claim races and O3 merge
  races in `thread` mode on the Windows host, using the existing runner for
  concurrent HTTP requests to Omnigraph. `container` mode was not built.
  M4's O1, O4 and O5 ran without a client race barrier
  [code: `core/witnessmark/runner.py`,
  `core/witnessmark/memory.py` and
  `targets/03-omnigraph/witnessmark_omnigraph/part2.py` @ `69d0cd3`].

**Invocation time.** In every mode, an operation's invocation is stamped when the client calls. A request waiting in a queue is already in flight.

Fault-injection actions are recorded in the history as operations whose client is `nemesis`, the schema's name for the fault injector. The schema values below are kept as they are, so recorded evidence stays readable:

| Action | Mechanism | Notes |
|---|---|---|
| `pause` / `resume` | `docker pause` / `docker unpause` | Docker suspends the container's processes (the cgroup freezer); a paused process cannot run, observe time or react. |
| `kill` | immediate stop of the test container (SIGKILL) | |
| `stop` / `start` | graceful stop, then start | |
| `restart` | restart of the same container | |

Network partitions and clock skew are out of scope for v0.1.

**Host.** Windows 11 with Docker Desktop, which runs a Linux VM. Every run records the VM's CPU and memory limits.

## 4. Adapter contract

Adapters translate the core's operations into a target's API. They contain no checking logic.

### 4.1 Engine adapters (graph databases)

| Operation | Semantics | Returns | Used by |
|---|---|---|---|
| `capabilities()` | Declares supported operations, consistency modes and documented claims (section 4.3) | capability record | all |
| `reset(fixture)` | Restores a known state | its digest | all |
| `write(shape, params)` | Runs one write statement or mutation | outcome, rows, error, commit token | I1, I2 |
| `read(shape, params, consistency)` | Runs one read | rows, commit token | I3, I4 |
| `snapshot(name)`, `drop_snapshot(name)` | Branch, fork or copy | handle, cost counters | I6 |
| `as_of(point)` | Reads at a valid-time or transaction-time point, where supported | rows | I7 |
| `dump()` | Canonical full state, or a digest plus samples when large | state | all |
| `health()` | Liveness and readiness, for example index status | status record | gates |

### 4.2 Memory-layer adapters (agent-memory frameworks)

| Operation | Semantics | Returns | Used by |
|---|---|---|---|
| `capabilities()` | As above, plus the backend in use | capability record | all |
| `reset(group)` | Empties one group, dataset or namespace | digest | all |
| `ingest(item, group)` | The target's ingest path, for example `add_episode`, or `add` then `cognify` | acknowledgement, item id | I1, I2, I7 |
| `delete(item, group)` | The target's delete path | acknowledgement | I5 |
| `search(query, group)` | The target's retrieval path | ranked results | I3, I4 |
| `dump(group)` | Canonical entities, facts with their temporal fields, and provenance | state | all |
| `quiesce()` | Waits until background work is done, such as queues and index builds | status | gates |
| `drain_stub_calls()` | Hands over the stub ledger since the last call (section 8) | call records | evidence |
| `release()` | Lets go of anything worker processes need, such as an embedded store's exclusive file lock. The runner calls it before every `process`-mode trial, after reset and setup; the next call that needs the store opens it again. Added in M3 for Cognee's Ladybug store. | – | `process` mode |

The contract is implemented as `MemoryTarget` in `core/witnessmark/memory.py`, together with the three run shapes:

- races, with a sequential control;
- known-answer case suites;
- visibility runs.

Case suites and races both declare a support level, basis and reference (section 5.8). Before M3 a case suite always reported `none` / `issue`; that remains the default.

### 4.3 Capabilities and claims

Every adapter declares what the SUT promises, with a source for each promise. Examples: "a single statement is atomic" [docs, link]; "reads are snapshot-isolated" [docs]; "ingestion is designed for high concurrency" [docs].

Checkers use these declarations to set each verdict's expectation basis (section 5.8). A check that no declaration and no standard covers reports OBSERVED, not FAIL.

## 5. The invariants, formally

### 5.0 Notation

**History.** A run has trials k = 1..T. In trial k, clients c ∈ C issue operations, and the set of those operations is the history Hₖ.

**Operations.** An operation o has these fields:

| Field | Meaning |
|---|---|
| `o.c` | the client that issued it |
| `o.kind`, `o.input` | what it was and its parameters |
| `o.inv`, `o.ret` | invocation and return time, on a monotonic clock |
| `o.out` | outcome: `ok`, `fail` or `unknown` |
| `o.res` | the result |

The three outcomes:

- `ok`: the SUT acknowledged success.
- `fail`: the SUT definitely did not apply the operation, either through a typed refusal or because a guard evaluated false.
- `unknown`: a timeout or a lost connection. The operation may or may not have taken effect.

**Orders and states.**

| Symbol | Meaning |
|---|---|
| o₁ ≺ o₂ | Real-time order: o₁.ret < o₂.inv. |
| <꜀ | Commit order, the SUT's own order where it exposes one (sequence numbers, commit ids); otherwise undefined. |
| Sₖ | The final state: read after `quiesce()`, with the strongest read the SUT offers. |
| Ack(H) | {o ∈ H : o.out = ok} |

### 5.1 I1: Single winner

**Form A, claims.** For each resource r, let:

- W_r = {o ∈ Ack(Hₖ) : o.kind = claim(r) ∧ o.res.won = 1}, the acknowledged winners;
- U_r = the claims of r whose outcome is `unknown`.

I1A holds when all four of these are true:

- (a) |W_r| ≤ 1.
- (b) If |W_r| = 1, Sₖ.holder(r) is that claimant.
- (c) If |W_r| = 0, Sₖ.holder(r) is either nobody or a member of U_r.
- (d) No two lease records on r overlap. For l₁ ≠ l₂, it is not the case that (l₁.from < l₂.until ∧ l₂.from < l₁.until). Commit order is used where available.

**Form B, unique creation.** Take any canonical key κ, for example an entity's normalised name within a group. In Sₖ, the number of live records with key κ is exactly 1 if an acknowledged operation introduced κ, and 0 otherwise.

**What a violation looks like.** Several clients are told they won, or one key has duplicate records.

### 5.2 I2: No lost acknowledged writes

**Single writes.** Take any w ∈ Ack(Hₖ) that sets field f of entity e to v, or that adds a fact φ. Then:

- Sₖ[e, f] = v, unless some w′ ∈ Ack(Hₖ) on (e, f) comes after w in commit order. Where the SUT exposes no commit order, real-time order is used instead.
- φ ∈ Sₖ, unless an acknowledged delete removed it afterwards.

**Disjoint writes and counters.** Writes to disjoint fields, or of disjoint facts, must all survive. After n acknowledged increments, the final value lies in [n, n + |unknown|].

**Memory-layer form.** Every fact the stub scripted for an acknowledged ingest is present in Sₖ, either exactly once or merged with an identical fact in the way the target documents.

**Deletes.** A delete that removes something another acknowledged operation still references violates I2 and is reported with `cause = delete`.

### 5.3 I3: Read your writes, and the visibility lag

- **Session form.** Take any w ∈ Ack issued by client c, and any later read r by the same client (w ≺ r). Then r observes w, or a later version of the same key.
- **Token form.** Applies only where the SUT offers causal tokens or bookmarks. The session rule then extends to reads by any client that carries w's token.
- **Measured quantity.** The visibility lag λ(w) is the least t such that a read invoked at w.ret + t observes w. It is reported as p50, p95, p99 and max for each read path.
- **Memory-layer form.** A search or recall issued after an ingest returns finds the ingested fact.

### 5.4 I4: Equivalence

**Definition.** For a query q over logical state Σ, I4 requires N(E(q, Σ, x)) = N(O(q, Σ)). Here:

- E is the engine under test, run in context x;
- O is the oracle (section 7);
- N normalises results: rows become a multiset, order counts only when q orders, and numbers and timestamps are canonicalised.

**Contexts x.**

- steady state;
- an index under construction;
- an index rebuilding after a drop;
- after a restart;
- a cold cache;
- a follower or replica read, where the SUT offers one.

**Classification.** Each pair (q, x) is classified as one of:

- identical;
- rejected (a typed error);
- silently different (no error, but different rows);
- crashed.

**Memory-layer form.** The same scripted ingest on two backends yields equal canonical graphs, ignoring ids, and equal answers to a fixed search suite.

### 5.5 I5: Deletion permanence

- **Definition.** Take any acknowledged delete d of item x. No read r with d ≺ r returns x, unless an acknowledged create of x came after d.
- **Derived form.** Everything derived only from x is gone: chunks, vectors, entities, and edges whose last provenance was x. Derived artefacts still referenced by live items remain.
- **Overreach.** A delete must not remove anything that another live or in-flight acknowledged item references. Such a removal is reported under I2, with `cause = delete`.

### 5.6 I6: Snapshot integrity and cost

**I6a, atomic snapshot.** A branch, fork or copy B taken from A while commits are running must equal A's state at a single commit point.

- Checked with a ledger: every commit appends an entry carrying the next counter value.
- B must hold a gapless prefix of the ledger.

**I6b, isolation.** Until an explicit merge:

- writes to B are invisible in A;
- writes to A after B was created are invisible in B.

**I6c, cost profile (measured).** Five quantities are measured:

| Symbol | Quantity |
|---|---|
| t(n) | creation time |
| s(n) | stall: the longest gap an unrelated reader sees during creation |
| b(n) | bytes written |
| m(n) | memory delta |
| w(n) | copy weight: t_snapshot(n) / t_cycle(n), for a create, apply, score, discard cycle |

They are measured across graph sizes n and counts of live sibling branches. I6c is a curve, not a verdict, unless the SUT documents a bound.

### 5.7 I7: Bitemporal integrity

**Model.** Each version f of a fact has:

- a valid interval [f.vf, f.vt);
- a transaction interval [f.ts, f.te). f.te = ∞ means the system currently believes f.

A functional key k is a subject–predicate pair that holds one value at a time. It groups the versions of one fact.

| Rule | Name | Statement |
|---|---|---|
| I7a | No overlapping current versions | For all f₁ ≠ f₂ with key k, it is not the case that (f₁.te = ∞ ∧ f₂.te = ∞ ∧ f₁.vf < f₂.vt ∧ f₂.vf < f₁.vt). This is GNOMON's K5b. |
| I7b | Transaction time ends only for a recorded reason | If f.te ≠ ∞, a superseding version or a retraction was committed at f.te. A known end of validity, past or future, does not by itself end transaction time. |
| I7c | Later evidence does not extend a finite interval | A later contradicting fact may move f.vt to a point inside [f.vf, f.vt). It does not move f.vt later, unless the SUT documents that it does. |
| I7d | As-of reproducibility | The valid-time slice of current beliefs at time T, written AT_TIME(T), and the transaction-time slice at point S, written AT_TX(S), equal the states the history implies. |

I7b and I7c follow the standard bitemporal model. Some targets define their own semantics, for example Graphiti's `expired_at`. For those, the harness reports the verdict under both readings and takes no side. Each target blueprint says which applies.

### 5.8 Verdicts

| Verdict | Meaning |
|---|---|
| PASS | The invariant held in every valid trial. |
| FAIL | It was violated in at least one valid trial. Reported as k of T, with witnesses. |
| INVALID | A control or a validity gate failed. Nothing may be claimed. |
| INCONCLUSIVE | The controls passed, but contention could not be shown (section 6.2). A clean result is not evidence of safety. |
| KNOWN_DEVIATION | The behaviour matches an entry in the known-deviation registry (section 7.5). |
| BOUNDARY | The behaviour lies outside the SUT's documented support boundary. Reported, not a defect. |
| OBSERVED | No promise and no standard applies. The behaviour is recorded without a verdict. |
| NOT_APPLICABLE | The SUT does not offer the capability. |

**Target runs.** A target run records the support level of its configuration, and that level decides what a violation is called:

| Support level | Source | A violation is |
|---|---|---|
| supported | the documentation promises the configuration works | FAIL |
| boundary | the documentation puts the configuration outside the contract, for example "add episodes sequentially" | BOUNDARY |
| none | no promise applies | OBSERVED |

A clean race without contention evidence is INCONCLUSIVE.

Every verdict also carries an expectation basis and a reference for it. The basis is one of:

- `documented`
- `standard`
- `baseline`
- `issue`: what an open upstream issue says should happen
- `inferred`

## 6. The barrier-synchronised runner

### 6.1 Trial lifecycle

1. **Reset.** Restore the precondition state and check its digest.
2. **Warm.** Every client opens its own connection or library instance and makes one no-op call, so that setup never falls inside the race.
3. **Arm.** Every client renders its payload: query text and parameters.
4. **Release.** Clients wait on a barrier of N + 1 parties; the coordinator is the last party. The barrier depends on the mode:

   | Mode | Barrier |
   |---|---|
   | `thread` | `threading.Barrier` |
   | `asyncio` | `asyncio.Barrier` |
   | `process` | `multiprocessing.Barrier` |
   | `container` | For the TCP start gun the coordinator accepts N connections, then writes one byte to each. The mode is unimplemented and outside M5 (section 3.4). |

5. **Act.** Each client records `inv`, sends its operation, then records `ret`, the outcome, the result, any error and the commit token. Per-operation timeout τ_op; per-trial timeout τ_trial.
6. **Quiesce.** Call `quiesce()` and record how long it took.
7. **Observe.** Read the final state with the strongest read available, and record its digest.
8. **Check.** Run the checkers on (Hₖ, Sₖ).

The release spread Δ is max(o.inv) − min(o.inv), taken over each client's first operation. Δ is recorded for every trial.

Monotonic times are comparable only within one clock domain, such as the Windows host or the Docker VM. Ordering across domains uses wall-clock times, and every run records the measured offset between domains.

### 6.2 Controls

| Control | What runs | Must show | If it does not |
|---|---|---|---|
| Sequential (SC) | the same operations, one at a time, from the same reset | the scenario's expected answer, exactly | INVALID: the probe or the fixture is wrong |
| Negative (NC) | a baseline known to keep the invariant, for example FalkorDB 6.0.4 with the naive guarded claim | no violation in T trials | INVALID; any baseline finding is handled separately |
| Positive (PC) | a configuration documented to violate it, for example Neo4j 5.26.2 at read committed with the naive guarded claim | at least one violation in T trials | clean target results are INCONCLUSIVE |
| Overlap (OC) | in-library races with no positive control: at least two operations in flight at once, each counted from its client's invocation to its return; the stub-call log (section 8) shows the inner windows | two or more in flight in every valid trial | a clean result is INCONCLUSIVE |

A positive or overlap control shows that the runner can see a race before a clean result is reported. The positive control is probabilistic. Not observing it says something about contention, never about the baseline.

### 6.3 Validity gates

A trial is valid only if every one of these holds:

- The precondition digest matched.
  - By default the digest covers the scenario's full observed state after reset [code: `core/witnessmark/scenarios.py:42–44` and `core/witnessmark/runner.py:88` @ `9e755b6`].
  - A scenario may override `Scenario.precondition()` to leave out fields that change on every reset but carry no logical state, such as a commit id that each fixture publish advances. It must list the fields it leaves out in its target blueprint. The full observed state is still written to `state/<k>.json`.
  - Omnigraph's O2 and O3 races do this (the Omnigraph blueprint, O2 runner wiring).
- Δ ≤ δ.
  - **`thread` mode.** M1 calibrated δ = 40 ms on this host against FalkorDB and Neo4j with 50 clients. It used 1.5 × p99 rounded up over 240 race trials (p50 7.88 ms, p99 26.65 ms, max 32.53 ms) [measured: `evidence/M1_CALIBRATION.md`].
    **Omnigraph (M5).** Batch `m5-20261115T222957Z` ran O2a and O2c on
    both builds with 50 clients and no spread gate. Over its 80 valid
    trials (4 runs × 20) the release spread had p50 8.671 ms, p99 36.365 ms
    and max 36.365 ms, so δ = ⌈1.5 × 36.365⌉ = 55 ms
    [measured: `20261115T223017Z-22107db4`, `20261115T223104Z-bcff6931`,
    `20261115T223149Z-b1b52c9c`, `20261115T223237Z-3658b53d`;
    `evidence/M5_OMNIGRAPH_CALIBRATION.md`]. It is the Omnigraph race
    default, `OMNIGRAPH_THREAD_SPREAD_GATE_MS` beside
    `THREAD_SPREAD_GATE_MS` in `core/witnessmark/runner.py`; the M1 40 ms
    gate is unchanged. That batch's O2 runs are calibration only and are
    not O2 results (§12.1, Phase B).
  - **Other modes.** M2 recorded the spread without gating on it, in batch `m2-20261113T174128Z` [measured: `evidence/M2_GRAPHITI.md`]. In `process` mode the spread is taken over each worker's first operation. δ follows the same 1.5 × p99 rule. Since M3 the gates apply to memory races (`SPREAD_GATE_MS` in `core/witnessmark/memory.py`). A scenario that staggers its clients on purpose, a declared offset sweep, turns its own gate off and records the sweep. Since M3 a trial is also invalid when the stub could not answer one of its calls (section 8). The provisional 50 ms `container` gate is unused (section 3.4).

    | Mode | Trials | p50 | p99 | δ |
    |---|---|---|---|---|
    | `asyncio` | 120 | 6.08 ms | 61.27 ms | 92 ms. The library's own synchronous start-up runs coroutine by coroutine, which is why the spread is wide. |
    | `queue` | 40 | 0.86 ms | 1.65 ms | 3 ms |
    | `process` | 40 | 0.12 ms | 0.26 ms | 1 ms |
  - **`calibrate`** records Δ without gating on it, because its job is to set δ.
- The SUT was healthy before and after the trial (`health()`).
- At most 5% of operations had an unknown outcome.
- No client raised an unhandled exception.

Invalid trials stay in the evidence and are counted. They are never dropped silently.

### 6.4 Unknown outcomes

An operation with an unknown outcome may have committed, so checkers treat it as possibly applied. For I1:

- One acknowledged winner and u unknown claims: the trial passes only if the final holder is the winner.
- No acknowledged winner: the holder must be nobody or one of the unknown claimants.

Unknown outcomes are always reported.

### 6.5 Benchmark protocol (I6c and other cost curves)

- **Repetitions.** Three warm-up repetitions are discarded, then at least five are measured. Medians and interquartile ranges are reported.
- **Interleaving.** Configurations run interleaved (A, B, A, B, and so on) to spread drift.
- **Isolation.** Only one workload runs on the host at a time. The Docker VM's limits are recorded.
- **Sanity bands.** Where a baseline figure was published before, a re-measured value more than 50% away from it stops the run until the environment is explained.
- **Cost counters.** These come from the SUT (for example AOF bytes, or object-store request counts) or from a counting proxy. A proxy that perturbs timing runs in separate, matched repetitions. Omnigraph's RFC 0031 takes the same approach.

### 6.6 Defaults

| Parameter | Default |
|---|---|
| Clients per race (N) | 50 for claims, 20 for ingest, 2 to 8 worker processes |
| Trials per configuration (T) | 20 |
| τ_op / τ_trial | 60 s / 600 s |
| Seed | recorded in every run; fixed for published runs |
| Python | 3.10 or newer for the core (M1 ran on 3.14.7) |

## 7. Baseline and oracle contracts

### 7.1 Roles

| Role | FalkorDB 6.0.4 | Neo4j 5.26.2 |
|---|---|---|
| Negative control for single-statement races (I1, I2) | yes | lock-first shapes only |
| Positive control for single-statement races | no | naive guarded shapes |
| Semantic oracle for query results (I4) | second reference | primary reference |
| Snapshot-cost baseline (I6) | `GRAPH.COPY` | none |
| Backend beneath memory layers | Graphiti; Cognee through a community adapter | Graphiti, Cognee |

### 7.2 FalkorDB 6.0.4

**Image.** `falkordb/falkordb@sha256:bef8acb1d8ed9ff8d2ea251767e75c6c05cfa759f7c6bc7e1c122f27d0ea4d7f`, the digest GNOMON pins for 6.0.4 (graph module 60004). Every run records the module version the server reports.

**Data directory.** `/var/lib/falkordb/data` [ours] [code: Graphiti's MCP compose file]. Every run records the persistence settings: `appendonly`, `appendfsync` and `save`.

**Measured behaviour from GNOMON's hazard log.** These come from [GNOMON's hazard log](https://github.com/suryaprasanthcse/gnomon/blob/acffec2/.agent/FACTS.md) [ours]. Items S3 to S27 were measured on 6.0.2 and re-checked on 6.0.4; S28 was measured on 6.0.4.

| Item | Behaviour |
|---|---|
| S3, concurrency | Write queries to one graph are serialised. 50 concurrent compare-and-set queries gave exactly 1 winner. 16 threads × 20 read-modify-write increments gave exactly 320. The harness re-establishes this as a negative control in every run. |
| S4, atomicity | An error anywhere in a write query rolls the whole query back. |
| S6, S27, index readiness | `db.indexes()` reports `UNDER CONSTRUCTION` until the index is `OPERATIONAL`. Dropping one property's index rebuilds the label's remaining index, and lookups plan as label scans until it is operational again. |
| S28, snapshot cost | One run, `appendfsync always`. `GRAPH.COPY` stops the whole server while it runs. A copy took 165 ms at 32k nodes and 32k edges, 546 ms at 128k and 2,400 ms at 512k. At 512k each copy also used 334 MB and wrote 189 MB of AOF. Writes on a copy do not stall the live graph. |

The S28 figures are a sanity band, not a result. The harness re-measures them on its own host.

**Re-measured in M1** [measured: `evidence/M1_CALIBRATION.md`]. With 50 clients per trial, all five shapes in section 7.6 held in 20 of 20 trials:

- Both claim shapes had exactly one winner in every trial.
- Neither counter shape lost an increment. That includes `counter.via_with`, the shape on which Neo4j loses increments.
- No disjoint write was lost.

### 7.3 Neo4j 5.26.2

**Image.** `neo4j:5.26.2` (Community), the version Graphiti's root `docker-compose.yml` pins. The digest is recorded at first pull and pinned from then on.

**Isolation** ([docs: Operations Manual, Concurrent data access](https://neo4j.com/docs/operations-manual/5/database-internals/concurrent-data-access/)).

- Read committed is the default.
- Cypher takes a write lock before reading only when the right-hand side of a `SET` reads the property being written.
- A guard in `WHERE` takes no lock, and neither does a value carried through `WITH`.
- The documented workaround is to write a dummy property first, which takes the node's write lock, and remove it afterwards.

**How the harness uses this.**

- A naive guarded claim is a positive control: it may admit several winners.
- A lock-first claim is a negative control: it should admit exactly one.
- Neither outcome is a Neo4j defect.

**Measured in M1** [measured: `evidence/M1_CALIBRATION.md`]. 50 clients, 20 trials per shape:

| Shape | Violating trials | Per trial |
|---|---|---|
| `claim.state.naive` | 20 of 20 | 4 to 13 clients told they won (median 10.5) |
| `claim.lease.naive` | 20 of 20 | 2 to 13 winners (median 10); every winner left its own lease edge |
| `counter.via_with` | 20 of 20 | 40 to 49 of 50 increments lost (median 46) |
| `claim.state.lock_first`, `claim.lease.lock_first` | 0 of 20 | exactly 1 winner |
| `counter.direct`, `disjoint.set` | 0 of 20 | nothing lost |

**Semantic role.** Neo4j is the primary oracle for Cypher result semantics on static data.

**Index visibility.** Whether fulltext and vector indexes reflect a write once it commits is measured, not assumed.

### 7.4 When the baselines disagree

1. Check the known-deviation registry (section 7.5).
2. Read the openCypher specification, and its TCK scenario for the construct where one exists.
3. Break the tie on a current, calendar-versioned Neo4j release, and record it as a tie-break.
4. If it is still unclear, classify the shape AMBIGUOUS and leave it out of all verdicts.

### 7.5 Known-deviation registry (initial)

| ID | Engine | Behaviour | Source | Effect on checks |
|---|---|---|---|---|
| KD-F1 | FalkorDB 6.0.4 | A `WHERE` after `LIMIT` or `SKIP` in a `WITH` is pushed below the limit | [FalkorDB/FalkorDB#3694](https://github.com/FalkorDB/FalkorDB/issues/3694); fix proposed in [FalkorDB/FalkorDB#3699](https://github.com/FalkorDB/FalkorDB/pull/3699) | Such shapes are judged against Neo4j only |
| KD-F2 | FalkorDB 6.0.4 | `OPTIONAL MATCH … WHERE` after an aggregating `WITH` returns null | [FalkorDB/FalkorDB#3352](https://github.com/FalkorDB/FalkorDB/issues/3352) (GNOMON S25); fix proposed in [FalkorDB/FalkorDB#3521](https://github.com/FalkorDB/FalkorDB/pull/3521) | Same |
| KD-F3 | FalkorDB 6.0.4 | `GRAPH.COPY` stalls the whole server | GNOMON S28 | An I6 baseline fact, not a correctness deviation |
| KD-F4 | FalkorDB 6.0.4 | Dropping one index rebuilds the label's remaining index | GNOMON S27 | I4 runs during an index rebuild wait for `OPERATIONAL`, or record the plan change |
| KD-N1 | Neo4j 5.26.2 | At read committed, guards in `WHERE` and values carried through `WITH` take no lock | Neo4j Operations Manual; measured in M1 (section 7.3) | Naive shapes are positive controls |

New entries need a public source and a minimal repro.

### 7.6 The calibration matrix (M1)

`python wm.py calibrate` runs every configuration below. Each run is 50 clients × 20 trials, after a sequential control. The shapes are defined in `core/witnessmark/scenarios.py`; labels carry a `WM` prefix.

| Scenario | Shape | What each client sends | FalkorDB 6.0.4 | Neo4j 5.26.2 |
|---|---|---|---|---|
| `claim.state` | `naive` | `MATCH (t:WMTask {id: $task}) WHERE t.state = 'open' SET t.state = 'claimed', t.holder = $agent RETURN count(t) AS won` | negative | positive (KD-N1) |
| `claim.state` | `lock_first` | The same, after `SET t._wm_lock = true REMOVE t._wm_lock WITH t` | not run | negative |
| `claim.lease` | `naive` | `OPTIONAL MATCH` the task's `WM_HOLDS` edges, `count` them, and `CREATE` one only if there are none: the shape of GNOMON's ClaimTask guard | negative | positive (KD-N1) |
| `claim.lease` | `lock_first` | The same, after the dummy-property lock on the task | not run | negative |
| `counter` | `direct` | `SET c.v = c.v + 1` | negative | negative (the documented automatic lock) |
| `counter` | `via_with` | `WITH c, c.v AS p SET c.v = p + 1` | negative | positive (KD-N1) |
| `disjoint` | `set` | Client i sets its own property `d.pNN` on one shared node | negative | negative |

**Bases.**

- **FalkorDB:** GNOMON S3 [ours].
- **Neo4j:** the Operations Manual, with one exception. `disjoint.set` is [inference]: every `SET` takes the node's write lock, and no client writes another client's property.

## 8. Deterministic model stubs

Agent-memory layers call an LLM, an embedder and often a reranker. Witnessmark replaces all three.

**Fixture-driven.**

- Each ingested item carries a stable id tag in its text, such as `[wm:E017]`.
- A fixture maps (step, item id) to the structured answer for that step.
- A prompt without a known tag fails loudly.

**Ideal-model policy.** For deduplication and contradiction steps, the stub answers as a perfect model would, given exactly what the prompt shows:

- It matches the candidate whose canonical key equals the fixture's key.
- If no candidate matches, it declares the item new.

The stub never makes a semantic mistake. Any duplicate or temporal error therefore comes from the pipeline, not the model.

**Embeddings.** Vectors are deterministic: equal canonical text gives equal vectors. Fixtures may pin vectors to control similarity. The dimension matches the target's configuration.

**Reranker.** Scores come from fixtures; ties are broken by id.

**Transport.** One of two forms:

- in-process, implementing the target's client interface;
- an OpenAI-compatible HTTP endpoint, serving chat completions with JSON output plus embeddings, and shared by all worker processes. Built in M3 as `core/witnessmark/stub_server.py`. It uses the standard library only and binds to loopback only. It validates every answer against the JSON schema the request carries, answers an unknown prompt with HTTP 400, and keeps the ledger in the process that serves it. The target supplies the fixture handler.

**Logged.** Every stub call becomes a history operation of kind `llm`, `embed` or `rerank`, carrying digests of the request and the response. The same log serves as the overlap control for in-library races (section 6.2).

**Validated.** A scenario's sequential control must reproduce its expected graph exactly before any concurrent trial runs.

## 9. Evidence: the raw JSON schema

### 9.1 Layout

```text
evidence/<target>/<scenario>/<run_id>/
  run.json        manifest, pins, environment, controls, trial summaries, verdicts
  history.jsonl   one JSON object per operation (clients, nemesis, stubs)
  state/<k>.json  canonical final state of trial k (a digest plus samples above 5 MB)
  REPRO.md        the command that regenerates this run
```

- Target runs add a level for the build and backend: `evidence/<target>/<build>.<backend>/<scenario>.<mode>/<run_id>/`. An example is `evidence/graphiti/v0.31.2.falkordb/g1.same_group.asyncio/`. Their history also holds the stub ledger, as operations with phase `stub`.
- `run_id` is `<UTC yyyymmddThhmmssZ>-<first 8 hex of the manifest's SHA-256>`.
- Evidence of published runs is committed.
- Database files and large dumps stay under `.state/`, which is gitignored.

### 9.2 `run.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:witnessmark:schema:run:0.1",
  "title": "Witnessmark run manifest",
  "type": "object",
  "required": ["schema_version", "run_id", "harness", "target", "components", "host",
               "scenario", "seed", "started_at", "finished_at", "controls", "trials", "verdicts"],
  "properties": {
    "schema_version": { "const": "0.1" },
    "run_id": { "type": "string", "pattern": "^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{8}$" },
    "batch": { "type": ["string", "null"], "description": "groups the runs of one calibration or sweep" },
    "expectation": {
      "type": "object",
      "description": "the configuration's control role and its basis (section 7.6)",
      "properties": {
        "role": { "enum": ["negative", "positive"] },
        "basis": { "enum": ["documented", "standard", "baseline", "issue", "inferred"] },
        "basis_ref": { "type": "string" },
        "known_deviation": { "type": ["string", "null"] }
      }
    },
    "harness": {
      "type": "object",
      "required": ["version", "commit", "dirty"],
      "properties": {
        "version": { "type": "string" },
        "commit": { "type": "string", "pattern": "^[0-9a-f]{40}$" },
        "dirty": { "type": "boolean", "description": "a dirty tree makes the run unpublishable" }
      }
    },
    "target": {
      "type": "object",
      "required": ["name", "repo", "ref"],
      "anyOf": [ { "required": ["commit"] }, { "required": ["digest"] } ],
      "description": "a target built from source is identified by its commit; one run from an image, by its digest",
      "properties": {
        "name": { "type": "string" },
        "repo": { "type": "string", "description": "owner/name" },
        "ref": { "type": "string", "description": "tag, branch, refs/pull/N/head, or the version an image reports" },
        "commit": { "type": "string", "pattern": "^[0-9a-f]{40}$" },
        "digest": { "type": "string", "pattern": "^sha256:[0-9a-f]{64}$" },
        "package_version": { "type": "string" }
      }
    },
    "components": {
      "type": "array",
      "description": "every engine, store, stub and proxy in the run",
      "items": {
        "type": "object",
        "required": ["role", "name", "version"],
        "properties": {
          "role": { "enum": ["sut", "baseline", "store", "stub", "proxy"] },
          "name": { "type": "string" },
          "version": { "type": "string" },
          "image": { "type": "string" },
          "digest": { "type": "string", "pattern": "^sha256:[0-9a-f]{64}$" },
          "config": { "type": "object", "description": "settings that change behaviour, e.g. appendfsync" }
        }
      }
    },
    "host": {
      "type": "object",
      "required": ["os", "cpu", "cores", "memory_gb"],
      "properties": {
        "os": { "type": "string" },
        "cpu": { "type": "string" },
        "cores": { "type": "integer" },
        "memory_gb": { "type": "number" },
        "python": { "type": "string" },
        "docker": { "type": "string" },
        "vm_cpus": { "type": "integer" },
        "vm_memory_gb": { "type": "number" },
        "clock_offsets_ms": { "type": "object", "description": "domain name to offset from the coordinator" }
      }
    },
    "scenario": {
      "type": "object",
      "required": ["id", "invariants", "mode", "clients", "trials", "params"],
      "properties": {
        "id": { "type": "string" },
        "invariants": { "type": "array", "items": { "type": "string", "pattern": "^I[1-7][A-Da-d]?$" } },
        "mode": { "enum": ["thread", "asyncio", "process", "container"] },
        "clients": { "type": "integer", "minimum": 1 },
        "trials": { "type": "integer", "minimum": 1 },
        "params": { "type": "object" },
        "declared_sweep": { "type": "array", "items": { "type": "object" },
                            "description": "every configuration of a sweep, declared before the run" }
      }
    },
    "seed": { "type": "integer" },
    "started_at": { "type": "string", "format": "date-time" },
    "finished_at": { "type": "string", "format": "date-time" },
    "controls": { "type": "array", "items": { "$ref": "#/$defs/control" } },
    "trials": { "type": "array", "items": { "$ref": "#/$defs/trial" } },
    "verdicts": { "type": "array", "items": { "$ref": "#/$defs/verdict" } }
  },
  "$defs": {
    "control": {
      "type": "object",
      "required": ["kind", "configuration", "expected", "observed", "met"],
      "properties": {
        "kind": { "enum": ["sequential", "negative", "positive", "overlap"] },
        "configuration": { "type": "string" },
        "expected": { "type": "string" },
        "observed": { "type": "string" },
        "met": { "type": "boolean" },
        "run_ref": { "type": "string", "description": "run_id, when the control ran as its own run" }
      }
    },
    "trial": {
      "type": "object",
      "required": ["k", "valid", "precondition_digest", "release_spread_ms", "outcomes", "final_state_digest"],
      "properties": {
        "k": { "type": "integer", "minimum": 1 },
        "valid": { "type": "boolean" },
        "invalid_reason": { "type": "string" },
        "precondition_digest": { "type": "string" },
        "release_spread_ms": { "type": "number" },
        "outcomes": {
          "type": "object",
          "required": ["ok", "fail", "unknown"],
          "properties": {
            "ok": { "type": "integer" }, "fail": { "type": "integer" }, "unknown": { "type": "integer" }
          }
        },
        "quiesce_ms": { "type": "number" },
        "final_state_digest": { "type": "string" },
        "state_file": { "type": "string" },
        "checks": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["invariant", "held"],
            "properties": {
              "invariant": { "type": "string" },
              "held": { "type": "boolean" },
              "magnitude": { "type": "number", "description": "e.g. number of winners, duplicates, lost writes" },
              "witnesses": { "type": "array", "items": { "type": "string" }, "description": "op_ids" }
            }
          }
        }
      }
    },
    "verdict": {
      "type": "object",
      "required": ["invariant", "status", "trials_violating", "trials_valid", "basis", "basis_ref"],
      "properties": {
        "invariant": { "type": "string" },
        "status": { "enum": ["PASS", "FAIL", "INVALID", "INCONCLUSIVE", "KNOWN_DEVIATION",
                             "BOUNDARY", "OBSERVED", "NOT_APPLICABLE"] },
        "trials_violating": { "type": "integer" },
        "trials_valid": { "type": "integer" },
        "magnitude": {
          "type": "object",
          "properties": {
            "min": { "type": "number" }, "median": { "type": "number" },
            "max": { "type": "number" }, "unit": { "type": "string" }
          }
        },
        "basis": { "enum": ["documented", "standard", "baseline", "issue", "inferred"] },
        "basis_ref": { "type": "string", "description": "link or path@commit" },
        "witnesses": { "type": "array", "items": { "type": "string" }, "description": "op_ids in history.jsonl" },
        "note": { "type": "string" }
      }
    }
  }
}
```

**Measurement runs (amended 2026-11-16, maintainer ruling at M5 Phase E).** A measurement run, meaning a cost curve, a latency curve, or a visibility, failover or parity measurement, computes no §5.8 verdict. Its manifest records `controls` and `verdicts` as null, and its checks live in the run's own fields, named per scenario. The other `required` fields above stand. As written, these manifests leave both keys out, which every reader takes as null. O1's curve and O6 keep their named checks in an object under `controls` (`i6` and `falkordb`; `sequential`), never in the control array above. The kinds this covers, at the commit that wrote their evidence:

| Scenario id (mode) | Run kind | Where its checks live | Written by |
|---|---|---|---|
| `o1.branch_cost` (`curve`) | O1 branch-cost curve, with the FalkorDB `GRAPH.COPY` curve | `summary`, `copy_weight`, `controls.i6`, `controls.falkordb` | [code: `targets/03-omnigraph/witnessmark_omnigraph/part2.py:651,731,734` @ `fb97518`] |
| `o1.i6_controls` (`controls`) | O1's I6a and I6b controls on their own (M4 only) | `i6` | [code: `targets/03-omnigraph/witnessmark_omnigraph/part2.py:411,422` @ `8bc5fd3`] |
| `o2b.disjoint_claims` (`sweep`) | O2b attempt curve, Omnigraph | `summary` and per-trial `attempts`, `wasted_attempts`, `holders_ok` | [code: `targets/03-omnigraph/witnessmark_omnigraph/costcurve.py:489,529` @ `4212c99`] |
| `o2b.claim_state_disjoint.sweep` (`sweep`) | O2b attempt curve, FalkorDB side | the same fields | [code: `targets/03-omnigraph/witnessmark_omnigraph/costcurve.py:637,640` @ `4212c99`] |
| `o4.failover_acceptance` (`matrix`) | O4 failover matrix (M4 only) | per-cell `trials` | [code: `targets/03-omnigraph/witnessmark_omnigraph/part2.py:805` @ `8bc5fd3`] |
| `o4.clean_stop_transfer` (`transfer`) | O4 clean-stop local transfer | per-trial `trials` | [code: `targets/03-omnigraph/witnessmark_omnigraph/part2.py:976` @ `6a15b9c`] |
| `o5.cross_process_ryw` (`visibility`) | O5 cross-process visibility | per-trial `trials` | [code: `targets/03-omnigraph/witnessmark_omnigraph/part2.py:1140,1183` @ `6a15b9c`] |
| `o6.traversal_parity` (`cases`) | O6 traversal parity | `controls.sequential`, `trials` | [code: `targets/03-omnigraph/witnessmark_omnigraph/part2.py:580,613` @ `6a15b9c`] |

- No validator reads `run.json`: `validate_history` checks `history.jsonl` only [code: `core/witnessmark/history.py:108` @ `f25653d`]. The rule therefore lives in the Omnigraph manifest writer. `check_manifest_fields` accepts null `controls` and `verdicts` only for the scenario ids above and refuses them for every other run (`targets/03-omnigraph/witnessmark_omnigraph/capture.py`, `core/tests/test_m5_phase_e.py`). The same test checks every committed manifest against the rule.
- These manifests also carry `schema_version` 1, the integer, where the schema above says `"0.1"`. They are kept as written, like all evidence. Settled by the maintainer on 2026-11-16: manifests written before `4153b02` carry the integer 1; the writer emits `"0.1"` from `4153b02` (unit test in `core/tests/test_m5_phase_e.py`).
- No report changed: every committed report still regenerates byte for byte.

### 9.3 `history.jsonl`, one object per line

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "urn:witnessmark:schema:op:0.1",
  "title": "Witnessmark operation record",
  "type": "object",
  "required": ["run_id", "k", "phase", "op_id", "client", "kind", "input", "inv", "ret", "outcome"],
  "properties": {
    "run_id": { "type": "string" },
    "k": { "type": "integer", "minimum": 0, "description": "trial number; 0 for setup" },
    "phase": { "enum": ["setup", "control", "race", "quiesce", "observe", "nemesis", "stub"] },
    "op_id": { "type": "string", "description": "<k>-<client>-<seq>, unique within the run" },
    "client": { "type": "string", "description": "c00..cNN, nemesis, or stub" },
    "process": { "type": "string", "description": "pid or container name" },
    "kind": { "type": "string", "description": "claim, write, incr, read, ingest, delete, search, snapshot, merge, pause, resume, kill, llm, embed, rerank, ..." },
    "input": { "type": "object", "description": "normalised parameters; never secrets" },
    "inv": { "$ref": "#/$defs/time" },
    "ret": { "oneOf": [ { "$ref": "#/$defs/time" }, { "type": "null" } ],
             "description": "null when the outcome is unknown" },
    "outcome": { "enum": ["ok", "fail", "unknown"] },
    "result": { "description": "normalised result" },
    "raw": { "type": ["string", "null"], "maxLength": 65536, "description": "raw response, capped" },
    "raw_sha256": { "type": "string", "description": "hash of the full raw response" },
    "error": {
      "oneOf": [
        { "type": "null" },
        {
          "type": "object",
          "required": ["type", "message"],
          "properties": {
            "type": { "type": "string", "description": "typed error name, e.g. WriterFenced" },
            "code": { "type": ["string", "integer"] },
            "message": { "type": "string" }
          }
        }
      ]
    },
    "token": { "type": ["string", "null"], "description": "commit id, sequence number or bookmark returned by the SUT" }
  },
  "$defs": {
    "time": {
      "type": "object",
      "required": ["mono_ns", "wall", "domain"],
      "properties": {
        "mono_ns": { "type": "integer" },
        "wall": { "type": "string", "format": "date-time" },
        "domain": { "type": "string", "description": "clock domain, e.g. host or docker-vm" }
      }
    }
  }
}
```

### 9.4 Evidence tags

| Tag | Meaning | Cited as |
|---|---|---|
| [measured] | from a run in `evidence/` | run_id |
| [ours] | measured earlier in the maintainer's own published work, such as GNOMON's hazard log; re-measured before anything relies on it | link |
| [code] | read in source at a pinned commit | path:line @ commit |
| [docs] | stated in the project's documentation | link @ version |
| [gh] | stated in a public issue or pull request | owner/repo#N |
| [inference] | reasoned from the above, not observed | its premises |
| [unmeasured] | a hypothesis waiting for a run | the scenario that will test it |

### 9.5 Redaction

- **No secrets.** Environment variables whose names contain `KEY`, `TOKEN`, `SECRET` or `PASSWORD` are dropped from recorded environments. The stubs make API keys unnecessary in the first place.
- **No personal paths or hostnames.** The home directory becomes `~`. Hosts are described by OS, CPU model, core count and memory only.
- **Capped responses.** A raw response is kept up to 64 KiB per operation, with the SHA-256 of the full response.

### 9.6 Regeneration rule

The reporter produces every number in a report, an issue comment or a draft from `evidence/`. Hand-typed numbers are not allowed. Every table cell names its run_id.

### 9.7 Reading a verdict: too few valid trials

Adopted 2026-11-16 (maintainer ruling at M5 Phase E).

- **Rule.** A verdict computed on fewer than half of the run's declared trials (`trials_valid` × 2 < `scenario.trials`) is read as **insufficient valid trials**. It is not quoted as PASS or FAIL, nor as BOUNDARY for a violation, whatever the manifest says. The Results text names the cause, for example "1 of 20 valid; the other 19 hit the Ladybug lock".
- **Evidence and reports stay as written.** The verdict code is not changed in M5, because a change would alter committed reports. Enforcing the rule in code, with a report column, is an M6 candidate (§12.1, Phase E).
- **Cells it touches in M3 to M5.** Checked over every committed manifest with a verdict list. Three cells were quoted with a verdict, and their text is corrected:
  - Cognee M3 R2 `c1.k4`: 2 of 20 valid. The other 18 raised `AfterRunHookError` [measured: `20261114T133423Z-70f45910`].
  - Cognee M3 R2 `c1.disjoint.k4`: 5 of 20 valid, the rest `AfterRunHookError` [measured: `20261114T212346Z-a6f1985e`].
  - Cognee M5 R1 `c2.improve`: 1 of 20 valid, the Ladybug lock [measured: `20261116T123522Z-49f0100f`].
- **Cells already unquoted.** The other M3 runs below half are INVALID in their reports, and the Results text quotes no PASS or FAIL for them: the Ladybug-lock runs of §12's boundary paragraph, R2 `c1.k8` and R3's C3 runs. So is the superseded batch-1 run `20261114T143626Z-f94d7606`, 9 of 20 valid. M4 and the Omnigraph and Graphiti M5 runs have no verdict below half.
- **Outside M3 to M5.** M2's G3 case-suite manifests declare 6 trials and record `trials_valid` 1 for I7C, I2 and MR1, because each of those is judged only in the one case that checks it. Every case was valid [measured: for example `20261113T174543Z-20792bcd`]. That is how case suites count, not a shortage of valid trials. M6's code rule has to tell the two apart.

## 10. Reporting rules

- **Counts, not only rates.** Write "17 of 20 trials had more than one winner", with the sequential control's result beside it.
- **Scope with every result.** Give versions, digests, topology (for example one node on local disk), host and mode.
- **Name the expectation basis.** A defect is a violation of documented behaviour or of a standard. BOUNDARY and OBSERVED results are reported as what they are.
- **Report passes as readily as failures.** When a check comes out clean, credit the project.
- **No fishing.** Declare a parameter sweep before it runs, and report every result in it.
- **Drop rule.** When a target's headline scenario is clean and its controls are valid, report it and move on.
- **Comparative numbers.** Name both pins, use the same host, and include the full reproduction.

## 11. Contribution and outreach rules

### 11.1 Draft first

- **Drafts.** Every outward text is written in `drafts/`, which is gitignored. That covers issues, comments, pull requests, gists, emails, direct messages and posts.
- **Review and sending.** The maintainer reads each draft in full and sends it. Tooling never posts.
- **Per-message approval.** Approving one message does not cover the next.
- **Follow-ups.** At most one, no sooner than seven days, and only if it adds information.

### 11.2 Non-competing contribution

- **No competing PRs.** Never open a pull request for an issue that already has someone else's open pull request. Contribute the executed test instead: its results on the release, on main and on that pull request's head, posted as the bar the fix has to clear.
- **Credit.** When building on community work, such as someone's test cases, credit its author by GitHub handle.
- **When to open a PR.** Only when all three hold:
  - no open pull request exists;
  - the project's gate allows it (section 11.3);
  - a maintainer has signalled interest.

### 11.3 Project gates (checked 2026-11-13; check again before every contribution)

| Project | Gates |
|---|---|
| getzep/graphiti | File an issue first, and link every pull request to it. Feature work needs a discussed issue labelled `rfc-approved`. Sign the CLA when the bot asks. [docs: CONTRIBUTING.md @ v0.31.2] |
| topoteretes/cognee | Bugs go in issues. Pull requests target `dev`. Every commit needs a DCO sign-off. [docs: CONTRIBUTING.md @ v1.6.8] |
| ModernRelay/omnigraph | Issues are the only inbound channel; Discussions are not used. A pull request must link an accepted issue or an accepted RFC, unless it is trivial. An RFC comes only after maintainers agree to one. [docs: CONTRIBUTING.md @ main] |
| FalkorDB/FalkorDB | Root causes in the engine, found through a target, are filed here. Check the gates before filing. |

### 11.4 Claims discipline

- Only measured claims, each with its tag (section 9.4) and its scope.
- Plain words. Say what happened ("two clients were told they won"), not adjectives ("broken", "unsafe").
- Neutral test vocabulary (adopted 2026-11-15). Prose says loopback-only network patch, fault injector, pause/resume the test container, stop, fail over to the second test server, and stale writer from the previous epoch. Schema values (`nemesis`, `kill`) and code identifiers keep their names, so recorded evidence and code stay readable.
- Keep documented behaviour apart from defects, and say which documentation applies.
- Peer tone: no flattery, no requests for work, no prices in public threads.

### 11.5 Comparative benchmarks

- Publish only with the full reproduction and both engines pinned.
- First check the licence terms for any restriction on publishing benchmarks.
- Give every vendor in the comparison the results first, in its own tracker or by a direct note, before posting more widely.

### 11.6 Security

A finding that crosses a privilege boundary goes through the project's `SECURITY.md` channel, not a public issue. A correctness bug that any client with write access can already trigger goes in a public issue.

### 11.7 Clean-room boundary

**Allowed inputs:**

- public source at pinned commits;
- public documentation;
- public issues and pull requests;
- workloads, fixtures and synthetic data written in this repository.

**Not allowed:**

- confidential material of any third party: client query shapes, schemas, data, results, contract terms and private code;
- anything received under a non-disclosure agreement;
- the maintainer's own unpublished experiments.

**Mechanism.**

- Client-specific work, if any, runs in separate private checkouts outside this repository, and nothing from them is copied back.
- A generic improvement is rewritten here from public inputs, and its commit message names the public source.
- `drafts/` and `private/` are gitignored as a backstop. The backstop is not the control.

## 12. Build sequence

Each milestone ends with a review by the maintainer, and the next one starts only after that review.

| Milestone | Delivers | Exit criterion |
|---|---|---|
| M0 | Scaffold, licence, README, four blueprints (this commit) | Reviewed |
| M1 | Core runner; history and evidence writers; I1 and I2 checkers; standard-library FalkorDB (RESP) and Neo4j (HTTP) adapters; the controls | SC and NC pass; PC fires on Neo4j; δ calibrated on this host |
| M2 | Graphiti adapter, in-process stubs, scenarios G1 to G4 | SC reproduces the fixture graph on both backends |
| M3 | Cognee adapter, HTTP stub endpoint, matrix rows R1 to R3 | SC passes on every row |
| M4 | Omnigraph adapter, O1 and I6 controls, O4 failover observations, O5 on a local root | The re-measured FalkorDB copy curve falls inside the S28 band |
| M5 | Clean reruns, reports regenerated from evidence, drafts | Every number traces to a run_id |

**Status.** M1 met its exit criterion on 2026-11-13:

- batch `m1-20261113T162442Z`;
- harness commit `c317583`, with a clean tree;
- report in `evidence/M1_CALIBRATION.md`.

All 12 sequential controls and all 9 negative controls were met, and all 3 positive controls fired.

**Review, M1.** Reviewed and signed off by the maintainer on 2026-11-16. M1 is closed.

**Status, M2.** M2 met its exit criterion on 2026-11-13:

- batch `m2-20261113T174128Z`, harness commit `526e98f`;
- report in `evidence/M2_GRAPHITI.md`;
- results in the Graphiti blueprint, §11.

The sequential control reproduced the fixture graph in all 11 race runs, on FalkorDB and on Neo4j. G6–G8 are deferred.

**Review, M2.** Reviewed and signed off by the maintainer on 2026-11-16. M2 is closed.

**Status, M3.** M3's exit criterion is met in part, on 2026-11-15:

- the sequential control passed on all four rows for the primary scenario `c1.k2`, and on 22 of the 24 final race runs; the two that did not are R3's `c2.writers` and `c3.cross_process`, which trip Cognee 1.6.1 behaviour on FalkorDB (target blueprint C27, §12), so those two are INVALID by rule (§9);
- batches `m3-20261114T131136Z` (harness `1fd4dd0`), `m3b-20261114T204628Z` (`f3dbe98`), `m3c-20261114T221140Z` (`84dcdb7`) and `m3d-20261114T233706Z` (`5747966`); the later batches re-ran what a harness fix or a crash spoiled, and the target blueprint's §12 says which and why;
- reports in `evidence/M3_COGNEE.md`, `evidence/M3_COGNEE_B2.md`, `evidence/M3_COGNEE_B3.md` and `evidence/M3_COGNEE_B4.md`; results in the Cognee blueprint, §12;
- R4 (PostgreSQL) and the C2 `memify` check were deferred. The maintainer skipped the GLiNER check permanently and declined pull-request builds for M3 (Cognee blueprint §10–§12).

**Review, M3.** Reviewed and signed off by the maintainer on 2026-11-15, after the closeout commits `4675786` to `57e0049` (support-boundary reporting, the two-node gap, the C0 cause, unit tests, the single-file repros, and the boundary-table fix) and an independent second-reader audit. The C0 repro was re-run for the sign-off and reproduced (exit 0). The decisions on the open items are in the Cognee blueprint, §10 and §11. M3 is closed, and M4 may start.

**Status, M4.** M4 met its exit criterion on 2026-11-15.

- The re-measured FalkorDB `GRAPH.COPY` curve falls inside the S28 band at all three sizes, with 95.3, 441.7 and 1,820.0 ms against 165, 546 and 2,400 (-42%, -19%, -24%) under S28's `appendonly yes` and `appendfsync always` settings [measured: `20261115T172253Z-0adb5788`]. The first attempt was 61%, 49% and 57% faster than S28 and the batch stopped by rule [measured: `20261115T164756Z-236def5c`]. It likely inherited the baseline's `appendonly no` [inference from `persistence_found` in `20261115T165838Z-b4925bd5` and `20261115T172253Z-0adb5788`].
- Six batches. The false start `m4-20261115T153532Z` has one planned manifest at `46adb1d` and no results [measured: `20261115T153548Z-45dc303e`]. The five reported batches are `m4-20261115T153804Z` (`46adb1d`), `m4b-20261115T164749Z` (`48737aa`), `m4c-20261115T165831Z` (`8f7bb3b`), `m4d-20261115T172246Z` (`2a02bd8`, the main batch) and `m4e-20261115T183929Z` (`8bc5fd3`) [measured: `20261115T154356Z-9ebd8e7e`, `20261115T164756Z-236def5c`, `20261115T165838Z-b4925bd5`, `20261115T172253Z-0adb5788`, `20261115T183931Z-fa543284`]. The Omnigraph blueprint's §10 records the batch history.
- reports in `evidence/M4_OMNIGRAPH.md` and `evidence/M4_OMNIGRAPH_B1.md` to `_B4.md`; results in the Omnigraph blueprint, §10;
- O4 recorded unclaimed epochs and fixed pause offsets without staging or publish-phase verification. In `m4e` the stable MinIO cells were BOUNDARY and the edge cells were NOT_EXERCISED [measured: `20261115T183001Z-3dcbea3c`, `20261115T184233Z-3a4a4f31`, `20261115T184523Z-2ae7e967`]. At the edge pin an epoch claim requires an embedding program [docs: Omnigraph troubleshooting.md, "Writer epoch" @ `b2dbaff`]. The epoch-claim test waits for an upstream release with a claim route.
- M4 evidence lacks `history.jsonl`, `state/` and `REPRO.md` (the Omnigraph blueprint, §10) [measured: the M4 run directories in `evidence/omnigraph/`, including `20261115T153548Z-45dc303e` through `20261115T184523Z-2ae7e967`]. The M5 decisions, including the O2, O3 and O6 work and O5 on MinIO, are in the Omnigraph blueprint's §11.
- commit `bfdec20` carries a `Co-Authored-By` trailer by mistake; it is kept because the evidence records harness commit hashes.

**Review, M4.** Reviewed and signed off by the maintainer on 2026-11-16, after the independent second-reader audit and the correction commit `387b2cf`. The decisions on the open items are in the Omnigraph blueprint, §11. M4 is closed, and M5 may start.

### 12.1 M5 plan

Each phase has its own prompt and starts after the maintainer gives that phase the go-ahead.

**Counting rule for the phase statuses (adopted 2026-11-16 at Phase E).** A batch's command count is every command its driver logs, numbered from 00, with the baseline commands included. Its exit count is those that ended with exit 0. A false start that ran only its baseline commands is counted the same way. The counts come from the driver logs under `.state/scratch/` (kept locally, not committed).

- [x] **Maintainer decision (2026-11-16).** Run O2 and O3 in `thread` mode
  on the Windows host (§3.4). `container` mode is out of scope for M5.

The existing thread runner releases clients together through a barrier, with
one connection per client [code: `core/witnessmark/runner.py` @ `2e0dbd7`].
M1 calibrated the 40 ms gate on this host with 50 clients, using FalkorDB and
Neo4j [measured: batch `m1-20261113T162442Z`, `evidence/M1_CALIBRATION.md`]. Omnigraph serves HTTP, so
either client layout can send the same concurrent operations to its server
concurrency controls [inference from the workload and §3.4]. O4 pauses A's
test server container and fails over to B independently of the client mode
[code: `targets/03-omnigraph/witnessmark_omnigraph/part2.py` @ `2e0dbd7`].
O4's planned local transfer likewise stops the test server container.
Network partitions are outside v0.1 (§3.4), so these tests can use the
existing runner.

#### 1. Phase A — Harness gaps

Phase A follows M4 sign-off and ends when selftest passes and one smoke run per Omnigraph scenario under `.state/scratch/` writes all four §9.1 artifacts, with each history validating against §9.3.

Implement the harness changes and cover them with unit tests. Run only the smoke checks in the exit criterion.

- [x] Write `history.jsonl`, `state/<k>.json` and `REPRO.md` with each
  `run.json`, following §9.1. In `history.jsonl`, record fault-injector
  actions as client `nemesis` with wall-clock times in `inv` and `ret`,
  following §9.3.
- [x] Pin the MinIO and proxy images by digest in `compose.yml` before the
  M5 reruns. Record the proxy image ID in the run manifests.
- [x] Capture O4 wall-clock times for pause, resume, successor readiness and
  each acknowledgement. Capture server logs on failure.
- [x] Make the Phase B entry points available. Add the O3 thread race, O6
  parity evidence, O4 clean-stop local transfer, O1 unrelated reader and
  writer, and the O2 calibration option.
- [x] Validate the scratch smoke runs, including O5 evidence on MinIO.
- [x] **Addendum (2026-11-16).** Add the O2b cost curve, `costcurve` for
  both engines, with its declared sweep, and document the
  `Scenario.precondition()` hook (§6.3 and the Omnigraph blueprint, O2b and
  O2 runner wiring). One scratch smoke run of each side wrote all four
  §9.1 files with valid histories. [code:
  `targets/03-omnigraph/witnessmark_omnigraph/costcurve.py` @ `6e2d1af`]

The maintainer approved a clean-stop transfer on 2026-11-16. Start B after
status confirms A released admission. A retained lock or an unclean exit
leaves the cell NOT_EXERCISED. The bootstrap exception applies to fresh
disposable roots only.
[Omnigraph ownership procedure](targets/03-omnigraph/MASTER_BLUEPRINT.md#o4-clean-stop-local-transfer)

#### 2. Phase B — Omnigraph runs

Phase B depends on Phase A and ends when the calibrated gate is recorded and the runs and their controls are checked and recorded in evidence.

Run these in order. Use `thread` mode for the O2 and O3 races, and run each
scenario with its sequential control and the applicable controls in §6.2.

1. [x] Use `--no-spread-gate` for the first O2 batch to record Δ for every trial. Treat 40 ms as
   provisional for Omnigraph, and set its δ using the 1.5 × p99 rule in §6.3
   before reporting O2 or O3 results.
2. [x] Run the O2b cost curve (declared sweep, both engines).
3. [x] Run the O2 claim races with the calibrated gate.
4. [x] Run the O3 merge races with the calibrated gate.
5. [x] Run O6 traversal parity beyond the Part 1 sequential control.
6. [x] Run O5 on MinIO.
7. [x] Exercise O4 local ownership transfer with `failover --variant clean-stop`.
   Stop A gracefully and read `cluster status --json`. Start B only after
   a clean exit and confirmed release. Mark retained or unclean cells
   NOT_EXERCISED and capture their logs.
8. [x] Run O1 with an unrelated-graph reader and a writer on the Omnigraph side
   before any public FalkorDB comparison. Follow §6.5 for the cost curve
   and §11.5 for publication.

**Status, Phase B (2026-11-16).** Steps 1 to 8 ran. Reviewed and signed off by the maintainer on 2026-11-16, after verifying the ten Phase B commits, the six batches, the 58 M5 runs' evidence and the superseded O1 and O2b runs.

- [x] Run plan declared in the Omnigraph blueprint, §12 (`772ef96`).
- [x] Step 1: batch `m5-20261115T222957Z` (`772ef96`), 17 commands, 10 exit 0;
  the seven Neo4j control cells exited 1. They were re-run in
  `m5c-20261115T223540Z` (`772ef96`), 9 of 9 commands exit 0. δ = 55 ms (§6.3),
  set in `fffe48b`. Reports: `evidence/M5_OMNIGRAPH_CALIBRATION.md` and
  `evidence/M5_OMNIGRAPH_B1.md`.
- [x] Maintainer decision (2026-11-16): one actor per client with N = 50, HTTP
  429 classified as the typed refusal `admission_limit`, and a race check that
  accepts every typed definite refusal (`a6b690d`). The per-actor cap of 16 is
  a documented boundary, and two refusal-type differences are OBSERVED
  (Omnigraph blueprint, §12 amendment and §13).
- [x] Steps 2 to 8: batch `m5b-20261115T230235Z` (`6a15b9c`), 37 commands,
  36 exit 0. The O1 cell that failed on a harness bug (host port exhaustion,
  fixed in `f7ae8f2`) was re-run in `m5d-20261116T003205Z` (3 of 3 commands
  exit 0), where the FalkorDB
  curve met the S28 band. Reports: `evidence/M5_OMNIGRAPH.md` and
  `evidence/M5_OMNIGRAPH_B2.md`. Results: Omnigraph blueprint §14.
- [x] O1 method change: from `f7ae8f2` each O1 load keeps one connection,
  where M4 opened one per request, and from `fb97518` each read retried after
  a dropped kept connection is its own history record. Every O1 cell was
  re-run on that method in `m5e-20261116T004953Z` (`fb97518`), 8 of 8 commands
  exit 0, with no read retry. The S28 band was met. Report:
  `evidence/M5_OMNIGRAPH_B3.md`. Batch 2's and `m5d`'s O1 runs are superseded.
- [x] O2b method change: from `4212c99` each O2b agent keeps one connection,
  and a read dropped on it is its own history record. Both engines' full sweep
  was re-run in `m5f-20261116T021553Z` (`4212c99`), 5 of 5 commands exit 0,
  with no read retry and no unknown outcome. Report:
  `evidence/M5_OMNIGRAPH_B4.md`. Batch 2's O2b runs are superseded.

The O4 epoch-claim test and its dependent probes wait for an upstream release
with a claim route. The O1 catalog-width axis and MinIO conditional-write
qualification versus RustFS remain deferred. [Omnigraph decisions (§11)](targets/03-omnigraph/MASTER_BLUEPRINT.md#11-open-questions-and-decisions-after-the-m4-audit)

#### 3. Phase C — Graphiti

Phase C follows Phase B and ends when G6, G7 and G8 have recorded outcomes and evidence.

1. G6. Check index readiness at startup, including what FalkorDB fulltext
   search returns while an index is `UNDER CONSTRUCTION` (§13).
2. G7. Check persistence across restarts in the root and MCP FalkorDB
   Compose configurations.
3. G8. Check deletion permanence under I5 (§5.5).

[Graphiti scenarios (§5)](targets/01-zep-graphiti/MASTER_BLUEPRINT.md#5-scenarios)

**Status, Phase C (2026-11-16).** G6, G7 and G8 ran. Reviewed and signed off by the maintainer on 2026-11-16.

- [x] Phase B sign-off recorded (`9761daa`). The run plan was declared before any batch (`886f4c6`), with pre-batch amendments (`8b9785a`) and the #2119 review (K21).
- [x] Main batch `m5g-20261116T051149Z` (`8b9785a`): 25 commands, 24 exit 0 (corrected at Phase E from "24 commands, 23 exit 0" by the counting rule above). Row 11 (G6a on Neo4j, main), driver command 12, hung and was ended. The false start `m5g-20261116T044019Z` ran its 2 baseline commands (both exit 0) and no row (a driver path bug). Report: `evidence/M5_GRAPHITI.md`.
- [x] Re-run `m5h-20261116T071955Z` (`425e22e`), 3 commands, 2 exit 0 (the baselines): row 11 hung again and was ended under the maintainer's ruling. The cell is INVALID, "harness could not bound a stalled search on this build", with no third run. `0395799` changes how the harness bounds a search.
- [x] Explanatory control `m5i-20261116T092138Z` (`0395799`, maintainer ruling 4): G7 kill-then-start with `appendonly yes`, 4 of 4 commands exit 0 (corrected at Phase E from "2 of 2", which counted the two rows only). Report: `evidence/M5_GRAPHITI_B1.md`.
- Results, findings and the choices taken without the maintainer are in the Graphiti blueprint, §12. In brief:
  - FalkorDB fulltext under construction returns fewer rows without an error (§13).
  - On #2119 the indexes were still under construction after the awaited build returned (KD-F4).
  - Neo4j at-once searches raised typed errors in 11 of 20 and 8 of 20 trials.
  - G6b and G6c were clean.
  - G7 lost everything on kill with `appendonly no` and nothing with `appendonly yes`.
  - G8 on Neo4j lost an acknowledged ingest's fact and entity to a concurrent delete in 20 of 20 trials. This is OBSERVED and a possible Graphiti defect for review; the P5 repro comes in Phase E.

#### 4. Phase D — Cognee

Phase D follows Phase C and ends when C2 and any approved R4 runs have recorded outcomes and evidence.

- [ ] Run C2's deferred `memify` case through its replacement `improve`.
  Script the required prompts with the deterministic stub before measuring it.
- R4 (Ladybug, LanceDB and PostgreSQL) stays blocked until the maintainer
  approves pinning the PostgreSQL baseline and separately approves any
  #4167 pull-request build needed for the C1 advisory-lock case.

**Status, Phase D (2026-11-16).** C2 ran through `improve`. Reviewed and signed off by the maintainer on 2026-11-16, after verifying the four Phase D commits, batch `m5k-20261116T123513Z` (5 of 5 exit 0), the three runs' evidence and the `m5j` false start.

- [x] Phase C sign-off recorded (`b8b35d8`).
- [x] `improve` read at the pin, and its prompts listed and scripted (Cognee blueprint §1.3, C29–C33, `f339e3e`). With no session ids only the graph-fed stages run: `review_conflicts` sends one scripted `ReviewResponse` prompt per call, and `global_context_index` makes no model call at v1.6.8. At cognee 1.6.1 (R3) it is opt-in, and its `GlobalContextSummaryContent` prompts get fixed strings (maintainer-approved). The seven session-fed stages are NOT_EXERCISED, "no session ids in C2's design" (C31).
- [x] C2 run plan declared before the batch (`951ccf9`). I7 stays NOT_APPLICABLE (Cognee blueprint §10).
- [x] Batch `m5k-20261116T123513Z` (`951ccf9`): 5 commands, 5 exit 0. The false start `m5j-20261116T123344Z` ran its 2 baseline commands (both exit 0) and no row (a driver path bug). Report: `evidence/M5_COGNEE.md`. Results: Cognee blueprint §13.
  - R2 was clean in 20 of 20 valid trials: no duplicate vector id, no writer conflict, no partial index, nothing lost or left behind (`20261116T125700Z-b7ebcfbc`).
  - R1 reached the Ladybug boundary in 19 of 20 trials, and in the valid trial's `improve` stage (`20261116T123522Z-49f0100f`). Under §9.7 its verdicts read as insufficient valid trials (1 of 20), not PASS.
  - R3 is INVALID by rule: its control was not met, the C27 edge (`20261116T131854Z-43702faa`).
- [x] #5253: every cell NOT_EXERCISED by the maintainer's ruling. Its head is based on main `c4cd8ceb`, 1,783 commits behind v1.6.8, and 11 of 16 `LanceDBAdapter.py` hunks do not apply (Cognee blueprint C32). R4 stays deferred.

The GLiNER check stays permanently skipped. The M3 C27 findings for C2 and C3 on
R3 stand as documented. The C3 fixture variant on R3 remains an open question.
[Cognee decisions (§10)](targets/02-cognee/MASTER_BLUEPRINT.md#10-open-questions)

#### 5. Phase E — Closeout

Phase E follows Phase D and ends with the maintainer's M5 review recorded in this section.

1. Rerun only where a harness fix requires it.
2. Regenerate reports from evidence and verify that every reported number
   traces to a run ID (§9.6).
3. Prepare contribution drafts in `drafts/` under §11.1 for the
   maintainer to review and send. Tooling never sends them.
4. Record the maintainer's M5 review.

**Notes for Phase E (recorded 2026-11-16 at the Phase B sign-off; not fixed now).**

- (a) The Part 2 run manifests (O1, O2b, O4, O5, O6) carry null `controls`
  and `verdicts`, which §9.2 lists as required. Decide in Phase E whether to
  amend §9.2 or fill them.
- (b) Candidate upstream questions for drafts under §11.1 (never sent by
  tooling): O2a losers refused with `CardinalityViolation` instead of
  `precondition_failure` (447 of 980 and 496 of 980 in `m5b`), and the O2b
  attempt curve.
- (c) Recorded 2026-11-16 at the Phase D ruling, for a Phase E draft under §11.1: #5253's head is based on main
  `c4cd8ceb`, 1,783 commits behind cognee v1.6.8, and 11 of its 16 `LanceDBAdapter.py` hunks do not apply
  to v1.6.8 (Cognee blueprint C32).

**Maintainer rulings on these notes (2026-11-16, at the Phase E go-ahead).**

- (a) Settled by amending §9.2 ("Measurement runs"); the manifests are not filled in. The rule is enforced in the Omnigraph manifest writer and covered by a unit test. Every report stays byte-identical.
- (b) and (c) are inputs to the Phase E drafts (§11.1), kept in `drafts/m5/` and never committed.
- (d) New: a verdict on fewer than half of the declared trials reads as insufficient valid trials (§9.7). Three Results cells were corrected in text; no verdict code changed.
- (e) New: one counting rule for the phase statuses (top of §12.1). The Phase C main batch and `m5i` lines were corrected, and the counts for the other batches were added.
- `schema_version` (ruled at the Phase E resume): the 64 measurement manifests that carry the integer 1 stay as written, and the writer emits `"0.1"` from `4153b02` (§9.2).
- No reruns, and no harness fix is pending. G6a on Neo4j with main stays INVALID as ruled. R3 stays INVALID by rule. #5253 stays NOT_EXERCISED.

**M6 candidates (recorded at Phase E, not started).**

- Enforce §9.7 in the verdict code from M6, with a report column for runs below half their declared trials. Case suites such as G3 need their own count (§9.7).

**Status, Phase E (2026-11-16).** Steps 1 to 3 ran. Step 4, the maintainer's M5 review, is not recorded.

- [x] Phase D sign-off recorded (`f25653d`). Rulings (a), (d) and (e) applied (`4deb2fc`, `b5593f0`); the `schema_version` ruling applied in the writer (`4153b02`) and in §9.2 (`62bcbda`).
- [x] Step 1: nothing was re-run. No harness fix required a re-run, and the `schema_version` fix changes no evidence.
- [x] G8-F1's P5 repro, declared before it ran (`37aefe8`) and recorded (`79015bb`): 19 of 20 iterations differed on Neo4j on both v0.31.2 and main `ebef986a`, 0 of 20 on FalkorDB on both, and the sequential control was as expected in all four runs (Graphiti blueprint §12.5).
- [x] Step 2: all 21 committed reports regenerate byte for byte. The §9.6 audit (`48ca0d7`) read 204 number-bearing claim blocks in the four M5 Results sections and these statuses, 50 of them tagged [measured], and checked their numbers against the manifests, histories and reports of the runs they cite. Every [measured] claim now names its run or batch id. The one exception is the P5 repro's counts, which carry the tag declared for them and come from console output kept outside `evidence/`. One count was wrong and is corrected (the first ended G6a run wrote states 0–7, not 0–5). One omission is added (G6c's observe-phase builds that ended running). One stale tag is retagged (the Omnigraph admission-cap docs check). No other mismatch was found.
- [x] Step 3: seven drafts in `drafts/m5/`: a sending plan and six messages, written for the maintainer under §11.1. They are gitignored, not committed and not sent.
- [ ] Step 4: the maintainer's M5 review.

**M5 summary.** On the host of §10. Tags as in §9.4; every run id is in `evidence/`.

| Target and scope | Headline results | BOUNDARY, OBSERVED, INVALID, NOT_EXERCISED | Not run |
|---|---|---|---|
| **Omnigraph** v0.15.0 and edge-b2dbaff; one server, local root unless stated, `thread` mode, 50 clients with one actor each, δ = 55 ms (Omnigraph blueprint §14) | **PASS on both builds.** O2a, O2c and O3: 1 acknowledged winner and 1 holder in 20 of 20 valid trials each, 120 of 120 in all, and no merge picked a winner silently [measured: `20261115T231454Z-7f2e75a3`, `20261115T231539Z-c7be08c9`, `20261115T231626Z-b28d5aff`, `20261115T231715Z-071a8831`, `20261115T231810Z-701d1d1d`, `20261115T232110Z-c67ea540`]. O6: traversal results identical to Neo4j and FalkorDB [measured: `20261115T232412Z-8935cb2f`, `20261115T232421Z-31c6fa46`]. O2b, the cost of documented behaviour: median attempts N(N + 1)/2 up to N = 25, and 1,269 and 1,264 at N = 50, with every agent claimed [measured: `20261116T021606Z-a0862379`, `20261116T022103Z-8b10eb2d`]. O1 on kept connections: curves for both builds on local, MinIO and proxy roots, no read retried [measured: batch `m5e-20261116T004953Z`]. **Credit:** every acknowledged write survived the documented clean-stop transfer. | BOUNDARY: the per-actor admission cap of 16, documented as a 429 (batch 1 [measured: `20261115T223017Z-22107db4`, `20261115T223104Z-bcff6931`, `20261115T223149Z-b1b52c9c`, `20261115T223237Z-3658b53d`]). OBSERVED: admitted O2a losers refused with `CardinalityViolation` where the docs say `precondition_failure`, 447 of 980 and 496 of 980 (`7f2e75a3`, `c7be08c9`); O2c answered `conflict` on v0.15.0 (381) where edge answered `CardinalityViolation` (`b28d5aff`, `071a8831`); O5 seen on the first poll, 1,439.9 and 1,498.6 ms on MinIO [measured: `20261115T232428Z-7b3675aa`, `20261115T232445Z-74a4b9d4`]; O4 clean-stop transfer worked on both builds, with the fence not engaged [measured: `20261115T232518Z-4a2c639b`, `20261115T232527Z-f549fc44`]. INVALID and NOT_EXERCISED: none; batch 1's O2 FAIL verdicts are calibration runs from the superseded checker. | O4's epoch-claim test and its probes (no claim route upstream); O3's merge-throughput curve against branch count; O1's catalog-width axis; MinIO conditional-write qualification; O5 with a concurrent second reader. |
| **Graphiti** v0.31.2, main `ebef986a` and #2119's head `b2b727e0`, on FalkorDB 6.0.4 and Neo4j 5.26.2 (Graphiti blueprint §12) | **PASS:** G6a on FalkorDB on all three builds, answers identical 200 of 200 [measured: `20261116T051153Z-2e987ec0`, `20261116T051801Z-c9fd6666`, `20261116T052409Z-5885a291`]; G6b on both backends and all three builds, no trial met an index that was not ready [measured: `20261116T053018Z-2290cc18`, `20261116T053508Z-67de8ce9`, `20261116T053958Z-f4b4332f`, `20261116T064831Z-bea83c1a`, `20261116T065525Z-d552844d`, `20261116T070159Z-af2cbe2f`]; G6c, eight concurrent ingests lost and duplicated nothing, credit to the #1676 fix [measured: `20261116T054448Z-74713339`, `20261116T054508Z-0928df36`, `20261116T054530Z-07a4e09a`]; G7 restart and down-then-up kept everything on both layouts, 10 of 10 each [measured: `20261116T070849Z-c09d11b2`, `20261116T070935Z-cdf2ec96`, `20261116T071106Z-079f03e1`, `20261116T071148Z-932b738f`]; I5 held in G8 on both backends. No G6 run recorded a never-retrieved task exception. | OBSERVED: **G8-F1**, on Neo4j a concurrent `remove_episode` took an acknowledged episode's fact and entity in 20 of 20 trials [measured: `20261116T071325Z-4bc1eaa9`], 0 of 20 on FalkorDB [measured: `20261116T071319Z-334d816c`]; the P5 repro gave 19 of 20 on Neo4j and 0 of 20 on FalkorDB, on v0.31.2 and main [measured: repro_g8_remove_vs_add.py at `37aefe8`]; undocumented at v0.31.2, support level none. main's later concurrent-ingestion spec (`869c1b27`, not run) names the race for its opt-in path only (Graphiti blueprint §12.5). G6-F1, FalkorDB fulltext under construction returned fewer rows or all, never an error. G6-F2, on #2119 an index was still under construction after the awaited build in 20 of 20 trials (`5885a291`). G6-F4, Neo4j at-once searches raised `ProcedureCallFailed` in 11 of 20 and 8 of 20 trials (`20261116T054555Z-85bc1662`, `20261116T064351Z-20ab7a28`). G7-F1, kill-then-start with `appendonly no` lost everything since the last snapshot in 10 of 10 on both layouts (`20261116T071025Z-e638bddf`, `20261116T071238Z-cfee79ff`); with `appendonly yes` nothing (`20261116T092142Z-a5ceedc5`, `20261116T092229Z-98725745`); tied to the persistence configuration. G7-F3, the root layout's `FALKORDB_ARGS` replace the module arguments. INVALID: G6a on Neo4j with main, the harness could not bound a stalled search (`20261116T055056Z-3d69b1c9`, `20261116T071959Z-74370fb1`). NOT_EXERCISED: the combined MCP image. NOT_APPLICABLE: G6c on Neo4j. | G6 at 20k facts; a third run of G6a on Neo4j with main; repros for G6 and G7, whose findings are engine or deployment behaviour. |
| **Cognee** v1.6.8 (R1, R2) and 1.6.1 with adapter `ff1324ec` (R3), C2 through `improve` (Cognee blueprint §13) | **PASS on R2** (I1B, I2, I4, I5), support boundary: 20 of 20 valid, no duplicate vector id, no writer conflict, no partial index, nothing lost or left behind [measured: `20261116T125700Z-b7ebcfbc`]. **Credit:** `improve`'s stages kept their own writes and B's data intact next to a `cognify` and a delete on the same store. | Insufficient valid trials (§9.7) and BOUNDARY: R1, 1 of 20 valid, the Ladybug one-process lock in the other 19 and in that trial's `improve` [measured: `20261116T123522Z-49f0100f`]. INVALID by rule: R3, control not met, the C27 edge [measured: `20261116T131854Z-43702faa`]. NOT_EXERCISED: every #5253 cell (its head does not apply to v1.6.8, C32); the seven session-fed `improve` stages. NOT_APPLICABLE: I7. | R4 (PostgreSQL); the GLiNER check (skipped permanently); the C3 fixture variant on R3. |
| **FalkorDB control** 6.0.4 | Five M1 shapes, 0 of 20 trials violating in each, in batch 1 and batch 2, with sequential controls met [measured: batches `m5-20261115T222957Z` and `m5b-20261115T230235Z`]. `GRAPH.COPY` met the S28 band at all three sizes, 121.5, 321.2 and 1,955.0 ms [measured: `20261116T005007Z-772bf510`]. In O2b every admitted claim succeeded on its first attempt [measured: `20261116T022558Z-e0fff930`]. | OBSERVED: its own admission limit, `Max pending queries exceeded`, refused 60 to 118 claims per claim-control run with no violation [measured: `20261115T231353Z-aacd795d`, `20261115T222959Z-dd58c949`], and 11 agents across 3 of 5 measured N = 50 repetitions in O2b (`e0fff930`). The comparison with Omnigraph stays internal (§11.5). | No public comparison. |
| **Neo4j control** 5.26.2 community | The three naive shapes fired in 20 of 20 trials each (KNOWN_DEVIATION, KD-N1), and the four lock-first, direct and disjoint shapes had 0 of 20 violating, in `m5c` and batch 2 [measured: batches `m5c-20261115T223540Z` and `m5b-20261115T230235Z`; Omnigraph blueprint §14, Controls]. It is O6's primary reference. | Graphiti's G6-F4 and G8-F1 above ran on it. | – |

M5's exit criterion, "every number traces to a run_id", holds for the Results sections and these statuses after `48ca0d7`, with the P5 repro's counts as the declared exception above.

Phase E awaits the maintainer's M5 review.

## 13. Open questions

| Question | Settled in |
|---|---|
| Can the release-spread bounds be met on Windows with Docker Desktop? | Answered for `thread` mode in M1: 50 threads cannot meet 5 ms (p50 7.88 ms), so δ is 40 ms (section 6.3). The other modes are measured when they land. |
| Should clients run inside the Docker network rather than on the Windows host? | Still open. M1 ran its clients on the Windows host, and M5 keeps them on the host (§3.4). |
| What does FalkorDB fulltext search return while an index is `UNDER CONSTRUCTION`: the same rows, fewer rows, or an error? | Answered in M5 Phase C by Graphiti G6a on FalkorDB 6.0.4. While the RELATES_TO fulltext index was under construction, the query returned fewer rows than the 2,000 of the control, or all of them, and never an error. Counted in monitor samples: 3 fewer and 5 all on v0.31.2, 1 and 4 on main, 58 and 2 on #2119. Before the index existed it returned 0 rows, again with no error [measured: `20261116T051153Z-2e987ec0`, `20261116T051801Z-c9fd6666`, `20261116T052409Z-5885a291`]. Neo4j 5.26.2 differs: a missing index is a typed error, and a populating one returned every row [measured: `20261116T054555Z-85bc1662`, `20261116T064351Z-20ab7a28`]. Graphiti blueprint §12.3, G6-F1. |
| When do Neo4j fulltext and vector indexes reflect a committed write? | Answered in M2 by Graphiti G4 on Neo4j 5.26.2. Both the writing instance and a second instance saw 10 of 10 writes on the first search [measured: `20261113T175059Z-738c7f37`]. |
| Which Neo4j release breaks ties (section 7.4)? | Pinned when first needed |

## Appendix A. Glossary

| Term | Meaning |
|---|---|
| SUT | System under test. |
| Guarded claim | A single write that succeeds only if the resource is unheld. |
| Naive shape | A guarded write whose guard is read without a lock. |
| Lock-first shape | A write that takes the node's write lock, by writing a dummy property, before it reads its guard. |
| Functional key | A subject–predicate pair that holds one value at a time. |
| Copy weight | The share of a branch cycle spent creating the branch. |
| Contention evidence | A fired positive control, or an observed overlap of clients' critical windows. |
| Expectation basis | The documented promise, standard, baseline or issue a verdict is judged against. |
