# Target 03: Omnigraph (ModernRelay/omnigraph)

Part of Witnessmark. Read it with the [master blueprint](../../MASTER_BLUEPRINT.md); "master §n" means a section of that document.

| | |
|---|---|
| Status | Specification v0.1, 2026-11-13. Part 1 and the M4 batches (O1, O4, O5, I6 controls) are recorded in the results section (§10); O2, O3 and O6 races and the writer-epoch fence acceptance remain not run. M4 awaits review. |
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
- **I6a.** Create a branch while `m_ledger` appends at a fixed rate. The branch must hold a gapless prefix of the ledger.
- **I6b.** Writes on the branch must be invisible on main, and the reverse, until a merge.
- **Runner.** Padding is loaded through the strict bounded NDJSON route in
  4,096-entity commits. For every `(n, s)` cell, three create/delete warm-ups
  precede five measured repetitions. One closed-loop `q_task` reader owns its
  own connection; object-store request counts are taken in a separate matched
  proxy repetition [code: `targets/03-omnigraph/witnessmark_omnigraph/part2.py`].
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
  - 50 agents, each a separate client process or a thread with its own HTTP connection, read the task (`q_task` plus the commit id) and submit `m_claim_cond`. A barrier releases them together. T = 20.
  - Expected [docs]: exactly one success and 49 `precondition_failure` replies. After re-reading, all 50 agents see the same holder.
  - Checked: I1 Form A, rules (a) to (d).
- **O2b, conditional claims on disjoint tasks.**
  - 50 agents claim 50 different tasks.
  - Any intervening commit invalidates a condition (O-K3), so the run measures rounds to completion, wasted attempts and latency.
  - This is a cost curve, not a correctness test. It shows what a branch-wide precondition costs on a workload with no logical conflicts. On FalkorDB, disjoint guarded claims are serialised but never refuse one another.
- **O2c, claims enforced by the constraint.**
  - 50 agents submit `m_claim_card` for one task, with no condition.
  - Expected [docs]: exactly one `HeldBy` edge, 49 typed refusals, and no silent duplicate.
  - This confirms that the cardinality check is evaluated against the head each publish lands on.
- **Controls.**
  - Sequential: the 50 claims one at a time.
  - Negative: the same race on FalkorDB 6.0.4, using a naive guarded Cypher claim.
  - Positive: Neo4j 5.26.2 with the naive claim (master §6.2).

**Runner wiring.** Omnigraph is a network server, so O2 uses the core thread
runner. Every client owns a distinct `OmnigraphClient`/HTTP connection and the
core barrier releases their requests together; this models independent network
clients without process-start noise [code:
`targets/03-omnigraph/witnessmark_omnigraph/runner_scenarios.py` and
`core/witnessmark/runner.py`].

### O3. One branch per agent, then merge (I1 at merge)

