# Target 03: Omnigraph (ModernRelay/omnigraph)

Part of Witnessmark. Read it with the [master blueprint](../../MASTER_BLUEPRINT.md); "master §n" means a section of that document.

| | |
|---|---|
| Status | Specification v0.1, 2026-11-13. Part 1 and the M4 batches (O1, O4, O5, I6 controls) are recorded in §10. M5 Phase B: the run plan is §12, batch 1 and the maintainer decision are §13, and the results of all five batches are §14. Phase B awaits review. |
| Project | [ModernRelay/omnigraph](https://github.com/ModernRelay/omnigraph), MIT, written in Rust. A typed property graph stored as Lance datasets on local disk or object storage, with git-style branches, typed merges and time travel. |
| Versions under test | **v0.15.0**, tag commit `373834b4c1` (2026-11-09): the latest stable tag, from before the writer epoch fence.<br>**edge-20261113-b2dbaff**, commit `b2dbaff7584eb849a98fa139876e0ae474e929ea`: 35 commits after v0.15.0. It includes [#1350](https://github.com/ModernRelay/omnigraph/pull/1350), merged 2026-11-11, which adds writer epoch fencing. |
| Binaries | `omnigraph` and `omnigraph-server`, packaged from the official pinned Linux release archives in a Linux image after checking their published SHA-256 values. No piped install script is used. |
| Storage | A local filesystem root. MinIO (S3-compatible), with and without a proxy that adds a fixed delay per request; the delay follows the method of [#642](https://github.com/ModernRelay/omnigraph/issues/642). |
| Baselines | FalkorDB 6.0.4 `GRAPH.COPY` for I6. FalkorDB 6.0.4 and Neo4j 5.26.2 for I1 controls and I4 parity (master §7). |
| Out of scope | Omnigraph Cloud, Azure roots, the MCP surface |

Documentation links point at main `9fb5b48e65d09db5ca8206ced437a0e4ec07cef6` (2026-11-13).

**Vocabulary (2026-11-15, master §11.4).** This document says fault injector, pause/resume the test container, fail over to the second test server, and stale writer from the previous epoch. The history schema still records fault actions under client `nemesis`.

## 1. What is already known

**Re-checked 2026-11-15.** The two pins still resolve to v0.15.0 commit
`373834b4c1c4b29cf0ddd64bee9565f98c60cc26` and edge-20261113-b2dbaff commit
`b2dbaff7584eb849a98fa139876e0ae474e929ea`; v0.15.0 is still the latest stable
release ([releases](https://github.com/ModernRelay/omnigraph/releases)) [gh]. Two newer edge builds exist,
[edge-20261114-2c0941e](https://github.com/ModernRelay/omnigraph/releases/tag/edge-20261114-2c0941e)
(`2c0941e0f3b58c1200227a06b475acdc9a89858b`) and
[edge-20261115-6d92b43](https://github.com/ModernRelay/omnigraph/releases/tag/edge-20261115-6d92b43)
(`6d92b436bb259149de8f7e546b699f40ba2589ab`); the test pins do not move [gh].
Issues [#642](https://github.com/ModernRelay/omnigraph/issues/642),
[#643](https://github.com/ModernRelay/omnigraph/issues/643),
[#1355](https://github.com/ModernRelay/omnigraph/issues/1355) and
[#1094](https://github.com/ModernRelay/omnigraph/issues/1094) are still open, while
[#1328](https://github.com/ModernRelay/omnigraph/pull/1328) and
[#1350](https://github.com/ModernRelay/omnigraph/pull/1350) remain merged [gh]. The writer-epoch RFC
still says `status: draft`, but its `implementation` has changed from `not-started` to `in-progress`
[docs: [RFC frontmatter](https://github.com/ModernRelay/omnigraph/blob/main/docs/rfcs/2026-11-09-writer-epoch-fence.md)].

| # | Fact | Tag |
|---|---|---|
| O-K1 | Reads are snapshot-isolated. A read-view capture waits for an exclusive pass on any handle of the process: schema apply, open, refresh, reload, `sync_branch`, branch create and others. The gate is write-preferring, so reads wait from the moment such a pass is queued. In-process gates prevent same-process races; durable correctness comes from manifest preconditions and Lance transactions. The docs warn against reading distributed writer safety into an in-process mutex ([architecture.md, "Concurrency and support boundary"](https://github.com/ModernRelay/omnigraph/blob/9fb5b48e65d09db5ca8206ced437a0e4ec07cef6/docs/dev/architecture.md#concurrency-and-support-boundary)). | [docs] |
| O-K2 | An ordinary write publishes under `ExactGraphHead` authority. A retryable attempt that fails before taking effect discards all staged work and captures fresh authority ([writes.md](https://github.com/ModernRelay/omnigraph/blob/9fb5b48e65d09db5ca8206ced437a0e4ec07cef6/docs/dev/writes.md)). | [docs] |
| O-K3 | Conditional mutations take `--if-commit <graph_commit_id>`. Any intervening commit, even an unrelated one, invalidates the condition. On a mismatch nothing is written and the response reports `precondition_failure`. The docs tell callers to re-read and decide again, not to retry blindly ([mutations/conditional.md](https://github.com/ModernRelay/omnigraph/blob/9fb5b48e65d09db5ca8206ced437a0e4ec07cef6/docs/user/mutations/conditional.md)). | [docs] |
| O-K4 | Schema constraints include `@key`, `@unique` and `@card(min..max)`. `@card` counts the edges of a type that start at each source node. A write that leaves a node outside the bounds is refused before publication ([schema/index.md L91, L131–133](https://github.com/ModernRelay/omnigraph/blob/9fb5b48e65d09db5ca8206ced437a0e4ec07cef6/docs/user/schema/index.md)). | [docs] |
| O-K5 | A merge reports typed conflicts: `DivergentInsert`, `DivergentUpdate`, `DeleteVsUpdate`, `OrphanEdge`, `UniqueViolation`, `CardinalityViolation` and `ValueConstraintViolation`. The docs state that a merge never silently picks a winner ([merge.md](https://github.com/ModernRelay/omnigraph/blob/9fb5b48e65d09db5ca8206ced437a0e4ec07cef6/docs/dev/merge.md)). | [docs] |
| O-K6 | The writer epoch fence. The RFC ([2026-11-09-writer-epoch-fence.md](https://github.com/ModernRelay/omnigraph/blob/9fb5b48e65d09db5ca8206ced437a0e4ec07cef6/docs/rfcs/2026-11-09-writer-epoch-fence.md)) was merged as text by [#1328](https://github.com/ModernRelay/omnigraph/pull/1328) on 2026-11-09, and implemented by [#1350](https://github.com/ModernRelay/omnigraph/pull/1350), merged 2026-11-11. The RFC's frontmatter on main still says `draft`; `implementation` now says `in-progress`. `writes.md` now documents the writer epoch and the error `WriterFenced { held, read, current }`, which is not retried. | [docs] [gh] |
| O-K7 | The gap the RFC closes. Writer exclusion across processes used to rest on a deployment rule (one mutation-capable writer process per cluster) and on admission locks. A server that stalled, was replaced and then woke up could still publish while its head precondition held, which left two writers on one branch. The RFC adds that no lock timeout closes this gap. | [docs] |
| O-K8 | What the fence covers. It fences publications through the publisher only. Branch creation and deletion, and cleanup, keep the single-writer-process boundary. Lance ref metadata puts, ref unlinks and deletes, collector deletes and optimize's configuration commit are not fenced. The stated freshness bound: after a failover, the old owner's reads may miss the successor's publishes until the old owner's next publish is refused, or until it is stopped. | [docs] |
| O-K9 | How the fence is tested in-repo. A child-process helper parks a publish before its put (`failpoints.rs`). A DST oracle also runs, but its actors share one process registry; the RFC says this exercises the check, not the fence between two processes. | [docs] |
| O-K10 | Other in-repo instruments:<br>• RFC 0031, comparative cost harness (draft, not started): two builds × two access paths.<br>• RFC 0032, adversarial correctness harness (draft, not started): write-cut sweeps that kill a child process, op-sequence fuzzing, parser fuzzing, scoped schedule exploration.<br>• RFC 0037, deterministic simulation (accepted, in progress).<br>• RFC 0039, end-to-end benchmark (accepted, in progress).<br>• Graph shallow clone RFC (draft, in progress), whose first user is that benchmark. | [docs] |
| O-K11 | Open issues on branching:<br>• [#642](https://github.com/ModernRelay/omnigraph/issues/642): fork and delete work grows with the number of live sibling branches (0.10.0, a 121-table catalog, MinIO with 17 ms added per request).<br>• [#643](https://github.com/ModernRelay/omnigraph/issues/643): merges into independent targets serialise behind graph-wide guards.<br>• [#1355](https://github.com/ModernRelay/omnigraph/issues/1355): branch create and delete return 413 while an export is in flight.<br>• [#1094](https://github.com/ModernRelay/omnigraph/issues/1094): cleanup leaves a table version's manifest readable after deleting its files. | [gh] |
| O-K12 | Contribution rules. Issues are the only inbound channel. A pull request must link an accepted issue or an accepted RFC, unless it is trivial. An RFC is written only after maintainers agree to one ([CONTRIBUTING.md](https://github.com/ModernRelay/omnigraph/blob/9fb5b48e65d09db5ca8206ced437a0e4ec07cef6/CONTRIBUTING.md)). | [docs] |

**What Witnessmark adds to the in-repo instruments.**

1. **A second engine.** It measures another engine's branching primitive, FalkorDB `GRAPH.COPY`, on the same host and the same graph shape.
2. **A real stale writer from a previous epoch.** It pauses whole test containers at chosen points in a write and performs a real failover to a second server, against a real object store. Write cuts that stop a child process cannot produce a writer that resumes later, and a DST whose actors share one registry does not model one.
3. **Many independent clients.** Separate client sessions drive the server over HTTP; each
   thread owns its connection, and no connection is shared across threads.

## 2. Workload model

These are specifications, not source. The `.pg` and `.gq` files are written in M4, against the documentation at the pinned commits.

### 2.1 Types

| Type | Kind | Properties and constraints | Purpose |
|---|---|---|---|
| `Agent` | node | `id: String @key` | claimants |
| `Skill` | node | `id: String @key` | eligibility |
| `Task` | node | `id: String @key`; `state`: open, claimed or done | the contested resource |
| `HasSkill` | edge `Agent → Skill` | none | eligibility |
| `Needs` | edge `Task → Skill` | none | eligibility |
| `HeldBy` | edge `Task → Agent`, `@card(0..1)` | `from_seq: I64`, `until_pt: I64`, `rw: String` | the lease; the schema itself allows at most one live holder per task |
| `Entry` | node | `id @key`, `seq: I64`, `rule: String`, `hash: String`, `prev: String`, `ts: I64` | padding to reach I6 graph sizes |
| `Next` | edge `Entry → Entry`, `@card(0..1)` | none | the padding chain |

**Lease history choice (F2).** The workload uses choice (b): the runner derives
`lease_records` from the `HeldBy` rows observed at one server snapshot and the
claim operations in history. Omnigraph exposes an opaque `graph_commit_id`, not
an ordered graph-commit sequence, so every live record retains that id as
`observed_graph_commit_id` and receives a deterministic harness observation
ordinal as `observed_order`. `from_seq` is the harness claim ordinal written on
the edge; `until_seq` is absent for a live record. These values are not presented
as native commit order. O2/O3 do not release a lease, so any two acknowledged
leases would both be live intervals and I1(d) remains decidable. This choice was
confirmed after the stable pin refused an attempted option-(a) release because
one mutation may not mix updates and deletes [measured: Part 1 query smoke,
2026-11-15] [code: `targets/03-omnigraph/witnessmark_omnigraph/engine.py`].

**Padding shape.** n `Entry` nodes and n `Next` edges form a log-like chain. The shape is close to the one behind the published FalkorDB numbers (equal node and edge counts, log-like properties; master §7.2). The S28 band therefore applies only approximately.

### 2.2 Queries and mutations

| Name | Does |
|---|---|
| `q_task` | Reads a task's state, with the response's `graph_commit_id`; `q_task_holder` reads its at-most-one holder and the `HeldBy` lease fields. A final-state dump passes the same `graph_commit_id` as the `snapshot` parameter to the holder query, so both describe one state. The pinned [query](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/queries/index.md) and [traversal](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/queries/traversal.md) guides do not document an optional traversal/projection that can return both when no holder exists [docs] [unmeasured: O2]. |
| `m_claim_cond` | Sets `state = claimed` and inserts `HeldBy`, under `--if-commit` (over HTTP, the conditional route) |
| `m_claim_card` | Inserts `HeldBy` with no condition, relying on `@card(0..1)` |
| `q_live` | Counts `HeldBy` per task |
| `q_eligible` | Traverses `Agent → HasSkill → Skill ← Needs ← Task`; compared with the same Cypher on FalkorDB and Neo4j (I4) |
| `m_ledger` | Appends an `Entry` with the next `seq` (the I6a ledger) |

**No-match semantics (F3).** Both claim mutations contain an `update Task ...
where state = "open"` followed by unconditional inserts. A zero-row update does
not skip later statements: the inserts run. On a second `m_claim_card`, the
`HeldBy @card(0..1)` check rejects the entire mutation and neither the edge nor
the preceding task update publishes. The HTTP envelope is status 400, code `bad_request`,
message `@card violation ...`, and disposition `effects: unknown`; the client
maps that documented constraint message to the definite typed refusal
`CardinalityViolation` [measured: `m4-part1-v0.15.0-local-20261115` and
`m4-part1-edge-b2dbaff-local-20261115`]. The edge pin produced the same result
[code: `targets/03-omnigraph/witnessmark_omnigraph/client.py`].

## 3. Scenarios

### O1. Branch creation cost and reader gap, against `GRAPH.COPY` (I6c, I6a, I6b)

- **Axes.**
  - n ∈ {32k, 128k, 512k} nodes, each with n edges.
  - s ∈ {0, 4, 16, 64} live sibling branches (#642's axis). GNOMON makes four or five branches per decision.
  - Storage: local filesystem, MinIO, and MinIO with 17 ms added per request.
- **Omnigraph side.** `omnigraph-server` serves main. Each branch create runs under load:
  - a closed-loop reader on main (`q_task`), with every completion recorded;
  - optionally, a closed-loop writer on main.

  Measured: creation time t(n, s); the stall, meaning the longest gap between reader completions during creation, minus the baseline gap; reader p99 during creation against before; object-store requests and bytes, in separate matched runs (master §6.5); the server's resident-memory delta; delete time; and the time to merge an unchanged branch.
- **FalkorDB side.** `GRAPH.COPY` of a graph with n nodes, under load:
  - a reader on the source graph;
  - a reader on an unrelated graph, which shows a server-wide stall;
  - a writer on an unrelated graph.

  Measured: copy time, stall, resident-memory delta, AOF bytes, and `GRAPH.DELETE` time.
- **Copy weight.** w(n) for GNOMON's decision cycle: create, apply one claim, score with one read, discard. A decision with four candidates makes five such cycles.
  The M4 reports give the full cycle time `t_cycle` in milliseconds [measured:
  `20261115T172253Z-0adb5788`]. Master §5.6 defines the copy-weight ratio
  as `t_snapshot / t_cycle`, which M4 leaves [unmeasured].
- **I6a.** Create a branch while `m_ledger` appends at a fixed rate. The branch must hold a gapless prefix of the ledger.
- **I6b.** Writes on the branch must be invisible on main, and the reverse, until a merge.
- **Runner.** Padding is loaded through the strict bounded NDJSON route in
  4,096-entity commits. For every `(n, s)` cell, three create/delete warm-ups
  precede five measured repetitions. One closed-loop `q_task` reader owns its
  own connection; object-store request counts are taken in a separate matched
  proxy repetition [code: `targets/03-omnigraph/witnessmark_omnigraph/part2.py`].
  **Connection model (method change in M5).** M4's O1, and the O1 runs of
  batch `m5b-20261115T230235Z`, opened a new TCP connection for every request
  of every closed-loop load and closed it after the reply [code:
  `targets/03-omnigraph/witnessmark_omnigraph/client.py` @ `2a02bd8` and
  `6a15b9c`]. From `f7ae8f2` on, each load (the main reader, and since M5 the
  unrelated reader and writer) keeps one HTTP/1.1 connection. The change
  followed host port exhaustion in batch 2 (§14). A read whose kept connection
  the server closes before replying is sent once more on a fresh connection.
  The dropped attempt is its own `history.jsonl` record (outcome unknown,
  error `kept_connection_dropped`), and the retry is a second record. Each
  sample's `read_retries` counts them during the create window and over the
  whole sample. A retried read completes only after its second attempt, so
  the stall gaps include the drop. A dropped write is an unknown outcome and
  is never sent again. The manifest records the model as `load_connections`.
  Reader latencies and stalls from the two models are not directly
  comparable: a kept connection skips the TCP handshake on every read
  [inference].
  **I6a and I6b controls** run at the end of each curve and, from batch `m4e`, alone
  (`wm_omnigraph.py i6`). The I6a branch is cut once five ledger appends have
  landed and the others continue. The first version cut it after a fixed 40 ms, which on
  a slow store was before the first append: all six O1 runs of batch `m4d` show an empty
  prefix, trivially gapless, so I6a was not exercised there. Every report states the
  prefix length, and an empty prefix is shown as not exercised.
- **Expected.**
  - FalkorDB: inside the S28 band [ours].
  - Omnigraph: [unmeasured]. The hypothesis [inference, from #642's description of lazy forks] is that creation time barely depends on n, and grows with s and with catalog width.

### O2. Fifty agents claim on main (I1 Form A, and the cost of false conflicts)

- **O2a, conditional claims on one task.**
  - 50 agents, each a thread with its own HTTP connection, read the task (`q_task` plus the commit id) and submit `m_claim_cond`. A barrier releases them together. T = 20.
  - Expected [docs]: exactly one success and 49 `precondition_failure` replies. After re-reading, all 50 agents see the same holder.
  - Checked: I1 Form A, rules (a) to (d).
- **O2b, conditional claims on disjoint tasks.** The sweep below was declared by
  the maintainer on 2026-11-16, before any O2b batch ran (master §10).
  - **Sweep.** N agents claim N different tasks, N ∈ {1, 2, 5, 10, 25, 50}. N = 1 is the no-contention baseline.
    Each agent is a thread with its own `OmnigraphClient`, released together by a barrier, as in O2.
  - **Policy** (re-read and decide again, never retry blindly
    [docs: [mutations/conditional.md](https://github.com/ModernRelay/omnigraph/blob/9fb5b48e65d09db5ca8206ced437a0e4ec07cef6/docs/user/mutations/conditional.md),
    the page O-K3 cites]). An agent reads its task with `q_task` and takes the graph commit id from the response.
    It submits `m_claim_cond` on that commit id. On `precondition_failure` it reads again and resubmits,
    until the claim succeeds or it has submitted 200 claims. A task that no longer reads as open, any other
    refusal, a failed read and an unknown outcome each end that agent and are recorded.
  - **Measured per trial.**
    - Total attempts, where an attempt is one claim submission, and wasted attempts, meaning attempts minus the claims that succeeded (attempts minus N when every agent claims).
    - Attempts per agent: median and maximum.
    - Time until all N agents have claimed, from the first agent's first operation to the last acknowledgement.
    - Latency of each claim submission: p50 and p99. Read latency is recorded the same way.
    - Medians and interquartile ranges are reported over the measured repetitions.
  - **Protocol** (master §6.5). Three warm-up repetitions are discarded, then five are measured, for each N.
    The configurations are interleaved: each round runs every N once. Warm-ups are kept in the evidence, flagged
    `warmup`, and left out of the summary. The release spread, taken over each agent's first operation, is recorded
    for every repetition. No spread gate applies until Phase B sets Omnigraph's δ: the manifest records
    `spread_gate: {"state": "off", "gate_ms": null}`, and `--spread-gate-ms` turns the gate on and records it.
    Omnigraph and FalkorDB run one after the other, never together.
  - **Checked as well** (a sanity check, not the purpose). After each trial every task has exactly one holder,
    its own agent. An agent that did not finish its claim holds nothing, and one whose outcome was unknown may or
    may not hold its task. A violation is reported as a finding with its run id.
  - **FalkorDB side.** The same sweep and protocol with the naive guarded claim (master §7.6, `claim.state` naive)
    on N different `WMTask` nodes, with N sessions. Expected [ours: GNOMON S3]: every claim succeeds on its first
    attempt, serialised. It sends no read: the guard is part of the claim.
  - **Expected.** Omnigraph: [unmeasured]. The hypothesis [inference from O-K3] is that wasted attempts grow with N,
    because every publish invalidates every other agent's condition. FalkorDB: no wasted attempts.
  - **Label.** The result is the cost of documented behaviour, not a defect (master §10, §11.4). It shows what a
    branch-wide precondition costs on a workload with no logical conflicts.
  - **Command.** `wm_omnigraph.py costcurve` rather than `race --scenario o2b --sweep`. The race command runs one
    operation per client for T trials at one N, through the core runner, and judges an invariant. O2b has several
    operations per agent, sweeps N and has no verdict, so it needs its own loop. It uses the same barrier
    pattern, and core stays unchanged. `costcurve --engine omnigraph --build <build> --storage <storage>` runs the Omnigraph
    side, `costcurve --engine falkordb` the FalkorDB side, and `--smoke` runs N ∈ {1, 2} with one warm-up and one
    measured repetition, recorded in the manifest.
  - **Evidence.** Omnigraph: `evidence/omnigraph/<build>.<storage>/o2b.disjoint_claims.sweep/<run_id>/`.
    FalkorDB: `evidence/falkordb/o2b.claim_state_disjoint.sweep/<run_id>/`, its own run with its own four
    files, next to the other FalkorDB baselines. The O1 FalkorDB curve sits inside the Omnigraph manifest
    and has no history, so it is not the pattern here. Every claim and read is a history record (phase `race`, kind `claim` or `read`,
    outcome `ok`, `fail` or `unknown`, error type `precondition_failure` where it applies), and fixture and observation
    calls are `setup` and `observe` records from client `admin`. `state/<k>.json` holds each trial's task rows with their
    holders. A trial is invalid under the master §6.3 gates (health, precondition digest, at most 5% unknown outcomes,
    no client fault, the spread gate when on).
    [code: `targets/03-omnigraph/witnessmark_omnigraph/costcurve.py:96,152,217,254,328,453,548` and
    `targets/03-omnigraph/wm_omnigraph.py:127–154` @ `6e2d1af`]
  - This is a cost curve, not a correctness test. It shows what a branch-wide precondition costs on a workload with no logical conflicts. On FalkorDB, disjoint guarded claims are serialised but never refuse one another.
- **O2c, claims enforced by the constraint.**
  - 50 agents submit `m_claim_card` for one task, with no condition.
  - Expected [docs]: exactly one `HeldBy` edge, 49 typed refusals, and no silent duplicate.
  - This confirms that the cardinality check is evaluated against the head each publish lands on.
- **Controls.**
  - Sequential: the 50 claims one at a time.
  - Negative: the same race on FalkorDB 6.0.4, using a naive guarded Cypher claim.
  - Positive: Neo4j 5.26.2 with the naive claim (master §6.2).

**Runner wiring.** The O2 adapter gives each client a distinct
`OmnigraphClient` and HTTP connection. The core thread barrier releases
their requests together [code:
`targets/03-omnigraph/witnessmark_omnigraph/runner_scenarios.py` and
`core/witnessmark/runner.py`]. The O2 and O3 races will use this thread
runner on the Windows host (master §3.4) and the Omnigraph release-spread
gate calibrated in master §6.3.

**Precondition hook.** Before each trial the runner resets the engine,
rebuilds the fixture and digests `Scenario.precondition(state)` of what it
observed. The trial is valid only if that digest equals the sequential
control's [code: `core/witnessmark/runner.py:83–90,264` @ `9e755b6`]. The
default returns the full observed state
[code: `core/witnessmark/scenarios.py:42–44` @ `9e755b6`]. A scenario may
override it to leave out fields that change on every reset but carry no
logical state, and must list them. The Omnigraph task races (`_TaskRace`,
which O2a, O2c and O3 share) leave out two, because every fixture setup
publishes a new head even when the rows are identical:

- `snapshot`, the graph commit id of the observation;
- `observed_graph_commit_id` in each lease record.

What stays in the digest is the task rows, the holders, and each lease record's
id, task, agent, sequence numbers and order. The run still writes the full
state, commit ids included, to `state/<k>.json`
[code: `targets/03-omnigraph/witnessmark_omnigraph/runner_scenarios.py:17–25`
and `core/witnessmark/runner.py:144–145` @ `9e755b6`]. O2b needs no override: its
precondition digest covers only each task's id and state, and carries no commit id
[code: `targets/03-omnigraph/witnessmark_omnigraph/costcurve.py:417` @ `6e2d1af`].

### O3. One branch per agent, then merge (I1 at merge)

- **Setup.** 50 branches `agent/<i>`. On each, an agent claims the same task by inserting `HeldBy(task → agent_i)`.
- **Procedure.** Merge every branch into main one after another, then repeat concurrently from separate client threads (see O2 runner wiring).
- **Expected [docs].** The first merge lands. Every later merge reports a typed conflict, `CardinalityViolation` or a divergence conflict, and writes nothing. No merge picks a winner silently (O-K5).
- **Also measured.** Merge throughput against the number of live branches, reported as a curve (#643's axis).

### O4. Stale writer after failover: an acceptance test for the writer epoch fence (I1 and I2 across a failover)

- **Topology.** Two `omnigraph-server` processes, A and B, on one graph root, in separate containers. Storage is a shared local volume, then MinIO.
- **Planned sequence for the epoch-fence test.**
  1. A serves main and holds its writer epoch. A client asks A to write.
  2. The fault injector pauses A's container (`docker pause`) at one of three phases:
     - p1, before staging;
     - p2, after staging and before publish;
     - p3, during publish retries.

     A seeded schedule picks the phase. It uses server-side progress markers where they exist, and otherwise a declared sweep of time offsets across the write.
  3. B starts and becomes main's writer the documented way, by acquiring the lease and claiming the epoch. In variant (b), B also publishes P_B.
  4. The fault injector resumes A (`docker unpause`), and A carries on with its write.
- **What M4 ran.** The recorded phase names are labels for fixed offsets.
  For p1 the runner pauses before starting the write thread (`-1.0` sentinel).
  For p2 and p3 it requests the pause 1 ms and 5 ms after starting the thread,
  respectively [measured:
  `20261115T183001Z-3dcbea3c`, `20261115T184233Z-3a4a4f31`,
  `20261115T184523Z-2ae7e967`]. The runner records the seed but does not use it
  to schedule pauses and captures no server progress markers [code:
  `targets/03-omnigraph/witnessmark_omnigraph/part2.py:725` @ `8bc5fd3`].
  The actual write phase is unknown in p2 and p3, and the evidence cannot
  distinguish the two as write phases [unmeasured: O4].
- **Pass criteria on the edge build** [docs: writes.md and the RFC].
  - A's publish is rejected with `WriterFenced` and is not retried.
  - Nothing A staged is reachable from main's head, and A's staging is unreferenced and collectable.
  - B's publications are intact.
  - Until the rejection, A's reads return the snapshot from before the claim; afterwards they see B's rows. This is the RFC's stated freshness bound.
  - `branch list --detailed` shows a single epoch.

**What the pinned release can and cannot do (corrected after batch 1).** The edge
pin's troubleshooting guide says that no CLI command or HTTP route claims a
branch; only a program that embeds the engine can, through
`Omnigraph::claim_branch_writer`. An unclaimed branch stays at epoch 0 and accepts
every writer as before [docs: `docs/user/operations/troubleshooting.md#writer-epoch`
@b2dbaff]. At the pin the RFC still says `implementation: not-started`, and
`omnigraph-server`, `omnigraph-cli` and `omnigraph-cluster` contain no claim call
[code: `crates/omnigraph-{server,cli,cluster}/src` @b2dbaff, searched for
`claim_branch_writer`, `claim_writer_epoch` and `writer_epoch`]. The RFC's server
claim of `main` after admission is its rollout phase 3, not shipped
[docs: RFC "Rollout"]. **The documented way to engage the fence is therefore a step
this harness does not perform**, so no O4 cell can pass or fail the fence criteria.
That is a harness gap, not a property of Omnigraph, and it is listed as open.

O4 cells are classified from what happened:

- **NOT_EXERCISED**: the successor never became ready, or it did on the edge build
  but `main` was never claimed. On a local root the successor is refused because
  the admission lock is unleased and its documented transfer (stop the previous
  owner, then `cluster force-unlock` with the exact lock id) needs a terminal
  owner; a paused A is not terminal, and the harness did not force the unlock
  [docs: deployment.md "Writer topology"].
- **BOUNDARY**: a failover took place on v0.15.0. The stable release predates the
  fence, so its documented one-writer deployment rule is its only protection.

The outcomes (A's and B's writes, the integrity scan, `branch list --detailed`) are
recorded for every cell regardless of its label [code:
`targets/03-omnigraph/witnessmark_omnigraph/part2.py`, `classify_o4_cell`].
- **Baseline on v0.15.0, before the fence.** The same sequence documents the behaviour the RFC describes: a stale writer's publish can land while its head precondition holds (O-K7). It is reported as BOUNDARY, because the deployment rule is documented, and not as FAIL.
- **Boundary probes on the edge build.** After the failover, A runs branch create or delete, cleanup, or optimize. The RFC puts all of these outside the fence (O-K8). The run records what happens, then checks integrity:
  - every object main's head references exists;
  - the graph opens;
  - a full scan succeeds.

  These probes, the several-failovers variant and the simultaneous-claims variant all need a claimed epoch. They are declared and **not implemented in this harness**; M4 reports them as NOT_EXERCISED, with the reason.
- **Variants.**
  - A paused for longer than the admission or lease timeout; the RFC says no timeout closes the gap.
  - Several failovers in a row.
  - A and B claiming at once. Expected: one claim succeeds, and a single epoch is listed.

### O5. Read your writes across processes (I3)

A write acknowledged by server A is read back by a second process, either the CLI or another server, on the same root. The run measures the staleness window, on both builds.

The implemented local-root control cleanly stops A after its acknowledgement,
starts server B on the same root, and polls B with `q_task_holder`; the measured
window begins at A's acknowledgement and includes process turnover [code:
`targets/03-omnigraph/witnessmark_omnigraph/part2.py`].

### O6. Traversal parity (I4)

`q_eligible` and `q_live` run on identical data, in Omnigraph and as Cypher on FalkorDB and Neo4j. Each result is classified as identical, rejected, or silently different.

### Part 1 controls

Fresh local roots on both pinned builds applied `schema.pg`, validated the
cluster configuration and executed all 11 declarations in `queries.gq`.
O2a, O2c, sequential O3 and O6 then met their expected states with 50 clients
on both builds; O3's 49 losing merges were typed `CardinalityViolation`
[measured: `m4-part1-v0.15.0-local-20261115` and
`m4-part1-edge-b2dbaff-local-20261115`]. The M1 claim controls also reproduced
their calibration: FalkorDB's naive guarded claim had 0/20 violating trials,
while Neo4j's naive claim had 20/20 [measured:
`m4-part1-control/20261115T143907Z-81158dcd` and
`m4-part1-control/20261115T143905Z-022d7057`].

## 4. Environment and pins

| Component | Pin |
|---|---|
| Omnigraph v0.15.0 | Source commit `373834b4c1c4b29cf0ddd64bee9565f98c60cc26`; official `omnigraph-linux-x86_64.tar.gz` SHA-256 `d7312ce49abca47a6bb47956b6987d32f650fa91678be1abd10e02824937bb15`; local image `witnessmark/omnigraph:v0.15.0`, digest `sha256:97d4950250b20019a80b03c8fd52cf52aa6243a86058a54895ba2772f15a2159` [measured: Docker build output, 2026-11-15]. |
| Omnigraph edge-20261113-b2dbaff | Source commit `b2dbaff7584eb849a98fa139876e0ae474e929ea`; official `omnigraph-linux-x86_64.tar.gz` SHA-256 `6b5b449cd4c292eae37ebd8d61a667b293714a5ad573b43a97a2299607297b8d`; local image `witnessmark/omnigraph:edge-b2dbaff`, digest `sha256:b7b8edac24ff8915346cee19eb85ac89c7aeaea6a8069d68410dcbc90e266792` [measured: Docker build output, 2026-11-15]. |
| Image build | `targets/03-omnigraph/docker/Dockerfile` uses digest-pinned Debian trixie-slim `sha256:a72b4433de1cf7d6bae0c4cee74d0547f58601a643b3375f070c51600d63b6b2` and installs the distribution's `ca-certificates` (20250419+deb13u1), as upstream's own Dockerfile does: without a trust store the binaries cannot build their S3 client and every S3 root fails with `storage_root_invalid`, even for a plain-HTTP endpoint [measured: MinIO smoke runs, `.state/scratch/m4-p2-smoke.json`, before and after]. The two image digests above are the rebuilt ones; batch 1 ran on the earlier, certificate-less images `sha256:32caa4e848b2…` (v0.15.0) and `sha256:9fd617ad5d75…` (edge). `build.ps1` downloads only the two pinned release archives, verifies each checksum, and labels the image with its exact source commit [code: `targets/03-omnigraph/docker/`]. The published-binary alternative is used, so a Rust toolchain and `protobuf-compiler` are not part of this image path. |
| MinIO | Built locally from MinIO's official, GitHub-verified signed tag `RELEASE.2025-09-07T16-13-09Z`, which dereferences to commit `07c3a429bfed433e49018cb0f78a52145d4bedeb`. `Dockerfile.minio` verifies that dereference before compiling with the release's own `buildscripts/gen-ldflags.go`; its Go and Debian stages are pinned to `sha256:79390b5e5af9ee6e7b1173ee3eac7fadf6751a545297672916b59bfa0ecf6f71` and `sha256:734a72b3d6142a71993b4bc580ca01d8ca687f77a2c422d96a961d3376b179bc`. M4 used the local build tagged `witnessmark/minio:RELEASE.2025-09-07T16-13-09Z`. Its local image ID is `sha256:5c9f6e9b19cdd3c333900e5102b196bfdb2e19f3e25674bfa0cef924e67dc899` (verified by `docker image inspect`, 2026-11-16). The configured digest in the M4 manifests matches this ID [measured: `20261115T173716Z-d303435d`, `20261115T181001Z-adf60896`]. `minio --version` reports the exact tag, commit and Go 1.24.2 [code: `targets/03-omnigraph/docker/Dockerfile.minio`] [measured: source build and loopback readiness smoke, 2026-11-15]. |
| Delay proxy | Standard-library forwarding proxy `core/witnessmark/proxy.py`; fixed 17 ms before each forwarded request, matching #642's method. `GET /__witnessmark__/counts` returns request count, request bytes and response bytes per HTTP method; `POST /__witnessmark__/reset` starts a matched repetition from zero. Its control calls are not counted. M4 used the local build tagged `witnessmark/proxy:17ms`. The rebuilt proxy's local image ID is `sha256:a865395be1e245d04d4e0b5a8bcc0813272a8e056f18b2cd94cb5a7230fc3e23` (verified by `docker image inspect`, 2026-11-16). The Python base is digest-pinned at `sha256:3fe1a0b6c2d6b2ebb572906cdabeca75aeb558c0c17db5ffefbcf8094871c32b` [code: `targets/03-omnigraph/docker/Dockerfile.proxy:1` @ `69d0cd3`]. It runs only in separate matched repetitions, never timing repetitions. Its first build rewrote the `Content-Length` of every `HEAD` reply to 0, so the object-store client saw empty objects (`Range started at 0 and ended at 0`); a reply to `HEAD` now keeps the upstream length (`core/tests/test_proxy.py`) [code: `core/witnessmark/proxy.py`] [measured: loopback MinIO smoke, 2026-11-15]. Rebuild with `docker/build-proxy.ps1` when the pinned local image is missing. A rebuild yields a new image ID. Update the digest in `compose.yml` and `part2.py` together [code: `targets/03-omnigraph/docker/build-proxy.ps1:1–11` @ `29356b0`]. |
| S3 settings and readiness | `compose.yml` passes `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION=us-east-1`, `AWS_ENDPOINT_URL_S3`, `AWS_S3_FORCE_PATH_STYLE=true` and `AWS_ALLOW_HTTP=true` for the local, disposable endpoints [docs: [storage.md, "S3 configuration"](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/concepts/storage.md#s3-configuration), [deployment.md](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/deployment.md#s3-compatible-storage)]. The binary derives plain-HTTP transport from the endpoint scheme and refuses an `AWS_ALLOW_HTTP` that disagrees [code: `crates/omnigraph-storage/src/binding.rs` L128 and L338–342@b2dbaff]. The harness waits on `GET /readyz`, never `/healthz`: the listener opens before graphs load, and a data request sent in between returns 503 `graph_unavailable` [docs: [deployment.md, "Use `GET /healthz`…" paragraph](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/deployment.md)] [code: `targets/03-omnigraph/witnessmark_omnigraph/part2.py`]. The S3 cluster lease is the documented 30 s default everywhere except O4, which shortens it to 2 s so that a paused owner can be replaced within the test; each run records `cluster_lease_seconds`. An owner stops every storage write once no heartbeat is answered for two thirds of a lease [docs: [storage-failures.md](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/operations/storage-failures.md#restart-after-a-failure)], and with the 2 s lease the proxy run of batch `m4c-20261115T165831Z` failed at 205,824 of 512,000 padding edges with `storage mutation admission is closed` [measured: `20261115T171130Z-e052669e`]. |
| FalkorDB | 6.0.4 by digest (master §7.2). The O1 `GRAPH.COPY` curve runs with `appendonly yes` and `appendfsync always`, the conditions S28 was measured under, and restores the container's own settings afterwards; the run records both. Batch 2's first attempt ran on the baseline's `appendonly no` and came out 61%, 49% and 57% faster than S28 at 32k, 128k and 512k (64.3, 279.2 and 1,025.1 ms against 165, 546 and 2,400), outside the ±50% band at two of three sizes, so the batch stopped [measured: `20261115T164756Z-236def5c`]. A scratch check of the same curve under S28's persistence gave 106.9, 359.3 and 1,600.3 ms, inside the band at all three [measured: scratch, not part of a batch]. The difference is the persistence setting [inference from that check]. |
| Neo4j | 5.26.2 (master §7.3) |
| Clients | The core runner: standard-library HTTP for Omnigraph and Neo4j, RESP for FalkorDB |

**M4 image provenance.** MinIO and the delay proxy were selected by tag
(`witnessmark/minio:RELEASE.2025-09-07T16-13-09Z` and `witnessmark/proxy:17ms`)
[code: `targets/03-omnigraph/docker/compose.yml:42,58` @ `2a02bd8`].
The proxy run manifest records MinIO's tag and a digest field, and omits the
proxy component [measured: `20261115T173716Z-d303435d`,
`20261115T181001Z-adf60896`]. The digest field comes from a constant in the
harness. The proxy tag in Compose is the record of the image selected at run
time [code: `targets/03-omnigraph/witnessmark_omnigraph/part2.py:41,200` and
`targets/03-omnigraph/docker/compose.yml:58` @ `2a02bd8`].

**M5 image pins.** Compose uses the local `repo@sha256` references for MinIO
and the proxy, as it does for the server. Docker's local image index resolves
both references to the image IDs in the table. Compose uses
`pull_policy: never`, and a missing local image stops startup
[code: `targets/03-omnigraph/docker/compose.yml:42–58` @ `fe13385`].
The manifest records the MinIO image ID and whether it is in use. Proxy runs
also record the proxy image ID
[code: `targets/03-omnigraph/witnessmark_omnigraph/part2.py:50` @ `fe13385`].

## 5. Checks

| Check | How |
|---|---|
| I1 Form A | Built from `HeldBy` and the acknowledged replies. Final task and holder reads use one snapshot; the runner derives live lease intervals and retains the opaque server commit id plus its own observation order [code: `targets/03-omnigraph/witnessmark_omnigraph/engine.py`] [measured: the two Part 1 control run ids in §3]. |
| I6a | The ledger prefix is gapless |
| O4 integrity | The graph opens; a full scan succeeds; every object the head references exists; error types match the documentation |
| I4 | Normalised row multisets, compared across the three engines (master §5.4) |

## 6. Deliverables

| ID | Deliverable |
|---|---|
| B1 | Branch-cost curves (creation time, stall, bytes, resident memory) against n, s and storage, next to `GRAPH.COPY`'s curve |
| B2 | Claim-race tables for O2a to O2c and O3, and the O2b cost curve |
| B3 | The fence acceptance matrix: phase × variant × storage × build |
| B4 | One single-file repro for each FAIL |
| Drafts | Kept in `drafts/`, never committed: comments for #642 and #643 with curves on current builds, and a note offering B3 to the maintainers of the fence work |

## 7. Contribution plan (non-competing)

1. **No pull requests.** Issues are the only inbound channel, and a pull request needs an accepted issue or RFC (O-K12). Witnessmark opens no pull request here.
2. **Data on open issues.** Post measured data, stated factually, on the open issues it bears on: #642, #643, #1355 and #1094.
3. **The fence.** If O4 finds a FAIL on the edge build, file a bug with a minimal repro: two containers, one pause, one failover. If O4 passes, report it in the public artefact, and offer it to the maintainers in a short note (draft first) as external, process-level confirmation of #1350.
4. **Benchmarks against FalkorDB** follow master §11.5: the maintainers of both Omnigraph and FalkorDB see the numbers first.
5. **If a pull request is ever invited,** use the commit types in their CONTRIBUTING; there is no `chore`.

## 8. Exit and drop rule

- **Clean results.** If O4 passes and O1 shows small stalls that do not grow with n, publish both as positive results with credit, and stop.
- **Off-band baseline.** If the FalkorDB side of O1 falls outside the S28 band, stop and explain the environment before anything else (master §6.5).

## 9. Open questions

### Answers from the pinned documentation (2026-11-15)

1. **Admission, leases and failover.** A cluster has one exclusive admission
   lock shared by the server, direct writes, deployments, branch controls and
   maintenance. A local-filesystem lock is unleased and has no timeout or safe
   automatic takeover: after establishing that the previous owner's graph and
   control-store work is terminal, an operator uses the exact lock id to unlock
   it. An S3 server lock is leased. Its owner writes heartbeats below
   `__cluster/lease/` every one third of the lease, stops storage writes after
   two thirds of a lease without an answered heartbeat, and a successor takes
   over after one and a half leases of silence. The lease defaults to 30 seconds,
   is configurable from 2 through 600 seconds with
   `OMNIGRAPH_CLUSTER_LEASE_SECONDS`, and therefore makes the default takeover
   wait about 45 seconds. Direct CLI and deployment locks are unleased even on
   S3 and require exact-id recovery. [docs: [deployment](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/deployment.md#writer-topology),
   [storage failure and restart](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/operations/storage-failures.md#restart-after-a-failure)]

   The writer-epoch RFC designs for the server to claim `main`'s persistent epoch
   after it wins cluster admission and before it serves, and for a successor claim
   to increment it, so that a stale writer from the previous epoch is refused with
   `WriterFenced` at its next publication. **That server claim is the RFC's rollout
   phase 3 and is not in the edge pin**: the pinned troubleshooting guide says no CLI
   command or HTTP route claims a branch, and the server, CLI and cluster crates
   contain no claim call (corrected 2026-11-15 after batch 1; the earlier reading of
   the RFC's design text as shipped behaviour was wrong). v0.15.0 has the admission
   lock but predates the fence. [docs:
   [writer-epoch RFC](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/rfcs/2026-11-09-writer-epoch-fence.md#main-and-the-lease),
   [troubleshooting](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/operations/troubleshooting.md#writer-epoch),
   [write protocol](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/dev/writes.md#writer-epoch)]

2. **Object-store request counts.** The documented server surface exposes
   health, readiness, logs and traces, but no object-store request counter or
   metrics route. O1 therefore uses a counting proxy in separate matched runs,
   as required by master §6.5. [docs: [server route families](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/operations/server.md#route-families),
   [server observability](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/operations/observability.md)]

3. **HTTP routes and payloads.** Every protected call carries
   `Omnigraph-Http-Api: 0.14`. Inline reads use
   `POST /graphs/{graph_id}/query` with body `{query, name?, params?, branch?,
   snapshot?, settings?}`. Unconditional inline writes use
   `POST /graphs/{graph_id}/mutate` with `{query, name?, params?, branch?,
   settings?}`. A conditional inline write uses
   `POST /graphs/{graph_id}/mutate/if-graph-commit` with the same mutation body
   and the raw commit id in the required `Omnigraph-If-Graph-Commit` header,
   not in the body. A stored conditional mutation uses
   `POST /graphs/{graph_id}/queries/{query_name}/if-graph-commit` and the same
   header. Ordinary mutation routes reject that header instead of ignoring it.
   [docs: [HTTP conditional mutations](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/operations/server.md#conditional-mutations),
   [edge OpenAPI](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/openapi.json)]

   Dedicated branch routes are: create,
   `POST /graphs/{graph_id}/branches` with `{name, from?}` or
   `{name, from_commit?}`; delete,
   `DELETE /graphs/{graph_id}/branches/{branch_name}` with no body; list,
   `GET /graphs/{graph_id}/branches` with optional `?detailed=true`; and merge,
   `POST /graphs/{graph_id}/branches/merge` with `{source, target?,
   delete_branch?, dry_run?, as_commit?, settings?}`. `from` and `from_commit`
   are mutually exclusive, `target` defaults to `main`, and `source` is required.
   The same route and request shapes are present at both test pins. [docs:
   [stable OpenAPI](https://github.com/ModernRelay/omnigraph/blob/373834b4c1c4b29cf0ddd64bee9565f98c60cc26/openapi.json),
   [edge OpenAPI](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/openapi.json)]

4. **Guards in GQ.** `.gq` can express a row-local guarded update in one
   statement: `update Type set { ... } where ...`; the predicate may read that
   type's properties, ids, parameters and `now()`. It cannot use a binding,
   traversal, aggregate or search call in the mutation `where`. A guard against
   the graph state that a prior read observed is not GQ syntax: it uses
   `--if-commit` or the HTTP header and conditional route above. [docs:
   [mutation statements](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/mutations/index.md#statements),
   [conditional mutations](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/mutations/conditional.md)]

5. **S3 conditional publication.** A graph-content write stages detached Lance
   commits, then makes them visible together with one conditional
   `__manifest` publication. The next manifest version is created only if
   absent: local storage uses a failing hard link, while S3 sends
   `If-None-Match: *`; updates of reused control objects use `If-Match`. An
   ambiguous manifest request is re-issued unchanged up to four times with
   about three seconds of pauses in total, then its attempted version is read
   back to distinguish this commit, another commit, or an unknown outcome.
   [docs: [write protocol](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/dev/writes.md),
   [cross-process write RFC](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/rfcs/2026-10-16-graph-access-serving-and-cross-process-writes.md#engine-control-facts-on-the-version-cas),
   [storage failures](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/operations/storage-failures.md#publication-outcomes)]

   The storage guide says every S3 binding requires correct `If-None-Match` and
   `If-Match` behavior, says the project's suite qualifies RustFS, and requires
   every other S3-compatible service to be qualified before production. It does
   not settle MinIO's behavior. That remains [unmeasured: O4 on MinIO]. [docs:
   [S3 configuration](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/concepts/storage.md#s3-configuration)]

The catalog-width question remains [unmeasured: O1]. Per the declared design,
the first O1 curve decides whether to add width as an axis.

## 10. Results (M4)

**Provenance.** Six batches on this host, including one false start (Windows 11,
11th Gen i5-11320H, 8 logical cores, 23.8 GB, Docker VM 8 CPUs and 11.6 GB).
The manifests record clean trees [measured: `20261115T153548Z-45dc303e`,
`20261115T154356Z-9ebd8e7e`, `20261115T164756Z-236def5c`,
`20261115T165838Z-b4925bd5`, `20261115T172253Z-0adb5788`,
`20261115T183931Z-fa543284`]. The five linked reports regenerate from
`evidence/`. The findings cite the manifests directly where they use fields
beyond the report tables.

**Evidence layout.** All 37 M4 run directories lack `history.jsonl`, `state/`
and `REPRO.md`, a departure from master §9.1 [measured: the M4 run directories in
`evidence/omnigraph/`, including `20261115T153548Z-45dc303e` through
`20261115T184523Z-2ae7e967`]. The O4 operation records have no `inv` or
`ret` fields, and the fault actions have no timestamps [measured:
`20261115T183001Z-3dcbea3c`, `20261115T184233Z-3a4a4f31`,
`20261115T184523Z-2ae7e967`].

| Batch | Report | Harness commit | What it holds |
|---|---|---|---|
| `m4-20261115T153532Z` | — | `46adb1d` | false start with one planned-before-execution manifest, zero trials and no accompanying `ERROR.md` [measured: `20261115T153548Z-45dc303e`] |
| `m4-20261115T153804Z` | [evidence/M4_OMNIGRAPH_B1.md](../../evidence/M4_OMNIGRAPH_B1.md) | `46adb1d` | the first full batch: 13 commands, 7 failed on harness problems |
| `m4b-20261115T164749Z` | [evidence/M4_OMNIGRAPH_B2.md](../../evidence/M4_OMNIGRAPH_B2.md) | `48737aa` | stopped after one command: the FalkorDB sanity band was not met |
| `m4c-20261115T165831Z` | [evidence/M4_OMNIGRAPH_B3.md](../../evidence/M4_OMNIGRAPH_B3.md) | `8f7bb3b` | completed stable-local O1, then two failed O1 runs before the batch driver crashed [measured: `20261115T165838Z-b4925bd5`, `20261115T170604Z-7d473a53`, `20261115T171130Z-e052669e`] |
| `m4d-20261115T172246Z` | [evidence/M4_OMNIGRAPH.md](../../evidence/M4_OMNIGRAPH.md) | `2a02bd8` | the main batch: O1 on both builds and three storages, O4, O5; 13 of 13 commands exit 0 |
| `m4e-20261115T183929Z` | [evidence/M4_OMNIGRAPH_B4.md](../../evidence/M4_OMNIGRAPH_B4.md) | `8bc5fd3` | re-run of the I6 controls (6 runs) and O4 (4 runs), after two checks in `m4d` proved weak; 11 of 11 commands exit 0 |

**Batch history.**

| Batch | Cause | Where |
|---|---|---|
| `m4` (batch 1) | Seven runs failed on harness problems, none a finding. (P1) `UnboundLocalError` in the FalkorDB curve: `o1-stable-local`, after its Omnigraph curve had finished but before its manifest was written, so that curve's data was lost. (P2) every MinIO and proxy run, O1 and O4, both builds, failed with `storage_root_invalid`: the Omnigraph image had no CA bundle, which the binaries need to build their S3 client (`ca-certificates`, as upstream's Dockerfile installs). Fixed in `48737aa`, with two more found while proving it: the harness waited on `/healthz` before the graph had loaded, and the delay proxy rewrote the `Content-Length` of `HEAD` replies to 0 (`bfdec20`). The same commit made the O4 labels honest (below) | `m4b` |
| `m4b` | The FalkorDB `GRAPH.COPY` curve came in 61% and 57% below S28 at 32k and 512k (and 49% below at 128k) with the baseline's `appendonly no`. S28 was measured with `appendfsync always`; a scratch check under that setting gave 106.9, 359.3 and 1,600.3 ms, inside the band at all three. The curve now sets and records S28's persistence and restores the container's own (`8f7bb3b`). The batch stopped by rule, as master §6.5 says | `m4c` |
| `m4c` | Two problems. The 2 s S3 cluster lease that O4 needs for a fast takeover was applied to O1 as well; an owner stops all storage writes when no heartbeat is answered for two thirds of a lease, and the proxy run failed with `storage mutation admission is closed` part-way through loading 512k edges (`20261115T171130Z-e052669e`). Separately, the batch driver died printing a log line with a character its console encoding could not hold, so commands 4 to 13 never ran. Lease fixed in `2a02bd8`; the driver is untracked and was fixed under `.state` | `m4d` |
| `m4d` → `m4e` | Two checks did not check what they claimed. I6a: the branch was cut 40 ms after the ledger writer started, before its first append on a slow store, so all six O1 runs hold an empty prefix, which is trivially gapless. O4: the integrity scan went through the stale server, which stops itself after its admission is taken over, so every S3 cell read "not checked". Fixed in `8bc5fd3` | `m4e` |

**Commit `bfdec20` carries a `Co-Authored-By` trailer by mistake.** The instruction for this work is no attribution line; the trailer was added without noticing. It is kept rather than rewritten because the evidence records harness commit hashes, and an amend or rebase would change them. Every other commit since `0f22a9b` is authored by the maintainer alone, with no attribution line (audited with `git log` on 2026-11-15).

**Batch 1's failures are cited from its driver log.** Its failed commands are in `.state/scratch/m4-batch/m4-20261115T153804Z/driver.log` (kept locally, not committed). Exit codes in command order: `baselines-up` 0; `o1-stable-local` 1, `o1-stable-minio` 1, `o1-stable-proxy` 1; `o1-edge-local` 0, `o1-edge-minio` 1, `o1-edge-proxy` 1; `o4-stable-local` 0, `o4-stable-minio` 1, `o4-edge-local` 0, `o4-edge-minio` 1; `o5-stable-local` 0, `o5-edge-local` 0. The driver also wrote an `ERROR.md` for each failed command under `evidence/omnigraph/errors/`. Those notes recorded the host Python's path under the user's home folder, so they were moved out of `evidence/` unedited, to `.state/scratch/m4-batch/m4-20261115T153804Z/driver-errors/`, instead of being committed. The in-run `ERROR.md` files, which are redacted, stay in the run folders and are listed in the first report's "Runs that did not complete" table. The driver now redacts the command and tracebacks (batches 2 and 3 have their notes in `evidence/omnigraph/errors/`).

**MinIO failure in `m4c`.** The run stopped on the third 512k create with
`Remote end closed connection without response` [measured:
`20261115T170604Z-7d473a53`, accompanying `ERROR.md`]. The failure evidence
contains no server log [measured: `20261115T170604Z-7d473a53`]. The cause is unknown
[unmeasured: O1, server logs on failure]. Lease expiry is one possibility
[inference from the closed connections in `20261115T184233Z-3a4a4f31` and
the completed O1 curve under the 30 s lease in `20261115T173025Z-fc74457b`].

### Controls

Controls come before findings.

| Control | Result | Run |
|---|---|---|
| FalkorDB `GRAPH.COPY` against S28 (the exit criterion, master §12) | **met**: 95.3 ms against 165 at 32k (-42%), 441.7 against 546 at 128k (-19%), 1,820.0 against 2,400 at 512k (-24%); all inside ±50%. Run under `appendonly yes`, `appendfsync always`, the conditions S28 was measured under | `20261115T172253Z-0adb5788` (`m4d`) |
| I6a, ledger prefix (`m4e`, branch cut after 5 of 20 appends) | gapless and non-empty in 6 of 6 runs: 5 of 20 entries on the branch. `m4d` is superseded for I6a: its six runs show an empty prefix, so I6a was not exercised there | `20261115T183931Z-fa543284`, `20261115T183939Z-2b18faf7`, `20261115T183955Z-401500b4`, `20261115T184035Z-505c2756`, `20261115T184042Z-d51c234e`, `20261115T184058Z-df6399b2` |
| I6b, isolation (`m4d` and `m4e`) | held in 12 of 12 runs: a branch write was invisible on main and the reverse | same, and the six `m4d` O1 runs |
| Part 1 sequential controls (O2a, O2c, O3, O6; M1 claim controls) | met on both builds, as recorded in §3 before M4 | see §3 |

I6a at other branch points remains [unmeasured: I6a with a cut other than
after the fifth append].

### Results

| Scenario | v0.15.0 | edge-b2dbaff | Verdict |
|---|---|---|---|
| O1, create time, local root | 6.0 to 8.2 ms across n = 32k, 128k, 512k and s = 0, 4, 16, 64 siblings. Reader stall medians 0 to 0.66 ms [measured: `20261115T172253Z-0adb5788`] | 5.35 to 11.25 ms. Reader stall medians 0 to 0.75 ms [measured: `20261115T175653Z-12eb6ff6`] | OBSERVED, no consistent trend across n or s |
| O1, create time, MinIO | 36.2 to 70.9 ms. Reader stall medians 27 to 60 ms [measured: `20261115T173025Z-fc74457b`] | 37.4 to 88.6 ms. Reader stall medians 28 to 81 ms [measured: `20261115T180251Z-742224c3`] | OBSERVED, no consistent trend across n or s |
| O1, object-store traffic through the 17 ms proxy, one create + delete | 34 to 39 requests. GET response bytes 58,335 (32k, s=0) to 418,639 (512k, s=0), and 137,966 at 32k, s=64 [measured: `20261115T173716Z-d303435d`] | 34 to 37 requests. GET response bytes 58,667 to 421,977 at s=0 [measured: `20261115T181001Z-adf60896`] | OBSERVED, requests nearly constant, bytes grow with n and s |
| O1, cycle time (create, claim, score, discard, one sample per size) | Local 87.2, 90.0, 200.6 ms [measured: `20261115T172253Z-0adb5788`]. MinIO 248.1, 274.9, 578.8 ms [measured: `20261115T173025Z-fc74457b`] | Local 83.7, 115.1, 195.7 ms [measured: `20261115T175653Z-12eb6ff6`]. MinIO 2,111.2, 319.1, 576.7 ms [measured: `20261115T180251Z-742224c3`] | OBSERVED, full cycle times. The master §5.6 ratio is [unmeasured]. |
| O1, FalkorDB `GRAPH.COPY` [measured: `20261115T172253Z-0adb5788`] | The unrelated reader's median gap was 95.1, 441.7 and 1,819.8 ms at 32k, 128k and 512k. The unrelated writer's was 95.3, 419.2 and 1,799.0 ms. Delete medians were 8.2 to 8.9 ms. RSS after-minus-before medians were 3.6, 9.3 and 47.2 MB. Last-sample AOF file sizes were 50.8, 79.4 and 101.4 MB. | — | OBSERVED (I6c) |
| O4, local root | the successor never became ready in 6 of 6 cells (the local lock is unleased [docs]); A's write was acknowledged and present in 6 of 6; none missing (`20261115T184136Z-24a2c040`) | same, 6 of 6 (`20261115T184426Z-ba1673ab`) | NOT_EXERCISED (harness gap) |
| O4, MinIO, leased takeover (`m4e`) | The successor became ready in 6 of 6 cells. A had 6 unknown outcomes and none of its writes appeared in the scan through B. All 3 of B's acknowledged writes were present [measured: `20261115T184233Z-3a4a4f31`]. | Ready 6 of 6, A unknown and absent from the scan 6 of 6, B present 3 of 3 [measured: `20261115T184523Z-2ae7e967`]. | BOUNDARY (stable), NOT_EXERCISED (edge) |
| O5, read your writes, local root, second server | seen on the first poll; window 1,523.8 ms, including stopping A and starting B (`20261115T183504Z-eb41bb89`) | seen on the first poll; 1,334.6 ms (`20261115T183511Z-4d593c85`) | observed, 2 of 2 |

FalkorDB's sampled `aof_current_size` stayed near 101.4 MB across the five
512k repetitions in both `m4c` and `m4d`, with no sustained growth
[measured: `20261115T165838Z-b4925bd5`, `20261115T172253Z-0adb5788`].
The cause is unknown. AOF rewrite status was [unmeasured: O1].
The manifests also record before and after RSS samples for Omnigraph
[measured: `20261115T172253Z-0adb5788`, `20261115T175653Z-12eb6ff6`].

### O4 labelling, checked against the pinned docs

Batch 1 labelled every O4 cell BOUNDARY with the reason "the pinned server exposes no branch writer-claim route". The reason is true [docs: troubleshooting.md "Writer epoch" at `b2dbaff`; code: no claim call in `omnigraph-server`, `omnigraph-cli` or `omnigraph-cluster` at `b2dbaff`], but the label was a conclusion the cells did not earn. The documented way to engage the fence is a claim by an embedding program (`Omnigraph::claim_branch_writer`), and the RFC's server claim of `main` is its rollout phase 3, not shipped at the pin. The harness drives the published binaries and performs neither step. For a local root the documented ownership transfer (stop the previous owner, then `force-unlock` its exact lock id) is also a step the harness did not perform, because A was paused, not terminal. These are harness gaps, not boundaries of Omnigraph, so since `48737aa` the cells are classified from what happened:

- **NOT_EXERCISED**: the successor did not become ready (all local cells), or it did on the edge build but `main` was never claimed, so the fence acceptance criteria could not apply.
- **BOUNDARY**: only a real failover on v0.15.0, whose documented deployment rule is its protection.

No cell is a fence pass or a fence failure. The batch-1 BOUNDARY labels are marked "first-version label, superseded" in its report.

The O4 phase column in the reports carries only the fixed offset labels
described in §3. The seed is recorded but unused in scheduling. The recorded
actions cannot distinguish p2 from p3 as write phases [code:
`targets/03-omnigraph/witnessmark_omnigraph/part2.py:725` @ `8bc5fd3`]
[measured: `20261115T183001Z-3dcbea3c`, `20261115T184233Z-3a4a4f31`,
`20261115T184523Z-2ae7e967`].

### Findings

1. **Readers waited during both primitives in the tests that measured them.**
   On MinIO, across 60 creates per build, the median per-sample ratio of reader
   p99 during create to create time was about 1.05× on both builds. The median
   ratio of stall to create time was about 0.78× on stable and 0.79× on edge.
   The reader on `main` typically waited for most of the create, consistent with the
   read-view gate [docs: O-K1] [measured: `20261115T173025Z-fc74457b`,
   `20261115T180251Z-742224c3`]. The stall metric subtracts the median baseline
   gap and floors the result at zero [code:
   `targets/03-omnigraph/witnessmark_omnigraph/part2.py:316–336` @ `2a02bd8`].
   The local cell medians were below 1 ms [measured: `20261115T172253Z-0adb5788`,
   `20261115T175653Z-12eb6ff6`]. Within the short local create window the
   metric cannot resolve a stall shorter than the reader's normal gap
   [inference from the metric].

   The measured stall durations differ. MinIO cell medians ranged from 27 to
   81 ms, while the FalkorDB source reader, unrelated reader and unrelated
   writer each saw gaps close to the 95–1,820 ms copy times in the three
   size cells [measured: `20261115T173025Z-fc74457b`,
   `20261115T180251Z-742224c3`, `20261115T172253Z-0adb5788`]. FalkorDB's gaps
   are raw gaps during the copy. Omnigraph had one reader on `main`, with
   neither an unrelated-graph reader nor a writer in the test [code:
   `targets/03-omnigraph/witnessmark_omnigraph/part2.py` @ `2a02bd8`].
   MinIO and FalkorDB also ran under different storage and durability
   conditions [measured: `20261115T173025Z-fc74457b`,
   `20261115T180251Z-742224c3`, `20261115T172253Z-0adb5788`].
2. **Create time had no consistent trend across the tested graph sizes or
   sibling counts.** For example, edge on a local root at 128k rose from
   6.43 to 11.25 ms (about 6.4 to 11.3 ms) as live siblings went from 0 to 64
   [measured: `20261115T175653Z-12eb6ff6`, `20261115T172253Z-0adb5788`,
   `20261115T173025Z-fc74457b`, `20261115T180251Z-742224c3`].
   Through the 17 ms proxy, request counts changed little while GET response
   bytes increased with n and s [measured: `20261115T173716Z-d303435d`,
   `20261115T181001Z-adf60896`]. A wider catalog is [unmeasured: O1].
3. **The `m4e` MinIO takeovers left A with 12 unknown outcomes across both
   builds.** The replies were `internal` ("storage mutation was fenced while
   this request was in flight"), `service_unavailable`
   ("server operation admission is closed") or a closed connection. The scan
   through B found none of A's writes and all six of B's acknowledged writes.
   Both runs record an unclaimed epoch
   [measured: `20261115T184233Z-3a4a4f31`, `20261115T184523Z-2ae7e967`].
   An owner stops storage writes after two thirds of a lease without a
   heartbeat reply [docs: storage-failures.md @ `b2dbaff`]. The cluster lease
   is a likely explanation [inference from this rule and A's replies].
4. **In `m4d`, B built on A's acknowledged commit in the stable MinIO p2/b
   cell.** A published manifest v3 (commit ending in `FW31MY`). B's
   acknowledged v4 names A's commit as its `parent_commit_id`. They form
   one lineage on `main` with no fork or overwrite in the recorded commits.
   The scan through A failed [measured: `20261115T183001Z-3dcbea3c`]. A may
   have published before the pause took effect [inference from the 1 ms
   offset and the recorded lineage]. The run lacks the action timestamps
   needed to place A's publish relative to B's takeover [unmeasured: O4].
   In the matching `m4e` cell A had an unknown outcome and its write was
   absent from the scan through B [measured: `20261115T184233Z-3a4a4f31`].
5. **Cross-process visibility on a local root took 1.3 to 1.5 s** from A's
   acknowledgement to the first successful read on B. The window includes
   stopping A and starting B [measured: `20261115T183504Z-eb41bb89`,
   `20261115T183511Z-4d593c85`]. Visibility to a concurrent second reader
   is [unmeasured: O5].
6. **Storage admission closed during the `m4c` proxy load**
   [measured: `20261115T171130Z-e052669e`, accompanying `ERROR.md`]. That
   runner configured a 2 s lease [code:
   `targets/03-omnigraph/witnessmark_omnigraph/part2.py` @ `8f7bb3b`]. The
   completed O1 proxy run used a 30 s lease [measured:
   `20261115T173716Z-d303435d`].
7. **Run-to-run spread is [unmeasured] for the main batch's O1 and O5 build
   comparisons.** The main batch recorded one run per build and storage
   for those comparisons [measured: `20261115T172253Z-0adb5788`,
   `20261115T175653Z-12eb6ff6`, `20261115T173025Z-fc74457b`,
   `20261115T180251Z-742224c3`, `20261115T173716Z-d303435d`,
   `20261115T181001Z-adf60896`, `20261115T183504Z-eb41bb89`,
   `20261115T183511Z-4d593c85`].

**Credit.** The I6a prefix and I6b isolation controls held on both builds and
all three storage configurations [measured: `20261115T183931Z-fa543284`,
`20261115T183939Z-2b18faf7`, `20261115T183955Z-401500b4`,
`20261115T184035Z-505c2756`, `20261115T184042Z-d51c234e`,
`20261115T184058Z-df6399b2`]. In the 12 `m4e` MinIO leased-takeover cells,
all 12 of A's outcomes were unknown. Scans through B found none of A's
writes and every acknowledged write [measured: `20261115T184233Z-3a4a4f31`,
`20261115T184523Z-2ae7e967`].

## 11. Open questions and decisions after the M4 audit

### M5 evidence and diagnostics

The Part 2 commands write the §9.1 evidence layout under
`evidence/omnigraph/<build>.<storage>/<scenario>.<mode>/<run_id>/`.
`history.jsonl` records HTTP calls from the Omnigraph clients and readiness
and proxy probes. It gives fault actions the `nemesis` client and phase,
with monotonic and wall-clock timestamps. An unknown outcome has a null
`ret`. `REPRO.md` gives the redacted command, harness commit and dirty flag,
build, image digests and storage
[code: `targets/03-omnigraph/witnessmark_omnigraph/capture.py:50–145` @ `a064bb1`].

| Scenario | Final state in `state/<k>.json` |
|---|---|
| O1 curve | The detailed branch lists and commit IDs for the source graph and the unrelated graph after each size and sibling cell [code: `targets/03-omnigraph/witnessmark_omnigraph/part2.py:685` @ `9e755b6`] |
| Standalone I6 | The ledger sequences on main and the branch, plus the branch-only and main-only visibility results [code: `targets/03-omnigraph/witnessmark_omnigraph/part2.py:455` @ `a064bb1`] |
| O4 matrix | Branch heads, task and holder rows at the observed commit, and the eligible agents from the integrity scan [code: `targets/03-omnigraph/witnessmark_omnigraph/part2.py:740` @ `a064bb1`] |
| O4 clean-stop | A's Docker exit state, root admission status, and, if B starts, the branch heads, task and holder rows, and eligible agents read through B [code: `targets/03-omnigraph/witnessmark_omnigraph/part2.py:926` @ `9e755b6`] |
| O5 | The task read from B and the holder response from B's final visibility poll [code: `targets/03-omnigraph/witnessmark_omnigraph/part2.py:952` @ `a064bb1`] |
| O6 | Per-engine rows and read errors for the sequential control and the parity trial [code: `targets/03-omnigraph/witnessmark_omnigraph/part2.py:567` @ `9e755b6`] |

Each state file includes a digest. States above 5 MiB retain the digest,
total byte count, and bounded excerpts from the canonical JSON
[code: `core/witnessmark/evidence.py:64` @ `b274458`].

For failed or unexplained O4 cells, `run.json` lists the trial's
`logs/<k>-wm-omnigraph-a.log`, `logs/<k>-wm-omnigraph-b.log` and, on
MinIO, `logs/<k>-wm-minio.log`. The harness collects these before teardown,
restricts the capture to the trial window, redacts it and retains at most
64 KiB per file. The readiness response from B and server acknowledgements
carry their own return timestamps in `history.jsonl`
[code: `targets/03-omnigraph/witnessmark_omnigraph/part2.py:203,274,874`
and `targets/03-omnigraph/witnessmark_omnigraph/capture.py:148` @ `a064bb1`].

O1 runs a reader and a writer with separate HTTP clients on the unrelated
graph during branch creation. It adds `unrelated_reader_stall_ms` and
`unrelated_writer_stall_ms`, both longest completion gaps over the create
window. The M4 main-reader fields retain their calculation
[code: `targets/03-omnigraph/witnessmark_omnigraph/part2.py:423–466` @ `9e755b6`].

`race --scenario o3` uses the core thread runner and shares its merge fixture
with the O3 sequential control. In O2 and O3, the reset check compares
logical task and lease state because setup publishes a fresh commit ID on
each reset (the precondition hook, described under O2's runner wiring). The
full state retains those IDs. `race --no-spread-gate` keeps
per-trial Δ and records `spread_gate_ms: null` for calibration. The default
stays 40 ms [code: `targets/03-omnigraph/witnessmark_omnigraph/runner_scenarios.py:18,111`,
`targets/03-omnigraph/wm_omnigraph.py:92–103` and
`core/witnessmark/runner.py:149,232` @ `9e755b6`].

`parity` writes the four §9.1 artifacts for O6. It records Neo4j as the
primary reference and FalkorDB as the second, including the no-holder
case. A disagreement between references is recorded separately from a
difference in Omnigraph's result
[code: `targets/03-omnigraph/witnessmark_omnigraph/controls.py:85`
and `targets/03-omnigraph/witnessmark_omnigraph/part2.py:567` @ `9e755b6`].

### M5

- Add `history.jsonl` and `REPRO.md` for Omnigraph runs to meet master §9.1.
- Record wall-clock timestamps for O4 pause, resume, successor readiness and
  each acknowledgement before repeating O4. Capture server logs on failure
  to help explain the timing in finding 4 and diagnose failures like
  `20261115T170604Z-7d473a53`.
- Add an unrelated-graph reader and a writer on the Omnigraph side of O1
  before any public FalkorDB comparison. Follow master §11.5 for publication.
- Run the O2 claim races, O3 merge races and O6 traversal parity beyond the
  Part 1 sequential controls, and run O5 on MinIO [unmeasured: O2, O3, O6
  and O5 on MinIO].
- Run the O2b cost curve, with the sweep declared under O2b, on both
  engines after Omnigraph's δ is set [unmeasured: O2b].
- Exercise the [O4 clean-stop local transfer](#o4-clean-stop-local-transfer)
  variant in Phase B [unmeasured: O4 local transfer].

### O4 clean-stop local transfer

`failover --variant clean-stop` stops A with a 40-second Docker timeout.
Both pinned binaries default to a 25-second bounded server shutdown. The
variant records A's exit code and Docker's kill indicators, then reads
root-addressed `cluster status --json`. It starts B only if A exited cleanly
and status confirms admission was released. Otherwise it records
NOT_EXERCISED and saves the trial logs
[code: `targets/03-omnigraph/witnessmark_omnigraph/part2.py:256,926` @ `9e755b6`].
[docs: [v0.15.0 shutdown](https://github.com/ModernRelay/omnigraph/blob/v0.15.0/docs/user/deployment.md#binary),
[b2dbaff shutdown](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/deployment.md#binary)]

The maintainer's fresh-root bootstrap exception allows one exact-ID
`cluster force-unlock` immediately after successful `cluster apply`.
Initial direct apply leaves a lock on the disposable root. Before A first
starts, `cluster status --json` must report the same lock ID as apply.
The apply, status read and unlock are timed setup records with client
`nemesis`. An apply failure or mismatched holder stops the run. Ownership
transfer from A to B uses only the clean-stop path
[code: `targets/03-omnigraph/witnessmark_omnigraph/part2.py:190–236` @ `9e755b6`].
[docs: [v0.15.0 writer topology](https://github.com/ModernRelay/omnigraph/blob/v0.15.0/docs/user/deployment.md#writer-topology),
[b2dbaff writer topology](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/deployment.md#writer-topology)]

### Awaiting an upstream release

- O4's epoch claim waits for an upstream release with a claim route.
  The fence acceptance test, branch create or delete, cleanup, optimize,
  repeated failovers and simultaneous claims remain [unmeasured: O4 after
  epoch claim].

### Deferred

- The O1 catalog-width axis [unmeasured: O1 with wider catalogs].
- MinIO's `If-None-Match` and `If-Match` qualification versus RustFS
  [unmeasured: MinIO conditional writes]. The pinned storage guide qualifies
  RustFS [docs: storage.md @ `b2dbaff`].

## 12. M5 run plan

Declared on 2026-11-16, before the first Phase B batch started (master §10, no
fishing). Every cell below runs once in its batch, and every result is
reported. Builds are v0.15.0 and edge-b2dbaff. Races use `thread` mode with 50
clients and T = 20 (master §3.4, §6.6). Each Omnigraph command runs its own
sequential control and the controls its scenario defines (§3, master §6.2). A
cell whose sequential control is not met is INVALID by rule; it is recorded
and the batch continues.

**Baseline claim controls.** `python wm.py calibrate` names its own batch
`m1-<UTC>` and has no batch option [code: `core/witnessmark/cli.py:68` @
`6be2b8e`]. To keep the controls in the same batch as the Omnigraph cells,
without changing harness code, each batch runs the twelve cells of the M1
matrix (`--only falkordb,neo4j` selects all twelve) as the per-run command
that calibrate itself records: `python wm.py run --engine <e> --scenario <s>
--shape <shape> --clients 50 --trials 20 --seed <20261113 + i>
--no-spread-gate --batch <batch> --evidence evidence`, with i the cell's index
in calibrate's order. FalkorDB's naive guarded claim is the negative control
and Neo4j's naive claim the positive control for O2 (§3, O2 controls).

**Batch 1, calibration (`m5-<UTC>`).** O2 runs here are calibration only and
are never reported as O2 results.

| Cell | Command (`targets/03-omnigraph/wm_omnigraph.py`, unless noted) |
|---|---|
| Baselines | `docker compose -f baselines/docker-compose.yml up -d` |
| M1 controls, 12 cells | `python wm.py run ...` as above, `--no-spread-gate` |
| O2a, both builds | `race --scenario o2a --build <b> --storage local --clients 50 --trials 20 --no-spread-gate --provision` |
| O2c, both builds | `race --scenario o2c` with the same options |

After batch 1, Omnigraph's thread-mode δ is 1.5 × p99 of the release spread
over every valid O2a and O2c trial of both builds, rounded up to the next
whole ms, as master §6.3 did for M1. It is recorded in master §6.3 with the
batch id and p50, p99 and max, and becomes the Omnigraph default gate in code
before batch 2.

**Batch 2, main (`m5b-<UTC>`), on the commit that sets δ, in master §12.1
Phase B order.**

| # | Cell | Command (`targets/03-omnigraph/wm_omnigraph.py`, unless noted) |
|---|---|---|
| 0 | Baselines | `docker compose -f baselines/docker-compose.yml up -d` |
| 1 | O2b, Omnigraph, both builds, local | `costcurve --engine omnigraph --build <b> --storage local --spread-gate-ms <δ>`; the declared sweep N ∈ {1, 2, 5, 10, 25, 50}, 3 warm-ups, 5 measured repetitions (§3, O2b) |
| 2 | O2b, FalkorDB side | `costcurve --engine falkordb --spread-gate-ms 40` (the M1 thread-mode δ) |
| 3 | M1 controls, 12 cells | `python wm.py run ...` as above, `--no-spread-gate`, as calibrate runs them |
| 4 | O2a and O2c, both builds | `race --scenario o2a\|o2c --build <b> --storage local --clients 50 --trials 20 --spread-gate-ms <δ> --provision` |
| 5 | O3, both builds | `race --scenario o3` with the same options |
| 6 | O6, both builds | `parity --build <b> --storage local`; Neo4j 5.26.2 primary, FalkorDB 6.0.4 second reference |
| 7 | O5, both builds | `visibility --build <b> --storage minio`, then `--storage local` for comparison with M4 |
| 8 | O4, both builds | `failover --variant clean-stop --build <b> --storage local` |
| 9 | O1, both builds | `curve --build <b> --storage local\|minio\|proxy`; `--include-falkor` once, on v0.15.0 local, which runs first among the O1 cells. If the FalkorDB curve misses the S28 band, the driver stops the batch (master §6.5, §8) |

O2b is reported as the cost of documented behaviour, not as a defect (§3,
O2b). Any FalkorDB comparison stays internal (master §11.5).

**Amendment before batch 2 (maintainer decision, 2026-11-16).** Declared
before batch 2 started, after batch 1 (§13).

- **One actor per client.** The pinned server guide documents an
  actor-to-token object, `OMNIGRAPH_SERVER_BEARER_TOKENS_JSON`, in which "the
  token selects the actor … clients cannot claim another actor". The pinned
  policy guide documents a graph policy that is bound in `cluster.yaml` and
  installed by `cluster apply`
  [docs: [server.md v0.15.0](https://github.com/ModernRelay/omnigraph/blob/373834b4c1c4b29cf0ddd64bee9565f98c60cc26/docs/user/operations/server.md),
  [server.md b2dbaff](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/operations/server.md),
  [policy.md v0.15.0](https://github.com/ModernRelay/omnigraph/blob/373834b4c1c4b29cf0ddd64bee9565f98c60cc26/docs/user/operations/policy.md),
  [policy.md b2dbaff](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/operations/policy.md)].
  When `race` and `costcurve` provision, the server now runs with one actor
  per client: `wm-admin` for fixture setup and observation, and `wm-c00` to
  `wm-c49` for the clients. Each actor has a random bearer token per run. The
  tokens stay in memory and the container environment, and never reach
  evidence.
  - `docker/compose.actors.yml` replaces `--unauthenticated` with the token
    object.
  - `workload/cluster-actors.yaml` binds `workload/actors.policy.yaml`, which
    grants the group `read` and `change` (`branch_scope: any`),
    `branch_create`, `branch_delete` and `branch_merge`
    (`target_branch_scope: any`, because the pinned validator refuses
    `branch_scope` on `branch_create`), and `invoke_query`.
  - The manifest's SUT component (races) or `actors` field (O2b) records the
    mode, the actor names, the token source and the policy path
    [code: `targets/03-omnigraph/witnessmark_omnigraph/actors.py` @ `a6b690d`].

  N stays 50 for O2a, O2c and O3, and the O2b sweep stays N ∈ {1, 2, 5, 10,
  25, 50}. A scratch smoke on both builds (50 clients, outside `evidence/`)
  had no admission-limit refusal. Other commands (O1, O4, O5, O6) keep the
  unauthenticated server they ran under in M4. δ stays 55 ms: it is measured
  from the clients' invocation times, which the actor change does not touch
  [inference].
- **Typed refusals.** HTTP 429 is the typed, definite refusal
  `admission_limit` [docs: server.md, "Admission limits use 429 … with
  Retry-After", at both pins]. The O2 and O3 race checks accept every typed
  definite refusal and report counts per type. A trial fails I1 only on:
  - a second winner;
  - a second holder;
  - a winner that does not hold its lease (a lost acknowledged write);
  - an unknown outcome that could have applied, which the final state cannot
    account for (master §6.4);
  - an untyped refusal.

  Sequential controls still require the documented refusal type
  (`precondition_failure` for O2a, `CardinalityViolation` for O2c, a typed
  merge conflict for O3) [code:
  `targets/03-omnigraph/witnessmark_omnigraph/runner_scenarios.py` and
  `client.py` @ `a6b690d`]. The O2b agent policy is unchanged: any refusal
  other than `precondition_failure` ends that agent, and the refusal is
  recorded.
- **Commit.** Batch 2 runs on the commit that records this amendment, after
  `a6b690d`, not on `fffe48b`. Its race and `costcurve` commands are those in
  the table above, with the default `--actors per-client`.

**Amendment 2, the O1 re-run (maintainer decision, 2026-11-16).** Declared
before the batch ran. The kept-connection change is a change to O1's method
(§3 O1, "Connection model"). So that every M5 O1 number uses one connection
model, batch `m5e-<UTC>` re-runs every O1 cell of batch 2 on the commit that
records the change, in batch 2's order: `curve --build v0.15.0 --storage
local --include-falkor` first (it carries the FalkorDB S28 curve and stops
the batch if the band is missed), then v0.15.0 MinIO and proxy, then edge
local, MinIO and proxy. Batch 2's O1 runs and the `m5d` re-run stay in
`evidence/` and are reported as superseded by `m5e`.

**Re-runs.** Only a harness bug, fixed with a unit test and committed first,
re-runs a cell, under a new batch id (`m5c-`, `m5d-`, ...). The affected
cells and the reason are recorded. Nothing is re-run to change a result, and
no evidence is deleted or edited.

## 13. M5 Phase B, batch 1 and the decision before batch 2

Phase B ran batch 1 and one re-run batch, set Omnigraph's δ, and stopped
before batch 2 for a maintainer decision on the O2 refusal types below. The
decision is recorded under "Classification", and the results are in §14.
The host is the one in §10. Every number comes from the linked reports, which
are regenerated from `evidence/` and byte-compared.

| Batch | Report | Harness commit | What it holds |
|---|---|---|---|
| `m5-20261115T222957Z` | [evidence/M5_OMNIGRAPH_CALIBRATION.md](../../evidence/M5_OMNIGRAPH_CALIBRATION.md) | `772ef96` | batch 1: the five FalkorDB control cells, and O2a and O2c on both builds without a spread gate. The seven Neo4j control cells did not run (below) |
| `m5c-20261115T223540Z` | [evidence/M5_OMNIGRAPH_B1.md](../../evidence/M5_OMNIGRAPH_B1.md) | `772ef96` | re-run of batch 1's seven Neo4j control cells |

**Why `m5c` exists.** The batch driver started the Neo4j cells 15 s after
`docker compose up -d`, before Neo4j answered HTTP. Each exited 1 with
`RemoteDisconnected` in under 1 s and wrote no run directory. Their redacted
notes are in `evidence/omnigraph/errors/m5-20261115T222957Z/`. The driver,
which is untracked under `.state`, now waits for both baselines before any
cell. No harness code changed, and `m5c` ran on the same commit as batch 1.

### Controls

| Control | Result | Runs |
|---|---|---|
| FalkorDB 6.0.4, five M1 shapes (negative) | 0 of 20 trials violating in each of the five; sequential controls met | `20261115T222959Z-dd58c949`, `20261115T223002Z-1cc6e5c3`, `20261115T223005Z-c8302f31`, `20261115T223008Z-6cc2bc17`, `20261115T223011Z-f2f25b0b` |
| Neo4j 5.26.2, three naive shapes (positive) | fired in 20 of 20 trials each (`KNOWN_DEVIATION`, KD-N1) | `20261115T223541Z-d507952d`, `20261115T223556Z-0c7fd4ab`, `20261115T223616Z-c2fb1473` |
| Neo4j 5.26.2, four lock-first, direct and disjoint shapes (negative) | 0 of 20 trials violating in each | `20261115T223551Z-36ddd91e`, `20261115T223602Z-b838cc27`, `20261115T223608Z-4c7cea08`, `20261115T223623Z-ed33ecfc` |
| O2a and O2c sequential controls, both builds | met: one winner `c00`, holder `c00`, typed refusals | `20261115T223017Z-22107db4`, `20261115T223104Z-bcff6931`, `20261115T223149Z-b1b52c9c`, `20261115T223237Z-3658b53d` |

### δ calibration

Batch 1 ran O2a and O2c on both builds with 50 clients. All 80 trials
(4 runs × 20) were valid. Their release spread had p50 8.671 ms,
p99 36.365 ms and max 36.365 ms. Omnigraph's thread-mode δ is
⌈1.5 × 36.365⌉ = **55 ms** [measured: the four O2 runs above]. It is recorded
in master §6.3 and was set as `OMNIGRAPH_THREAD_SPREAD_GATE_MS` in `fffe48b`.
The M1 40 ms gate is unchanged.

### Observation: refusal types in batch 1's O2 runs (calibration only)

Batch 1's O2 runs are calibration runs, not O2 results. The core verdict for
all four is FAIL, in 20 of 20 trials, but not because of a second winner. In
every one of the 80 trials exactly one client was acknowledged, the task had
exactly one holder, and the only lease record was the winner's [measured: the
four O2 runs; every trial's check detail reads "1 winner(s)"]. The checker
also requires each loser's refusal to be the scenario's one expected type:
`precondition_failure` for O2a, `CardinalityViolation` for O2c [code:
`targets/03-omnigraph/witnessmark_omnigraph/runner_scenarios.py:39,72–79` @
`fffe48b`]. Counted from `history.jsonl` over 20 trials × 50 clients per
run, the refusals were:

| Run | Build | Scenario | Acknowledged | Refusals |
|---|---|---|---|---|
| `20261115T223017Z-22107db4` | v0.15.0 | O2a | 20 | `too_many_requests` 680, `precondition_failure` 266, `CardinalityViolation` 34 |
| `20261115T223104Z-bcff6931` | edge-b2dbaff | O2a | 20 | `too_many_requests` 680, `precondition_failure` 262, `CardinalityViolation` 38 |
| `20261115T223149Z-b1b52c9c` | v0.15.0 | O2c | 20 | `too_many_requests` 680, `conflict` 263, `CardinalityViolation` 37 |
| `20261115T223237Z-3658b53d` | edge-b2dbaff | O2c | 20 | `too_many_requests` 680, `CardinalityViolation` 300 |

- `too_many_requests` (HTTP 429), "actor in-flight count cap 16 exceeded",
  came back 34 times in every trial of every run. All 50 harness clients send
  without credentials. The server appears to treat them as one actor, so at
  most 16 of the 50 claims were admitted at once [measured: the four runs]
  [inference: one actor, from the message and the constant count 50 − 16].
  Whether the pinned docs describe this cap is [unmeasured: docs check].
- `conflict` on v0.15.0 O2c: "write authority 'graph_head:main' changed during
  preparation, reprepare from the current branch state". This is O-K2's
  retryable conflict. In the same position the edge build returned
  `CardinalityViolation`.
- In O2a, 34 and 38 conditional claims were refused with `CardinalityViolation`
  rather than `precondition_failure`.

No refusal was untyped and no outcome was unknown. Nothing here was re-run.

### Classification (maintainer decision, 2026-11-16)

- **BOUNDARY: per-actor admission limit.** The pinned server guide
  documents that admission limits answer 429 with `Retry-After` [docs:
  server.md at v0.15.0 and b2dbaff]. Batch 1 measured the limit's size:
  "actor in-flight count cap 16 exceeded", 34 refusals in every trial of all
  four runs with 50 clients on one actor [measured:
  `20261115T223017Z-22107db4`, `20261115T223104Z-bcff6931`,
  `20261115T223149Z-b1b52c9c`, `20261115T223237Z-3658b53d`]. The guide
  documents the 429 behaviour, not the value 16, which comes only from the
  server's message [measured]. This is documented behaviour, not a defect.
  The harness now classifies it as `admission_limit`, a typed definite
  refusal, and gives each client its own actor (§12, amendment).
- **OBSERVED: refusal type of admitted O2a losers.** Of the admitted losers
  (15 per trial × 20 trials = 300 per run), 34 of 300 on v0.15.0 and 38 of
  300 on edge-b2dbaff were refused with `CardinalityViolation` rather than
  the documented `precondition_failure` [docs: mutations/conditional.md; O-K3]
  [measured: `20261115T223017Z-22107db4`, `20261115T223104Z-bcff6931`]. Both
  are typed refusals that write nothing, and one holder remained. Not chased
  with further runs.
- **OBSERVED: O2c refusal type differs by build.** For a constraint-guarded
  claim that lost the race, v0.15.0 answered `conflict` ("write authority
  'graph_head:main' changed during preparation, reprepare from the current
  branch state") 263 times, while edge-b2dbaff answered `CardinalityViolation`
  in its place [measured: `20261115T223149Z-b1b52c9c`,
  `20261115T223237Z-3658b53d`]. Both are typed refusals; `conflict` is O-K2's
  retryable conflict. Not chased with further runs.

Batch 1's FAIL verdicts stay in the evidence as recorded. The checker that
produced them is superseded for later batches; nothing was re-run to change
them. Batch 2 runs as declared in §12, with the amendment.

## 14. Results (M5)

**Provenance.** Five batches on the host of §10 (Windows 11, 11th Gen
i5-11320H, 8 logical cores, 23.8 GB, Docker VM 8 CPUs and 11.6 GB). Every run
records a clean tree. The five reports regenerate from `evidence/` byte for
byte. The switchyard containers stayed up and idle on the host during every
batch (under 0.2% CPU each when checked before batch 1).

| Batch | Report | Harness commit | What it holds |
|---|---|---|---|
| `m5-20261115T222957Z` | [evidence/M5_OMNIGRAPH_CALIBRATION.md](../../evidence/M5_OMNIGRAPH_CALIBRATION.md) | `772ef96` | batch 1, calibration: the FalkorDB controls, and O2a and O2c without a spread gate (§13) |
| `m5c-20261115T223540Z` | [evidence/M5_OMNIGRAPH_B1.md](../../evidence/M5_OMNIGRAPH_B1.md) | `772ef96` | re-run of batch 1's seven Neo4j control cells, which the driver had started before Neo4j answered (§13) |
| `m5b-20261115T230235Z` | [evidence/M5_OMNIGRAPH.md](../../evidence/M5_OMNIGRAPH.md) | `6a15b9c` | batch 2, the main batch: 37 commands, 36 exit 0. Its O1 runs are superseded by `m5e` |
| `m5d-20261116T003205Z` | [evidence/M5_OMNIGRAPH_B2.md](../../evidence/M5_OMNIGRAPH_B2.md) | `f7ae8f2` | re-run of the one batch-2 cell that failed on a harness bug, O1 on v0.15.0 local with the FalkorDB curve. **Superseded by `m5e`** |
| `m5e-20261116T004953Z` | [evidence/M5_OMNIGRAPH_B3.md](../../evidence/M5_OMNIGRAPH_B3.md) | `fb97518` | every O1 cell, both builds, local, MinIO and proxy, with the FalkorDB curve, on the kept-connection method (§12, amendment 2); 8 of 8 commands exit 0. **The M5 O1 results** |

**Why the re-runs exist.** Nothing was re-run to change a result. Each earlier
run stays in `evidence/` and in its report.

| Re-run | Cause | Where |
|---|---|---|
| Neo4j control cells | Batch 1's driver started them before Neo4j answered HTTP. They exited 1 in under 1 s and wrote no run directory; their notes are in `evidence/omnigraph/errors/m5-20261115T222957Z/`. The driver is untracked. | `m5c` |
| O1, v0.15.0, local, `--include-falkor` | Harness bug. The three closed-loop loads opened one TCP connection per request, and the sockets left in TIME_WAIT exhausted the host's ephemeral ports: `WinError 10048` in the unrelated reader. The run stopped before its manifest was complete, and before the FalkorDB curve [measured: `20261115T232536Z-6d1be538`, its `ERROR.md` and `evidence/omnigraph/errors/m5b-20261115T230235Z/31-o1-v0.15.0-local/ERROR.md`]. Fixed in `f7ae8f2`: each load keeps one connection. A scratch check against both pinned servers added 0 and 1 TIME_WAIT sockets over 300 kept reads, against 295 without keep-alive. | `m5d` |
| Every O1 cell | Method change, not a result. The kept connection changes O1's method (§3 O1, "Connection model"). After `m5d`, v0.15.0 local was the only O1 cell on kept connections, so the maintainer ruled that every O1 cell be re-run on one model. `fb97518` also records each read retried after a dropped kept connection as its own history record and counts it per sample. | `m5e` |

**Superseded O1 runs.** Batch 2's five completed O1 runs opened a connection
per request [measured: `20261115T233008Z-ba6c2bba`, `20261115T233710Z-d6e9001c`,
`20261115T235639Z-1a7662ca`, `20261116T000227Z-a91e2dae`,
`20261116T001000Z-dedd3d1f`]. Batch 2's failed run is
`20261115T232536Z-6d1be538`. `m5d`'s run kept connections
[measured: `20261116T003206Z-579fed57`]. All seven stay in `evidence/` and in
`evidence/M5_OMNIGRAPH.md` and `evidence/M5_OMNIGRAPH_B2.md`. All seven are
superseded by `m5e`, which ran every O1 cell on one connection model. No
number below comes from them. The same port bug touched O2b, whose agents
still open a connection per request: one read per build ended with
`WinError 10048` (Results, O2b).

### Controls

| Control | Result | Runs |
|---|---|---|
| FalkorDB `GRAPH.COPY` against S28 (master §6.5, §7.2) | **met** at all three sizes: 121.5, 321.2 and 1,955.0 ms against 165, 546 and 2,400 (−26%, −41%, −19%). Run under `appendonly yes` and `appendfsync always`. `m5d`'s superseded curve also met it, at 85.2, 474.7 and 1,957.3 ms (`20261116T003206Z-579fed57`) | `20261116T005007Z-772bf510` (`m5e`) |
| FalkorDB 6.0.4, five M1 shapes (negative) | 0 of 20 trials violating in each, in batch 1 and batch 2; sequential controls met | batch 1 §13; batch 2 `20261115T231353Z-aacd795d`, `20261115T231355Z-e3f43105`, `20261115T231358Z-4ac87436`, `20261115T231400Z-99a48567`, `20261115T231402Z-1d44e6d1` |
| Neo4j 5.26.2, three naive shapes (positive) | fired in 20 of 20 trials each, in `m5c` and in batch 2 | batch 2 `20261115T231405Z-2793c658`, `20261115T231419Z-2365e346`, `20261115T231439Z-ff2bf67f` |
| Neo4j 5.26.2, four negative shapes | 0 of 20 trials violating in each, in `m5c` and in batch 2 | batch 2 `20261115T231414Z-902d7816`, `20261115T231425Z-f5bfeba7`, `20261115T231431Z-36b7ecf4`, `20261115T231445Z-cde1d9cd` |
| O2a, O2c and O3 sequential controls, both builds (batch 2) | met in all six runs, with the documented refusal type for every later operation | the six race runs below |
| O6 sequential control, both builds | met: identical normalised results from Neo4j, FalkorDB and Omnigraph | `20261115T232412Z-8935cb2f`, `20261115T232421Z-31c6fa46` |
| I6a prefix and I6b isolation, end of each O1 curve | gapless, non-empty prefix (5 entries) and isolation held in 6 of 6 `m5e` runs (and in the 6 superseded complete runs) | the six `m5e` O1 runs |

### Results

Scope for all rows: one `omnigraph-server` per run, on a local root unless
stated otherwise, `thread` mode, 50 clients, each with its own actor (§12,
amendment), and the race gate at δ = 55 ms.

| Scenario | v0.15.0 | edge-b2dbaff | Verdict |
|---|---|---|---|
| O2a, conditional claims on one task, T = 20 | 1 acknowledged winner and 1 holder in 20 of 20 valid trials; 980 typed refusals: `precondition_failure` 533, `CardinalityViolation` 447 [measured: `20261115T231454Z-7f2e75a3`] | 20 of 20 the same; `CardinalityViolation` 496, `precondition_failure` 484 [measured: `20261115T231539Z-c7be08c9`] | PASS on both |
| O2c, claims guarded by `@card(0..1)`, T = 20 | 1 winner and 1 holder in 20 of 20; `CardinalityViolation` 599, `conflict` 381 [measured: `20261115T231626Z-b28d5aff`] | 20 of 20 the same; `CardinalityViolation` 980 [measured: `20261115T231715Z-071a8831`] | PASS on both |
| O3, 50 concurrent merges of `agent/<i>` into main, T = 20 | 1 merge landed and 1 holder in 20 of 20; the other 980 merges were refused with `CardinalityViolation`; none picked a winner silently [measured: `20261115T231810Z-701d1d1d`] | 20 of 20 the same [measured: `20261115T232110Z-c67ea540`] | PASS on both |
| O6, traversal parity against Neo4j (primary) and FalkorDB | `q_eligible`, `q_live` and `q_live_open` identical on all three engines [measured: `20261115T232412Z-8935cb2f`] | identical [measured: `20261115T232421Z-31c6fa46`] | PASS on both |
| O5, read your writes on a second server, MinIO | seen on the first poll, 1,439.9 ms after A's acknowledgement, including stopping A and starting B [measured: `20261115T232428Z-7b3675aa`] | first poll, 1,498.6 ms [measured: `20261115T232445Z-74a4b9d4`] | OBSERVED |
| O5, local root (for comparison with M4's 1,523.8 and 1,334.6 ms) | first poll, 1,644.0 ms [measured: `20261115T232500Z-bc9d3caf`] | first poll, 1,456.4 ms [measured: `20261115T232509Z-b97455a1`] | OBSERVED |
| O4, clean-stop local transfer | A's write acknowledged; A exited 0, neither killed nor out of memory; `cluster status` showed admission released; B started and its write was acknowledged; the scan through B found both writes, none missing [measured: `20261115T232518Z-4a2c639b`] | the same [measured: `20261115T232527Z-f549fc44`] | OBSERVED: the documented transfer works on both builds. The fence was not engaged (no epoch claim, §3 O4) |

**Release spread in batch 2.** The 120 Omnigraph race trials had p50 8.30 ms,
p99 18.90 ms and max 19.66 ms, inside δ = 55 ms; the gate invalidated none
[measured: `evidence/M5_OMNIGRAPH.md`, "Release spread"].

**O2b, the cost of documented behaviour.** Local root, both builds, the
declared sweep, 3 warm-ups and 5 measured repetitions per N, the gate at
55 ms (Omnigraph) and 40 ms (FalkorDB). All measured repetitions were valid,
and no holder check failed. Medians:

| N | Omnigraph attempts, v0.15.0 / edge | Omnigraph wasted attempts | Omnigraph time to all claimed (ms), v0.15.0 / edge | FalkorDB attempts | FalkorDB time to all claimed (ms) |
|---|---|---|---|---|---|
| 1 | 1 / 1 | 0 / 0 | 51.7 / 40.2 | 1 | 1.1 |
| 2 | 3 / 3 | 1 / 1 | 94.3 / 85.8 | 2 | 1.2 |
| 5 | 15 / 15 | 10 / 10 | 277.7 / 266.0 | 5 | 1.8 |
| 10 | 55 / 55 | 45 / 45 | 815.3 / 777.8 | 10 | 2.7 |
| 25 | 325 / 325 | 300 / 300 | 4,494.1 / 4,465.0 | 25 | 5.2 |
| 50 | 1,267 / 1,259 | 1,217 / 1,209 | 23,376.1 / 22,517.0 | 50 | 9.8 |

[measured: `20261115T230248Z-b1c0842e`, `20261115T230816Z-91a819a6`,
`20261115T231348Z-552b23e0`]

- Omnigraph's median attempts equal N(N + 1)/2 up to N = 25, and are just
  below it at N = 50 (1,275). That is what one success per round of re-reads
  gives when every publish invalidates every other agent's condition
  [inference from O-K3 and the counts]. The hypothesis of §3 O2b holds on
  both builds.
- FalkorDB's naive guarded claims on disjoint tasks succeeded on the first
  attempt every time, with no wasted attempts.
- Two measured repetitions had an agent that never claimed. One agent's read
  ended with `WinError 10048`, the host port exhaustion above, so that agent
  stopped by the declared policy, and the trial stayed valid (1 unknown
  outcome, under 5%): v0.15.0 at N = 50 (49 of 50 claimed) and edge at
  N = 25 (24 of 25) [measured: `20261115T230248Z-b1c0842e` trial 30,
  `20261115T230816Z-91a819a6` trial 29]. O2b's agents still open a connection
  per request. These two repetitions were not re-run.
- The comparison with FalkorDB stays internal (master §11.5).

**O1, branch creation with an unrelated-graph reader and writer (`m5e`, kept
connections).** Every cell ran on the kept-connection method (§3 O1). Cell
medians across n ∈ {32k, 128k, 512k} and s ∈ {0, 4, 16, 64}, with three
create/delete warm-ups and five measured repetitions per cell:

| Build, storage | Create (ms) | Main-reader stall (ms) | Unrelated reader stall (ms) | Unrelated writer stall (ms) | Run |
|---|---|---|---|---|---|
| v0.15.0, local | 8.02–13.88 | 0–2.96 | 4.41–7.34 | 5.61–13.88 | `20261116T005007Z-772bf510` |
| edge, local | 7.02–15.34 | 0–2.27 | 4.55–9.05 | 7.02–15.34 | `20261116T012433Z-cb2af23d` |
| v0.15.0, MinIO | 49.00–73.40 | 37.64–55.60 | 18.84–51.45 | 37.01–69.39 | `20261116T005740Z-b787c6ff` |
| edge, MinIO | 48.44–116.17 | 35.62–105.17 | 20.12–49.45 | 40.11–116.17 | `20261116T013014Z-7bf20e6c` |

- **Read retries.** No read was retried after a dropped kept connection in
  any of the six runs. No `kept_connection_dropped` record appears in their
  histories, and every sample's `read_retries` is 0 [measured: the six `m5e`
  O1 runs; `evidence/M5_OMNIGRAPH_B3.md`, "Read retries" columns]. Their only
  unknown outcomes are 1 to 4 readiness polls per MinIO and proxy run, during
  stack start-up, answered with a closed connection (trial 0, kind
  `readiness`). Batch 2 had the same kind.
- Through the 17 ms proxy, one create plus delete took 34 to 38 requests on
  v0.15.0 and 34 to 41 on edge. GET response bytes ran from 58,338 to 498,411
  (v0.15.0) and 58,668 to 502,220 (edge) [measured: `20261116T010446Z-36dc0553`,
  `20261116T013703Z-aade14a0`].
- Copy-weight cycles (create, claim, score, discard) on a local root were 63.9,
  107.5 and 256.4 ms on v0.15.0 and 76.0, 104.3 and 218.5 ms on edge, at 32k,
  128k and 512k [measured: `20261116T005007Z-772bf510`,
  `20261116T012433Z-cb2af23d`].
- The stall metrics are the longest gap between completions inside the create
  window. A write takes longer than a local create here, so the unrelated
  writer's gap often equals the whole create window. On MinIO it was 0.73 to
  1.0 times the create time per cell. The metric does not separate a blocked
  writer from a slow one [inference from the metric and the equal values].
  On MinIO, the unrelated reader's longest gap was 0.34 to 0.96 (v0.15.0) and
  0.24 to 0.91 (edge) times the create time per cell, and under half of it in
  3 and 4 of 12 cells. In those cells it kept completing reads during
  creation [measured: the two `m5e` MinIO runs].
- **Comparison with M4, with the method change.** M4's O1 had one load, the
  main reader, and it opened a new TCP connection per request. M5's O1 has
  three loads, each on one kept connection (§3 O1). With that difference:
  - local create medians were 6.0–8.2 ms (v0.15.0) and 5.35–11.25 ms (edge)
    in M4, against 8.02–13.88 and 7.02–15.34 ms here;
  - MinIO create medians were 36.2–70.9 and 37.4–88.6 ms in M4, against
    49.00–73.40 and 48.44–116.17 ms here;
  - main-reader stall medians were 0–0.66 and 0–0.75 ms (local) and 27–60 and
    28–81 ms (MinIO) in M4, against 0–2.96, 0–2.27, 37.64–55.60 and
    35.62–105.17 ms here;
  - proxy request counts were 34–39 and 34–37 in M4, against 34–38 and 34–41
    here [measured: M4 `20261115T172253Z-0adb5788`, `20261115T175653Z-12eb6ff6`,
    `20261115T173025Z-fc74457b`, `20261115T180251Z-742224c3`,
    `20261115T173716Z-d303435d`, `20261115T181001Z-adf60896`; M5 the six `m5e`
    runs].

  The load count and the connection model both changed between the two
  milestones. So the differences are not attributed to Omnigraph, and the
  reader figures are not one method measured twice [inference].
- The FalkorDB side ran once, beside the v0.15.0 local curve, and met S28 (see
  Controls). The comparison stays internal (master §11.5).

### Boundaries, observations and cells not exercised

- **BOUNDARY (batch 1): per-actor admission limit.** 429 "actor in-flight
  count cap 16 exceeded", 34 refusals per trial with 50 clients on one actor
  [measured: `20261115T223017Z-22107db4`, `20261115T223104Z-bcff6931`,
  `20261115T223149Z-b1b52c9c`, `20261115T223237Z-3658b53d`]. The admission
  limit is documented (server.md); its size is not (§13). With one actor per
  client, batch 2 had no admission-limit refusal.
- **OBSERVED: O2a losers refused with `CardinalityViolation`.** Batch 1:
  34 of 300 (v0.15.0) and 38 of 300 (edge) admitted losers. Batch 2, all 980
  losers admitted: 447 of 980 and 496 of 980. The documented refusal is
  `precondition_failure` [docs: mutations/conditional.md]. Both types are
  typed and write nothing, and every trial kept one holder [measured: the four
  O2a runs]. Not chased.
- **OBSERVED: O2c refusal type differs by build.** v0.15.0 answered
  `conflict` (reprepare, O-K2) 263 times in batch 1 and 381 times in batch 2,
  where edge answered `CardinalityViolation` [measured: the four O2c runs].
  Not chased.
- **OBSERVED: FalkorDB's own admission limit.** `Max pending queries
  exceeded` refused 60 to 118 claims per FalkorDB claim-control run, and
  6 claims in one O2b warm-up at N = 50, with no violation and every measured
  O2b repetition complete [measured: `20261115T231353Z-aacd795d`,
  `20261115T222959Z-dd58c949`, `20261115T231348Z-552b23e0` trial 12].
- **INVALID:** no trial in batch 2, `m5c` or `m5d`. Batch 1's O2 FAIL verdicts
  come from the superseded single-type checker (§13); they are calibration
  runs, not O2 results.
- **NOT_EXERCISED:** none of the M5 cells. Both O4 clean-stop cells released
  admission and started B.

**Credit.** On both pinned builds, with 50 concurrent clients:
- every conditional claim race, constraint-guarded claim race and merge race
  left exactly one acknowledged winner and one holder in 120 of 120 trials;
- no merge picked a winner silently;
- traversal results matched Neo4j and FalkorDB exactly;
- the documented clean-stop ownership transfer released admission and kept
  every acknowledged write.

### Not run

- O4's epoch-claim acceptance test and its boundary probes, which wait for an
  upstream release with a claim route (§11).
- O3's merge-throughput curve against the number of live branches (#643's
  axis). The harness has no such curve; the races above use one branch count.
- The O1 catalog-width axis and MinIO's conditional-write qualification,
  which stay deferred (§11).
- O5 with a concurrent second reader; O5 measures process turnover only.
- An O2b repeat with kept connections for the agents. O2b's agents still
  open a connection per request.