- **Setup.** 50 branches `agent/<i>`. On each, an agent claims the same task by inserting `HeldBy(task → agent_i)`.
- **Procedure.** Merge every branch into main: first one after another, then concurrently from separate clients.
- **Expected [docs].** The first merge lands. Every later merge reports a typed conflict, `CardinalityViolation` or a divergence conflict, and writes nothing. No merge picks a winner silently (O-K5).
- **Also measured.** Merge throughput against the number of live branches, reported as a curve (#643's axis).

### O4. Stale writer after failover: an acceptance test for the writer epoch fence (I1 and I2 across a failover)

- **Topology.** Two `omnigraph-server` processes, A and B, on one graph root, in separate containers. Storage is a shared local volume, then MinIO.
- **Sequence for each trial.**
  1. A serves main and holds its writer epoch. A client asks A to write.
  2. The fault injector pauses A's container (`docker pause`) at one of three phases:
     - p1, before staging;
     - p2, after staging and before publish;
     - p3, during publish retries.

     A seeded schedule picks the phase. It uses server-side progress markers where they exist, and otherwise a declared sweep of time offsets across the write.
  3. B starts and becomes main's writer the documented way, by acquiring the lease and claiming the epoch. In variant (b), B also publishes P_B.
  4. The fault injector resumes A (`docker unpause`), and A carries on with its write.
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
| MinIO | Built locally from MinIO's official, GitHub-verified signed tag `RELEASE.2025-09-07T16-13-09Z`, which dereferences to commit `07c3a429bfed433e49018cb0f78a52145d4bedeb`. `Dockerfile.minio` verifies that dereference before compiling with the release's own `buildscripts/gen-ldflags.go`; its Go and Debian stages are pinned to `sha256:79390b5e5af9ee6e7b1173ee3eac7fadf6751a545297672916b59bfa0ecf6f71` and `sha256:734a72b3d6142a71993b4bc580ca01d8ca687f77a2c422d96a961d3376b179bc`. Local image `witnessmark/minio:RELEASE.2025-09-07T16-13-09Z`, digest `sha256:5c9f6e9b19cdd3c333900e5102b196bfdb2e19f3e25674bfa0cef924e67dc899`; `minio --version` reports the exact tag, commit and Go 1.24.2 [code: `targets/03-omnigraph/docker/Dockerfile.minio`] [measured: source build and loopback readiness smoke, 2026-11-15]. |
| Delay proxy | Standard-library forwarding proxy `core/witnessmark/proxy.py`; fixed 17 ms before each forwarded request, matching #642's method. `GET /__witnessmark__/counts` returns request count, request bytes and response bytes per HTTP method; `POST /__witnessmark__/reset` starts a matched repetition from zero. Its control calls are not counted. Local image `witnessmark/proxy:17ms`, digest `sha256:a865395be1e245d04d4e0b5a8bcc0813272a8e056f18b2cd94cb5a7230fc3e23`; it runs only in separate matched repetitions, never timing repetitions. Its first build rewrote the `Content-Length` of every `HEAD` reply to 0, so the object-store client saw empty objects (`Range started at 0 and ended at 0`); a reply to `HEAD` now keeps the upstream length (`core/tests/test_proxy.py`) [code: `core/witnessmark/proxy.py`] [measured: loopback MinIO smoke, 2026-11-15]. |
| S3 settings and readiness | `compose.yml` passes `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION=us-east-1`, `AWS_ENDPOINT_URL_S3`, `AWS_S3_FORCE_PATH_STYLE=true` and `AWS_ALLOW_HTTP=true` for the local, disposable endpoints [docs: [storage.md, "S3 configuration"](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/concepts/storage.md#s3-configuration), [deployment.md](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/deployment.md#s3-compatible-storage)]. The binary derives plain-HTTP transport from the endpoint scheme and refuses an `AWS_ALLOW_HTTP` that disagrees [code: `crates/omnigraph-storage/src/binding.rs` L128 and L338–342@b2dbaff]. The harness waits on `GET /readyz`, never `/healthz`: the listener opens before graphs load, and a data request sent in between returns 503 `graph_unavailable` [docs: [deployment.md, "Use `GET /healthz`…" paragraph](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/deployment.md)] [code: `targets/03-omnigraph/witnessmark_omnigraph/part2.py`]. The S3 cluster lease is the documented 30 s default everywhere except O4, which shortens it to 2 s so that a paused owner can be replaced within the test; each run records `cluster_lease_seconds`. An owner stops every storage write once no heartbeat is answered for two thirds of a lease [docs: [storage-failures.md](https://github.com/ModernRelay/omnigraph/blob/b2dbaff7584eb849a98fa139876e0ae474e929ea/docs/user/operations/storage-failures.md#restart-after-a-failure)], and with the 2 s lease the proxy run of batch `m4c-20261115T165831Z` failed at 205,824 of 512,000 padding edges with `storage mutation admission is closed` [measured: `20261115T171130Z-e052669e`]. |
| FalkorDB | 6.0.4 by digest (master §7.2). The O1 `GRAPH.COPY` curve runs with `appendonly yes` and `appendfsync always`, the conditions S28 was measured under, and restores the container's own settings afterwards; the run records both. Batch 2's first attempt ran on the baseline's `appendonly no` and came out 61%, 49% and 57% faster than S28 at 32k, 128k and 512k (64.3, 279.2 and 1,025.1 ms against 165, 546 and 2,400), outside the ±50% band at two of three sizes, so the batch stopped [measured: `20261115T164756Z-236def5c`]. A scratch check of the same curve under S28's persistence gave 106.9, 359.3 and 1,600.3 ms, inside the band at all three [measured: scratch, not part of a batch]. The difference is the persistence setting [inference from that check]. |
| Neo4j | 5.26.2 (master §7.3) |
| Clients | The core runner: standard-library HTTP for Omnigraph and Neo4j, RESP for FalkorDB |

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
| B2 | Claim-race tables for O2a to O2c and O3 |
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

**Provenance.** Five batches on this host (Windows 11, 11th Gen i5-11320H, 8 logical cores, 23.8 GB; Docker VM 8 CPUs, 11.6 GB), all with a clean tree. Every number below is [measured] and comes from a report regenerated from `evidence/` and cmp-verified. Nothing was re-run to change a result: each re-run followed a harness fix that was committed first, and the earlier runs stay in `evidence/` and in their reports.

| Batch | Report | Harness commit | What it holds |
|---|---|---|---|
| `m4-20261115T153804Z` | [evidence/M4_OMNIGRAPH_B1.md](../../evidence/M4_OMNIGRAPH_B1.md) | `46adb1d` | the first full batch: 13 commands, 7 failed on harness problems |
| `m4b-20261115T164749Z` | [evidence/M4_OMNIGRAPH_B2.md](../../evidence/M4_OMNIGRAPH_B2.md) | `48737aa` | stopped after one command: the FalkorDB sanity band was not met |
| `m4c-20261115T165831Z` | [evidence/M4_OMNIGRAPH_B3.md](../../evidence/M4_OMNIGRAPH_B3.md) | `8f7bb3b` | two failed O1 runs, then the batch driver crashed |
| `m4d-20261115T172246Z` | [evidence/M4_OMNIGRAPH.md](../../evidence/M4_OMNIGRAPH.md) | `2a02bd8` | the main batch: O1 on both builds and three storages, O4, O5; 13 of 13 commands exit 0 |
| `m4e-20261115T183929Z` | [evidence/M4_OMNIGRAPH_B4.md](../../evidence/M4_OMNIGRAPH_B4.md) | `8bc5fd3` | re-run of the I6 controls (6 runs) and O4 (4 runs), after two checks in `m4d` proved weak; 11 of 11 commands exit 0 |

**Why there are five batches.**

| Batch | Cause | Where |
|---|---|---|
| `m4` (batch 1) | Seven runs failed on harness problems, none a finding. (P1) `UnboundLocalError` in the FalkorDB curve: `o1-stable-local`, after its Omnigraph curve had finished but before its manifest was written, so that curve's data was lost. (P2) every MinIO and proxy run, O1 and O4, both builds, failed with `storage_root_invalid`: the Omnigraph image had no CA bundle, which the binaries need to build their S3 client (`ca-certificates`, as upstream's Dockerfile installs). Fixed in `48737aa`, with two more found while proving it: the harness waited on `/healthz` before the graph had loaded, and the delay proxy rewrote the `Content-Length` of `HEAD` replies to 0 (`bfdec20`). The same commit made the O4 labels honest (below) | `m4b` |
| `m4b` | The FalkorDB `GRAPH.COPY` curve came in 61% and 57% below S28 at 32k and 512k (and 49% below at 128k) with the baseline's `appendonly no`. S28 was measured with `appendfsync always`; a scratch check under that setting gave 106.9, 359.3 and 1,600.3 ms, inside the band at all three. The curve now sets and records S28's persistence and restores the container's own (`8f7bb3b`). The batch stopped by rule, as master §6.5 says | `m4c` |
| `m4c` | Two problems. The 2 s S3 cluster lease that O4 needs for a fast takeover was applied to O1 as well; an owner stops all storage writes when no heartbeat is answered for two thirds of a lease, and the proxy run failed with `storage mutation admission is closed` part-way through loading 512k edges (`20261115T171130Z-e052669e`). Separately, the batch driver died printing a log line with a character its console encoding could not hold, so commands 4 to 13 never ran. Lease fixed in `2a02bd8`; the driver is untracked and was fixed under `.state` | `m4d` |
| `m4d` → `m4e` | Two checks did not check what they claimed. I6a: the branch was cut 40 ms after the ledger writer started, before its first append on a slow store, so all six O1 runs hold an empty prefix, which is trivially gapless. O4: the integrity scan went through the stale server, which stops itself after its admission is taken over, so every S3 cell read "not checked". Fixed in `8bc5fd3` | `m4e` |

**Commit `bfdec20` carries a `Co-Authored-By` trailer by mistake.** The instruction for this work is no attribution line; the trailer was added without noticing. It is kept rather than rewritten because the evidence records harness commit hashes, and an amend or rebase would change them. Every other commit since `0f22a9b` is authored by the maintainer alone, with no attribution line (audited with `git log` on 2026-11-15).

**Batch 1's failures are cited from its driver log.** Its failed commands are in `.state/scratch/m4-batch/m4-20261115T153804Z/driver.log` (kept locally, not committed). Exit codes in command order: `baselines-up` 0; `o1-stable-local` 1, `o1-stable-minio` 1, `o1-stable-proxy` 1; `o1-edge-local` 0, `o1-edge-minio` 1, `o1-edge-proxy` 1; `o4-stable-local` 0, `o4-stable-minio` 1, `o4-edge-local` 0, `o4-edge-minio` 1; `o5-stable-local` 0, `o5-edge-local` 0. The driver also wrote an `ERROR.md` for each failed command under `evidence/omnigraph/errors/`. Those notes recorded the host Python's path under the user's home folder, so they were moved out of `evidence/` unedited, to `.state/scratch/m4-batch/m4-20261115T153804Z/driver-errors/`, instead of being committed. The in-run `ERROR.md` files, which are redacted, stay in the run folders and are listed in the first report's "Runs that did not complete" table. The driver now redacts the command and tracebacks (batches 2 and 3 have their notes in `evidence/omnigraph/errors/`). The failed O1 run of `m4c` on MinIO (`20261115T170604Z-7d473a53`, `Remote end closed connection without response` on the third 512k create) is treated as an observed unknown outcome: Docker emitted no `oom` event, the server container was alive until the harness stopped it, and the VM had 11.6 GB. No server log survives, so the cause is [inference]: the same lease setting, because after the successor takes over a stale server in `m4e` also closes connections without a reply, and the identical run completed under the 30 s lease in `m4d` (`20261115T173025Z-fc74457b`).

### Controls

Controls come before findings.

| Control | Result | Run |
|---|---|---|
| FalkorDB `GRAPH.COPY` against S28 (the exit criterion, master §12) | **met**: 95.3 ms against 165 at 32k (-42%), 441.7 against 546 at 128k (-19%), 1,820.0 against 2,400 at 512k (-24%); all inside ±50%. Run under `appendonly yes`, `appendfsync always`, the conditions S28 was measured under | `20261115T172253Z-0adb5788` (`m4d`) |
| I6a, ledger prefix (`m4e`, branch cut after 5 of 20 appends) | gapless and non-empty in 6 of 6 runs: 5 of 20 entries on the branch. `m4d` is superseded for I6a: its six runs show an empty prefix, so I6a was not exercised there | `20261115T183931Z-fa543284`, `20261115T183939Z-2b18faf7`, `20261115T183955Z-401500b4`, `20261115T184035Z-505c2756`, `20261115T184042Z-d51c234e`, `20261115T184058Z-df6399b2` |
| I6b, isolation (`m4d` and `m4e`) | held in 12 of 12 runs: a branch write was invisible on main and the reverse | same, and the six `m4d` O1 runs |
| Part 1 sequential controls (O2a, O2c, O3, O6; M1 claim controls) | met on both builds, as recorded in §3 before M4 | see §3 |

### Results

| Scenario | v0.15.0 | edge-b2dbaff | Verdict |
|---|---|---|---|
| O1, create time, local root | 6.0 to 8.2 ms across n = 32k, 128k, 512k and s = 0, 4, 16, 64 siblings; reader stall 0 to 0.66 ms (`20261115T172253Z-0adb5788`) | 5.4 to 11.2 ms; stall 0 to 0.75 ms (`20261115T175653Z-12eb6ff6`) | observed: no growth with n or s at these sizes |
| O1, create time, MinIO | 36.2 to 70.9 ms; stall 27 to 60 ms (`20261115T173025Z-fc74457b`) | 37.4 to 88.6 ms; stall 28 to 81 ms (`20261115T180251Z-742224c3`) | observed: no growth with n; no clear growth with s |
| O1, object-store traffic through the 17 ms proxy, one create + delete | 34 to 39 requests at every cell; GET response bytes 58,335 (32k, s=0) to 418,639 (512k, s=0), and 137,966 at 32k, s=64 (`20261115T173716Z-d303435d`) | 34 to 37 requests; GET response bytes 58,667 to 421,977 at s=0 (`20261115T181001Z-adf60896`) | observed: requests constant, bytes grow with n and with s |
| O1, copy weight (create, claim, score, discard; one sample per size) | local 87.2, 90.0, 200.6 ms; MinIO 248.1, 274.9, 578.8 ms | local 83.7, 115.1, 195.7 ms; MinIO 2,111.2 (an outlier), 319.1, 576.7 ms | observed |
| O1, FalkorDB `GRAPH.COPY` (`20261115T172253Z-0adb5788`) | server-wide stop: an unrelated reader's longest gap was 95.1, 441.7 and 1,819.9 ms at 32k, 128k, 512k, equal to the copy; an unrelated writer's 95.3, 419.2 and 1,799.0 ms; delete 8.2 to 8.9 ms; memory delta 3.6, 9.3, 47.2 MB; AOF 50.8 to 101.4 MB | not applicable | curve (I6c) |
| O4, local root | the successor never became ready in 6 of 6 cells (the local lock is unleased [docs]); A's write was acknowledged and present in 6 of 6; none missing (`20261115T184136Z-24a2c040`) | same, 6 of 6 (`20261115T184426Z-ba1673ab`) | NOT_EXERCISED (harness gap) |
| O4, MinIO, leased takeover | the successor became ready in 6 of 6 cells; A's write was acknowledged in 0 of 6; B's write was acknowledged and present in 3 of 3; none missing (`20261115T184233Z-3a4a4f31`) | same: ready 6 of 6; A 0 of 6; B 3 of 3 present (`20261115T184523Z-2ae7e967`) | BOUNDARY (stable); NOT_EXERCISED (edge): the fence was not engaged |
| O5, read your writes, local root, second server | seen on the first poll; window 1,523.8 ms, including stopping A and starting B (`20261115T183504Z-eb41bb89`) | seen on the first poll; 1,334.6 ms (`20261115T183511Z-4d593c85`) | observed, 2 of 2 |

### O4 labelling, checked against the pinned docs

Batch 1 labelled every O4 cell BOUNDARY with the reason "the pinned server exposes no branch writer-claim route". The reason is true [docs: troubleshooting.md "Writer epoch" at `b2dbaff`; code: no claim call in `omnigraph-server`, `omnigraph-cli` or `omnigraph-cluster` at `b2dbaff`], but the label was a conclusion the cells did not earn. The documented way to engage the fence is a claim by an embedding program (`Omnigraph::claim_branch_writer`), and the RFC's server claim of `main` is its rollout phase 3, not shipped at the pin. The harness drives the published binaries and performs neither step. For a local root the documented ownership transfer (stop the previous owner, then `force-unlock` its exact lock id) is also a step the harness did not perform, because A was paused, not terminal. These are harness gaps, not boundaries of Omnigraph, so since `48737aa` the cells are classified from what happened:

- **NOT_EXERCISED**: the successor did not become ready (all local cells), or it did on the edge build but `main` was never claimed, so the fence acceptance criteria could not apply.
- **BOUNDARY**: only a real failover on v0.15.0, whose documented deployment rule is its protection.

No cell is a fence pass or a fence failure. The batch-1 BOUNDARY labels are marked "first-version label, superseded" in its report.

### Findings

Each is [measured] with the run id; causes are [code], [docs] or [inference] as marked.

1. **Creating a branch took 5 to 11 ms on a local root and 36 to 89 ms on MinIO, and did not grow with graph size (32k to 512k nodes, one edge each) or with 0 to 64 live sibling branches**, on both builds (run ids in the results table). The reader's longest gap beyond its baseline was under 1 ms locally and 27 to 81 ms on MinIO. FalkorDB's `GRAPH.COPY` of the same shapes took 95 to 1,820 ms and stopped every reader and writer on the server for the whole copy (`20261115T172253Z-0adb5788`). The two sides differ in storage, durability and what a copy is, so this compares a primitive's cost on this host, not two products.
2. **The bytes a create and a delete move grow with n and with s even though the request count does not.** Through the 17 ms proxy, GET response bytes at s=0 grew from 58,335 to 418,639 between 32k and 512k nodes, and at 32k from 58,335 to 137,966 between 0 and 64 siblings, while requests stayed at 34 to 39 (`20261115T173716Z-d303435d`, `20261115T181001Z-adf60896`). [inference] The reads follow the number of table versions and branches, not the row count. #642 describes work that grows with live sibling branches; at this catalog width (a few tables, not #642's 121) the growth is in bytes, and no growth in time showed at 0 to 64 siblings. Whether a wider catalog changes that is [unmeasured].
3. **After the successor took over an S3 root, the stale server's writes were refused by its own storage layer in 12 of 12 cells, on both builds.** Its replies were `internal` ("storage mutation was fenced while this request was in flight; it may still land"), `service_unavailable` ("server operation admission is closed") or a closed connection (`20261115T184233Z-3a4a4f31`, `20261115T184523Z-2ae7e967`). None of its writes appears in the graph, B's three acknowledged writes per build are all present, and no acknowledged write is missing. [docs] This is the cluster lease: an owner stops its storage writes when no heartbeat is answered for two thirds of a lease (storage-failures.md). It is not the writer epoch fence, which was not engaged (no claim), and the v0.15.0 cells share the behaviour. The stable release's lease held in these six cells.
4. **One `m4d` cell is unexplained.** In v0.15.0 on MinIO, phase p2 variant b, A's write was acknowledged and B's was acknowledged (`20261115T183001Z-3dcbea3c`). The scan in that batch went through A and failed, so whether both rows persisted is [unmeasured]. The same cell in `m4e` (`20261115T184233Z-3a4a4f31`) did not reproduce it: A's write was refused. The pause offsets are timings and so vary between runs; one cell is not a rate.
5. **Cross-process visibility on a local root took 1.3 to 1.5 s** from A's acknowledgement to the first successful read on a second server (`20261115T183504Z-eb41bb89`, `20261115T183511Z-4d593c85`). The window includes stopping A and starting B, so it bounds the process turnover and says nothing about a concurrently running second reader.
6. **The 2 s lease is a hazard for anything that is not a failover test.** Under load and through the 17 ms proxy, a 2 s lease closed storage admission mid-load (`20261115T171130Z-e052669e`). The harness uses the 30 s default outside O4.
7. **The stable and edge builds do not differ on O1 or O5** beyond this host's run-to-run spread.

**Credit.** On this host, with these shapes, branch creation in Omnigraph is cheap and flat in graph size, the I6a prefix and I6b isolation controls hold on both builds and all three storages, and the lease refused every stale write the harness produced in the leased-takeover cells without losing an acknowledged one.

### Not run, and open

- **Not run in any batch:** O2 (the 50-client claim races), O3 (merge of 50 agent branches) and O6 (traversal parity) beyond their Part 1 sequential controls; O5 on MinIO; the memory delta of Omnigraph's server (recorded in each sample's `rss_*` fields, not tabulated); a catalog-width axis for O1 (finding 2).
- **Open harness gap, the fence:** an epoch claim by an embedding program (a small Rust program on the pinned crate, or any later release that adds a claim route) is needed before O4 can pass or fail anything about the writer epoch fence. Until then the pass criteria, the boundary probes (branch create or delete, cleanup, optimize), several failovers in a row and simultaneous claims are all NOT_EXERCISED.
- **Open harness gap, local roots:** a variant that stops A, reads its lock id from `cluster status --json`, and runs `cluster force-unlock` before starting B would exercise the documented transfer. A paused A holding the lock is the case the docs say an operator must not unlock.
- **MinIO is not qualified.** The storage guide requires every S3-compatible store to honour `If-None-Match` and `If-Match`, and qualifies only RustFS. These runs raised no double publish, which is not a qualification of MinIO's conditional writes.
- **The unexplained cell** in finding 4 and the unrecoverable cause of the `m4c` MinIO failure (no server log was captured on failure) are open. Capturing the server's log in a failed run's evidence would close the second.
- **I6a at other branch points** (the branch is cut after 5 of 20 appends only).
