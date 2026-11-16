# M5: Omnigraph: batch `m5b-20261115T230235Z`

Regenerated from `evidence/` by `python wm.py report --memory`. Do not edit by hand.

- Harness commit: `6a15b9c950505f412ddd17891f3b2f16be3bc8e5` (dirty: false)
- Host: Windows-11-10.0.26300-SP0; 11th Gen Intel(R) Core(TM) i5-11320H @ 3.20GHz; 8 logical cores; 23.8 GB
- Docker: 29.9.3; VM limits 8 CPUs, 11.6 GB
- Runs: 35 (0 races, 0 case suites, 4 visibility, 6 cost curves, 0 failover matrices, 0 I6 control runs)
- Runs added in M5: 18 thread-mode races, 3 O2b cost curves, 2 O6 parity runs, 2 O4 clean-stop transfers
- Harness commits in this batch: `6a15b9c`

## Runs that did not complete

[measured] These runs wrote their planned manifest and then stopped; no result was inferred from them.

| Build | Storage | Scenario | Error | Run |
|---|---|---|---|---|
| v0.15.0 | local | o1.branch_cost | RuntimeError: wm-o1-unrelated-reader failed: unknown connection: [WinError 10048] Only one usage of each socket address (protocol/network address/port) is normally permitted | `20261115T232536Z-6d1be538` |

## Baseline claim controls (thread mode)

The M1 control matrix, run in this batch. FalkorDB 6.0.4 is the negative control; Neo4j 5.26.2's naive shapes are the positive control (master blueprint section 6.2).

| Engine | Build | Storage | Scenario | Role | Clients | Gate (ms) | Sequential control | Role control | Valid trials | Violating trials | Outcomes ok / fail / unknown (valid trials) | Release spread p50 / max (ms) | Verdict | Run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| falkordb | 6.0.4 (graph module 60004) | – | claim.state.naive | negative | 50 | off | met | met | 20 of 20 | 0 of 20 | 20 / 980 / 0 | 4.96 / 6.95 | PASS | `20261115T231353Z-aacd795d` |
| falkordb | 6.0.4 (graph module 60004) | – | claim.lease.naive | negative | 50 | off | met | met | 20 of 20 | 0 of 20 | 20 / 980 / 0 | 4.97 / 8.40 | PASS | `20261115T231355Z-e3f43105` |
| falkordb | 6.0.4 (graph module 60004) | – | counter.direct | negative | 50 | off | met | met | 20 of 20 | 0 of 20 | 890 / 110 / 0 | 4.12 / 7.21 | PASS | `20261115T231358Z-4ac87436` |
| falkordb | 6.0.4 (graph module 60004) | – | counter.via_with | negative | 50 | off | met | met | 20 of 20 | 0 of 20 | 919 / 81 / 0 | 4.80 / 8.01 | PASS | `20261115T231400Z-99a48567` |
| falkordb | 6.0.4 (graph module 60004) | – | disjoint.set | negative | 50 | off | met | met | 20 of 20 | 0 of 20 | 919 / 81 / 0 | 5.07 / 7.96 | PASS | `20261115T231402Z-1d44e6d1` |
| neo4j | 5.26.2 community | – | claim.state.naive | positive | 50 | off | met | met | 20 of 20 | 20 of 20 | 179 / 821 / 0 | 7.86 / 18.00 | KNOWN_DEVIATION | `20261115T231405Z-2793c658` |
| neo4j | 5.26.2 community | – | claim.state.lock_first | negative | 50 | off | met | met | 20 of 20 | 0 of 20 | 20 / 980 / 0 | 7.47 / 29.84 | PASS | `20261115T231414Z-902d7816` |
| neo4j | 5.26.2 community | – | claim.lease.naive | positive | 50 | off | met | met | 20 of 20 | 20 of 20 | 169 / 831 / 0 | 7.45 / 12.01 | KNOWN_DEVIATION | `20261115T231419Z-2365e346` |
| neo4j | 5.26.2 community | – | claim.lease.lock_first | negative | 50 | off | met | met | 20 of 20 | 0 of 20 | 20 / 980 / 0 | 8.96 / 17.93 | PASS | `20261115T231425Z-f5bfeba7` |
| neo4j | 5.26.2 community | – | counter.direct | negative | 50 | off | met | met | 20 of 20 | 0 of 20 | 1000 / 0 / 0 | 7.02 / 12.56 | PASS | `20261115T231431Z-36b7ecf4` |
| neo4j | 5.26.2 community | – | counter.via_with | positive | 50 | off | met | met | 20 of 20 | 20 of 20 | 1000 / 0 / 0 | 7.52 / 14.89 | KNOWN_DEVIATION | `20261115T231439Z-ff2bf67f` |
| neo4j | 5.26.2 community | – | disjoint.set | negative | 50 | off | met | met | 20 of 20 | 0 of 20 | 1000 / 0 / 0 | 7.71 / 30.08 | PASS | `20261115T231445Z-cde1d9cd` |

## Omnigraph races (thread mode)

| Engine | Build | Storage | Scenario | Role | Clients | Gate (ms) | Sequential control | Role control | Valid trials | Violating trials | Outcomes ok / fail / unknown (valid trials) | Release spread p50 / max (ms) | Verdict | Run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| omnigraph | v0.15.0 | local | o2a.conditional_one_task.thread | negative | 50 | 55 | met | met | 20 of 20 | 0 of 20 | 20 / 980 / 0 | 8.42 / 11.17 | PASS | `20261115T231454Z-7f2e75a3` |
| omnigraph | edge-b2dbaff | local | o2a.conditional_one_task.thread | negative | 50 | 55 | met | met | 20 of 20 | 0 of 20 | 20 / 980 / 0 | 7.29 / 17.01 | PASS | `20261115T231539Z-c7be08c9` |
| omnigraph | v0.15.0 | local | o2c.cardinality_one_task.thread | negative | 50 | 55 | met | met | 20 of 20 | 0 of 20 | 20 / 980 / 0 | 8.22 / 18.90 | PASS | `20261115T231626Z-b28d5aff` |
| omnigraph | edge-b2dbaff | local | o2c.cardinality_one_task.thread | negative | 50 | 55 | met | met | 20 of 20 | 0 of 20 | 20 / 980 / 0 | 9.43 / 19.66 | PASS | `20261115T231715Z-071a8831` |
| omnigraph | v0.15.0 | local | o3.merge_agents.thread | negative | 50 | 55 | met | met | 20 of 20 | 0 of 20 | 20 / 980 / 0 | 6.69 / 15.51 | PASS | `20261115T231810Z-701d1d1d` |
| omnigraph | edge-b2dbaff | local | o3.merge_agents.thread | negative | 50 | 55 | met | met | 20 of 20 | 0 of 20 | 20 / 980 / 0 | 8.98 / 13.88 | PASS | `20261115T232110Z-c67ea540` |

### Race outcomes by error type

Counted from `history.jsonl` over every race trial of the run.

| Engine | Build | Scenario | Race operations | Acknowledged | Refusals by error type (count) | Unknown | Run |
|---|---|---|---|---|---|---|---|
| omnigraph | v0.15.0 | o2a.conditional_one_task.thread | 1000 | 20 | `precondition_failure` 533; `CardinalityViolation` 447 | 0 | `20261115T231454Z-7f2e75a3` |
| omnigraph | edge-b2dbaff | o2a.conditional_one_task.thread | 1000 | 20 | `CardinalityViolation` 496; `precondition_failure` 484 | 0 | `20261115T231539Z-c7be08c9` |
| omnigraph | v0.15.0 | o2c.cardinality_one_task.thread | 1000 | 20 | `CardinalityViolation` 599; `conflict` 381 | 0 | `20261115T231626Z-b28d5aff` |
| omnigraph | edge-b2dbaff | o2c.cardinality_one_task.thread | 1000 | 20 | `CardinalityViolation` 980 | 0 | `20261115T231715Z-071a8831` |
| omnigraph | v0.15.0 | o3.merge_agents.thread | 1000 | 20 | `CardinalityViolation` 980 | 0 | `20261115T231810Z-701d1d1d` |
| omnigraph | edge-b2dbaff | o3.merge_agents.thread | 1000 | 20 | `CardinalityViolation` 980 | 0 | `20261115T232110Z-c67ea540` |

### Release spread, thread mode (valid trials)

| Engine | Scenarios | Valid trials | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | 1.5 × p99, rounded up (ms) |
|---|---|---|---|---|---|---|---|
| falkordb | claim.lease.naive, claim.state.naive, counter.direct, counter.via_with, disjoint.set | 100 | 4.89 | 7.21 | 8.12 | 8.40 | 13 |
| neo4j | claim.lease.lock_first, claim.lease.naive, claim.state.lock_first, claim.state.naive, counter.direct, counter.via_with, disjoint.set | 140 | 7.59 | 16.00 | 29.84 | 30.08 | 45 |
| omnigraph | o2a.conditional_one_task.thread, o2c.cardinality_one_task.thread, o3.merge_agents.thread | 120 | 8.30 | 14.81 | 18.90 | 19.66 | 29 |

## O2b disjoint-claim cost curve

Measured repetitions only; warm-ups stay in the evidence and are left out here. This is the cost of documented behaviour, not a correctness verdict.

| Engine | Build | Storage | Gate (ms) | N | Valid / measured repetitions | Attempts, median [IQR] | Wasted attempts, median [IQR] | Attempts per agent, median / max (medians) | Time to all claimed, median [IQR] (ms) | Claim latency p50 / p99, medians (ms) | Holder check failed (measured repetitions) | Agents that did not claim (measured repetitions) | Run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| omnigraph | v0.15.0 | local | 55 | 1 | 5 / 5 | 1 [1–1] | 0 [0–0] | 1 / 1 | 51.67 [47.89–54.02] | 45.54 / 45.54 | 0 of 5 | 0 | `20261115T230248Z-b1c0842e` |
| omnigraph | v0.15.0 | local | 55 | 2 | 5 / 5 | 3 [3–3] | 1 [1–1] | 1.50 / 2 | 94.29 [86.07–98.52] | 36.65 / 42.02 | 0 of 5 | 0 | `20261115T230248Z-b1c0842e` |
| omnigraph | v0.15.0 | local | 55 | 5 | 5 / 5 | 15 [15–15] | 10 [10–10] | 3 / 5 | 277.72 [247.04–301.47] | 42.78 / 62.49 | 0 of 5 | 0 | `20261115T230248Z-b1c0842e` |
| omnigraph | v0.15.0 | local | 55 | 10 | 5 / 5 | 55 [55–55] | 45 [45–45] | 5.50 / 10 | 815.31 [792.44–876.30] | 75.28 / 109.44 | 0 of 5 | 0 | `20261115T230248Z-b1c0842e` |
| omnigraph | v0.15.0 | local | 55 | 25 | 5 / 5 | 325 [325–325] | 300 [300–300] | 13 / 25 | 4494.14 [4350.93–4628.76] | 170.06 / 278.46 | 0 of 5 | 0 | `20261115T230248Z-b1c0842e` |
| omnigraph | v0.15.0 | local | 55 | 50 | 5 / 5 | 1267 [1262–1268] | 1217 [1212–1218] | 25.50 / 49 | 23376.08 [22741.87–23757.86] | 478.64 / 772.92 | 0 of 5 | 1 (unknown) | `20261115T230248Z-b1c0842e` |
| omnigraph | edge-b2dbaff | local | 55 | 1 | 5 / 5 | 1 [1–1] | 0 [0–0] | 1 / 1 | 40.19 [35.48–48.43] | 34.97 / 34.97 | 0 of 5 | 0 | `20261115T230816Z-91a819a6` |
| omnigraph | edge-b2dbaff | local | 55 | 2 | 5 / 5 | 3 [3–3] | 1 [1–1] | 1.50 / 2 | 85.76 [80.75–101.96] | 36.77 / 37.30 | 0 of 5 | 0 | `20261115T230816Z-91a819a6` |
| omnigraph | edge-b2dbaff | local | 55 | 5 | 5 / 5 | 15 [15–15] | 10 [10–10] | 3 / 5 | 266.03 [242.16–281.99] | 48.69 / 57.17 | 0 of 5 | 0 | `20261115T230816Z-91a819a6` |
| omnigraph | edge-b2dbaff | local | 55 | 10 | 5 / 5 | 55 [55–55] | 45 [45–45] | 5.50 / 10 | 777.76 [749.30–819.11] | 69.58 / 92.45 | 0 of 5 | 0 | `20261115T230816Z-91a819a6` |
| omnigraph | edge-b2dbaff | local | 55 | 25 | 5 / 5 | 325 [325–325] | 300 [300–300] | 13 / 25 | 4464.95 [4279.24–4873.86] | 167.56 / 328.03 | 0 of 5 | 1 (unknown) | `20261115T230816Z-91a819a6` |
| omnigraph | edge-b2dbaff | local | 55 | 50 | 5 / 5 | 1259 [1249–1265] | 1209 [1199–1215] | 25.50 / 50 | 22517.02 [21516.86–22781.33] | 454.63 / 793.24 | 0 of 5 | 0 | `20261115T230816Z-91a819a6` |
| falkordb | 6.0.4 (graph module 60004) | – | 40 | 1 | 5 / 5 | 1 [1–1] | 0 [0–0] | 1 / 1 | 1.09 [0.92–1.12] | 1.09 / 1.09 | 0 of 5 | 0 | `20261115T231348Z-552b23e0` |
| falkordb | 6.0.4 (graph module 60004) | – | 40 | 2 | 5 / 5 | 2 [2–2] | 0 [0–0] | 1 / 1 | 1.24 [1.23–1.62] | 1.14 / 1.23 | 0 of 5 | 0 | `20261115T231348Z-552b23e0` |
| falkordb | 6.0.4 (graph module 60004) | – | 40 | 5 | 5 / 5 | 5 [5–5] | 0 [0–0] | 1 / 1 | 1.78 [1.69–1.84] | 1.47 / 1.62 | 0 of 5 | 0 | `20261115T231348Z-552b23e0` |
| falkordb | 6.0.4 (graph module 60004) | – | 40 | 10 | 5 / 5 | 10 [10–10] | 0 [0–0] | 1 / 1 | 2.69 [2.41–2.98] | 1.84 / 2.31 | 0 of 5 | 0 | `20261115T231348Z-552b23e0` |
| falkordb | 6.0.4 (graph module 60004) | – | 40 | 25 | 5 / 5 | 25 [25–25] | 0 [0–0] | 1 / 1 | 5.17 [5.11–6.06] | 3.03 / 4.33 | 0 of 5 | 0 | `20261115T231348Z-552b23e0` |
| falkordb | 6.0.4 (graph module 60004) | – | 40 | 50 | 5 / 5 | 50 [50–50] | 0 [0–0] | 1 / 1 | 9.80 [9.15–9.91] | 5.18 / 8.81 | 0 of 5 | 0 | `20261115T231348Z-552b23e0` |

## O6 traversal parity

| Build | Storage | Case | Query | Classification | Read errors | Run |
|---|---|---|---|---|---|---|
| v0.15.0 | local | sequential control | q_eligible | identical | none | `20261115T232412Z-8935cb2f` |
| v0.15.0 | local | sequential control | q_live | identical | none | `20261115T232412Z-8935cb2f` |
| v0.15.0 | local | trial 1 | q_eligible | identical | none | `20261115T232412Z-8935cb2f` |
| v0.15.0 | local | trial 1 | q_live | identical | none | `20261115T232412Z-8935cb2f` |
| v0.15.0 | local | trial 1 | q_live_open | identical | none | `20261115T232412Z-8935cb2f` |
| edge-b2dbaff | local | sequential control | q_eligible | identical | none | `20261115T232421Z-31c6fa46` |
| edge-b2dbaff | local | sequential control | q_live | identical | none | `20261115T232421Z-31c6fa46` |
| edge-b2dbaff | local | trial 1 | q_eligible | identical | none | `20261115T232421Z-31c6fa46` |
| edge-b2dbaff | local | trial 1 | q_live | identical | none | `20261115T232421Z-31c6fa46` |
| edge-b2dbaff | local | trial 1 | q_live_open | identical | none | `20261115T232421Z-31c6fa46` |

## O4 clean-stop local transfer

| Build | Storage | A write | A exit code | A killed / OOM | Admission released | Successor ready | B write | Integrity scan | Acknowledged writes missing | Fence | Classification | Reason | Run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v0.15.0 | local | ok | 0 | no / no | yes | yes | ok | ok | none | not engaged | OBSERVED | admission released; B started | `20261115T232518Z-4a2c639b` |
| edge-b2dbaff | local | ok | 0 | no / no | yes | yes | ok | ok | none | not engaged | OBSERVED | admission released; B started | `20261115T232527Z-f549fc44` |

## I6a and I6b controls

| Build | Storage | Source | I6a: branch prefix / main ledger | I6a gapless and non-empty | I6b isolation | Run |
|---|---|---|---|---|---|---|
| v0.15.0 | minio | end of O1 curve | 5 / 20 | yes | yes | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | proxy | end of O1 curve | 5 / 18 | yes | yes | `20261115T233710Z-d6e9001c` |
| edge-b2dbaff | local | end of O1 curve | 5 / 20 | yes | yes | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | minio | end of O1 curve | 5 / 20 | yes | yes | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | proxy | end of O1 curve | 5 / 18 | yes | yes | `20261116T001000Z-dedd3d1f` |

## O1 branch-creation cost

| Build | Storage | Nodes / edges | Siblings | Create median [IQR] (ms) | Stall median (ms) | Reader p99 before / during (ms) | Merge / delete median (ms) | Object requests / bytes, one create + delete | Run |
|---|---|---|---|---|---|---|---|---|---|
| v0.15.0 | minio | 32000 / 32000 | 0 | 70.68 [69.05–80.45] | 52.40 | 26.19 / 87.93 | 16.42 / 36.15 | – | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | minio | 32000 / 32000 | 4 | 68.97 [65.49–88.01] | 59.44 | 23.03 / 88.46 | 15.51 / 35.35 | – | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | minio | 32000 / 32000 | 16 | 60.90 [55.76–80.91] | 46.96 | 27.36 / 62.41 | 20.98 / 41.74 | – | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | minio | 32000 / 32000 | 64 | 68.01 [61.04–71.35] | 56.84 | 27.75 / 73.20 | 20.81 / 46.42 | – | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | minio | 128000 / 128000 | 0 | 57.98 [56.37–76.70] | 44.36 | 26.92 / 60.22 | 22.11 / 42.61 | – | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | minio | 128000 / 128000 | 4 | 58.51 [54.04–73.18] | 46.92 | 27.99 / 64.19 | 23.01 / 40.78 | – | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | minio | 128000 / 128000 | 16 | 58.93 [50.92–65.16] | 39.86 | 30.47 / 59.05 | 19.27 / 37.07 | – | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | minio | 128000 / 128000 | 64 | 63.23 [52.03–72.83] | 48.38 | 27.19 / 63.60 | 23.93 / 45.26 | – | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | minio | 512000 / 512000 | 0 | 51.37 [48.33–55.20] | 39.26 | 29.61 / 53.16 | 26.24 / 39.67 | – | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | minio | 512000 / 512000 | 4 | 52.30 [51.34–54.58] | 44.45 | 30.23 / 59.24 | 28.69 / 40.81 | – | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | minio | 512000 / 512000 | 16 | 67.53 [65.65–75.89] | 59.72 | 27.79 / 73.73 | 29.51 / 43.03 | – | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | minio | 512000 / 512000 | 64 | 54.87 [49.68–56.15] | 41.93 | 24.87 / 58.15 | 41.58 / 42.70 | – | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | proxy | 32000 / 32000 | 0 | – | 391.14 | 111.77 / 519.74 | 416.54 / 611.98 | 38 / 62885 | `20261115T233710Z-d6e9001c` |
| v0.15.0 | proxy | 32000 / 32000 | 4 | – | 305.21 | 109.11 / 431.64 | 373.45 / 571.40 | 34 / 66760 | `20261115T233710Z-d6e9001c` |
| v0.15.0 | proxy | 32000 / 32000 | 16 | – | 303.46 | 107.91 / 428.65 | 375.39 / 577.03 | 38 / 82812 | `20261115T233710Z-d6e9001c` |
| v0.15.0 | proxy | 32000 / 32000 | 64 | – | 304.67 | 108.86 / 432.40 | 391.10 / 569.86 | 34 / 141422 | `20261115T233710Z-d6e9001c` |
| v0.15.0 | proxy | 128000 / 128000 | 0 | – | 397.95 | 107.37 / 527.77 | 417.46 / 617.58 | 34 / 123213 | `20261115T233710Z-d6e9001c` |
| v0.15.0 | proxy | 128000 / 128000 | 4 | – | 304.43 | 109.32 / 429.87 | 379.15 / 577.04 | 34 / 128191 | `20261115T233710Z-d6e9001c` |
| v0.15.0 | proxy | 128000 / 128000 | 16 | – | 303.67 | 107.62 / 431.27 | 385.26 / 579.51 | 34 / 143139 | `20261115T233710Z-d6e9001c` |
| v0.15.0 | proxy | 128000 / 128000 | 64 | – | 309.25 | 108.63 / 435.79 | 390.71 / 582.28 | 34 / 202853 | `20261115T233710Z-d6e9001c` |
| v0.15.0 | proxy | 512000 / 512000 | 0 | – | 386.98 | 108.43 / 512.90 | 484.28 / 625.19 | 37 / 422810 | `20261115T233710Z-d6e9001c` |
| v0.15.0 | proxy | 512000 / 512000 | 4 | – | 315.23 | 109.59 / 449.16 | 428.77 / 587.88 | 37 / 427788 | `20261115T233710Z-d6e9001c` |
| v0.15.0 | proxy | 512000 / 512000 | 16 | – | 299.15 | 109.20 / 424.14 | 434.58 / 582.21 | 37 / 442741 | `20261115T233710Z-d6e9001c` |
| v0.15.0 | proxy | 512000 / 512000 | 64 | – | 305.73 | 105.28 / 431.47 | 441.08 / 585.08 | 37 / 502451 | `20261115T233710Z-d6e9001c` |
| edge-b2dbaff | local | 32000 / 32000 | 0 | 8.34 [8.05–9.56] | 0.44 | 23.01 / 10.86 | 10.07 / 5.14 | – | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | local | 32000 / 32000 | 4 | 8.30 [6.05–8.89] | 0 | 17.45 / 10.93 | 8.87 / 5.29 | – | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | local | 32000 / 32000 | 16 | 9.01 [7.79–9.71] | 0.92 | 25.80 / 11.91 | 13.82 / 5.28 | – | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | local | 32000 / 32000 | 64 | 10.13 [8.24–10.41] | 0.04 | 19.20 / 10.64 | 9.51 / 7.15 | – | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | local | 128000 / 128000 | 0 | 9.68 [8.91–11.32] | 0.57 | 27.51 / 13.07 | 10.09 / 5.76 | – | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | local | 128000 / 128000 | 4 | 9.75 [8.23–11.89] | 0 | 20.86 / 14.79 | 10.20 / 6.23 | – | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | local | 128000 / 128000 | 16 | 10.64 [10.21–10.84] | 0 | 22.38 / 11.24 | 10.41 / 6.05 | – | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | local | 128000 / 128000 | 64 | 9.73 [9.38–12.54] | 1.30 | 20.40 / 14.58 | 23.37 / 5.88 | – | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | local | 512000 / 512000 | 0 | 9.21 [8.63–9.97] | 0.29 | 26.54 / 11.60 | 13.71 / 6.75 | – | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | local | 512000 / 512000 | 4 | 14.62 [12.63–39.17] | 3.54 | 28.96 / 28.48 | 22.24 / 6.75 | – | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | local | 512000 / 512000 | 16 | 10.64 [10.63–11.83] | 0 | 20.45 / 11.34 | 22.25 / 6.17 | – | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | local | 512000 / 512000 | 64 | 12.19 [11.49–13.50] | 4.24 | 30.71 / 19.55 | 26.23 / 9.10 | – | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | minio | 32000 / 32000 | 0 | 143.55 [129.35–148.03] | 107.13 | 37.99 / 134.34 | 18.01 / 42.15 | – | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | minio | 32000 / 32000 | 4 | 113.21 [104.93–135.97] | 72.17 | 36.15 / 98.08 | 45.76 / 79.48 | – | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | minio | 32000 / 32000 | 16 | 102.28 [88.04–114.11] | 72.67 | 28.47 / 92.38 | 43.22 / 82.14 | – | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | minio | 32000 / 32000 | 64 | 114.22 [108.59–116.74] | 93.93 | 37.03 / 131.11 | 48.14 / 56.20 | – | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | minio | 128000 / 128000 | 0 | 91.61 [86.00–109.22] | 63.94 | 39.53 / 88.08 | 29.59 / 62.21 | – | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | minio | 128000 / 128000 | 4 | 57.30 [50.43–60.92] | 38.82 | 26.83 / 59.97 | 35.76 / 57.85 | – | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | minio | 128000 / 128000 | 16 | 55.82 [53.31–79.75] | 48.69 | 28.84 / 64.25 | 26.63 / 35.04 | – | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | minio | 128000 / 128000 | 64 | 75.69 [57.98–108.96] | 49.90 | 25.03 / 75.48 | 44.58 / 71.16 | – | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | minio | 512000 / 512000 | 0 | 60.60 [52.71–70.07] | 47.13 | 27.21 / 67.41 | 27.91 / 42.45 | – | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | minio | 512000 / 512000 | 4 | 75.06 [59.06–77.26] | 62.84 | 26.64 / 79.55 | 34.13 / 44.66 | – | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | minio | 512000 / 512000 | 16 | 73.19 [54.11–74.42] | 56.96 | 27.84 / 71.47 | 30.43 / 63.91 | – | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | minio | 512000 / 512000 | 64 | 59.57 [51.79–69.77] | 45.53 | 29.30 / 60.48 | 29.21 / 41.49 | – | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | proxy | 32000 / 32000 | 0 | – | 396.11 | 111.07 / 519.08 | 419.30 / 613.67 | 36 / 62811 | `20261116T001000Z-dedd3d1f` |
| edge-b2dbaff | proxy | 32000 / 32000 | 4 | – | 304.20 | 108.74 / 427.09 | 378.29 / 585.36 | 38 / 68317 | `20261116T001000Z-dedd3d1f` |
| edge-b2dbaff | proxy | 32000 / 32000 | 16 | – | 303.28 | 108.39 / 427.79 | 376.16 / 582.10 | 34 / 82387 | `20261116T001000Z-dedd3d1f` |
| edge-b2dbaff | proxy | 32000 / 32000 | 64 | – | 314.10 | 108.69 / 443.24 | 395.52 / 579.63 | 34 / 143059 | `20261116T001000Z-dedd3d1f` |
| edge-b2dbaff | proxy | 128000 / 128000 | 0 | – | 384.16 | 110.03 / 512.13 | 430.76 / 620.72 | 34 / 123993 | `20261116T001000Z-dedd3d1f` |
| edge-b2dbaff | proxy | 128000 / 128000 | 4 | – | 308.40 | 107.52 / 435.86 | 377.96 / 574.51 | 34 / 129051 | `20261116T001000Z-dedd3d1f` |
| edge-b2dbaff | proxy | 128000 / 128000 | 16 | – | 313.85 | 108.57 / 441.90 | 383.83 / 577.01 | 34 / 144241 | `20261116T001000Z-dedd3d1f` |
| edge-b2dbaff | proxy | 128000 / 128000 | 64 | – | 309.29 | 112.04 / 435.48 | 377.92 / 585.89 | 34 / 204913 | `20261116T001000Z-dedd3d1f` |
| edge-b2dbaff | proxy | 512000 / 512000 | 0 | – | 391.22 | 112.02 / 519.15 | 473.79 / 631.96 | 37 / 425208 | `20261116T001000Z-dedd3d1f` |
| edge-b2dbaff | proxy | 512000 / 512000 | 4 | – | 307.25 | 109.12 / 437.76 | 445.33 / 591.57 | 37 / 430264 | `20261116T001000Z-dedd3d1f` |
| edge-b2dbaff | proxy | 512000 / 512000 | 16 | – | 304.93 | 108.77 / 433.09 | 443.91 / 584.73 | 37 / 445454 | `20261116T001000Z-dedd3d1f` |
| edge-b2dbaff | proxy | 512000 / 512000 | 64 | – | 306.50 | 109.81 / 434.58 | 431.03 / 589.58 | 37 / 506124 | `20261116T001000Z-dedd3d1f` |

### Unrelated graph during branch creation

| Build | Storage | Nodes / edges | Siblings | Unrelated reader stall median (ms) | Unrelated writer stall median (ms) | Run |
|---|---|---|---|---|---|---|
| v0.15.0 | minio | 32000 / 32000 | 0 | 40.64 | 66.96 | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | minio | 32000 / 32000 | 4 | 35.85 | 68.97 | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | minio | 32000 / 32000 | 16 | 24.19 | 60.90 | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | minio | 32000 / 32000 | 64 | 19.86 | 68.01 | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | minio | 128000 / 128000 | 0 | 16.53 | 57.98 | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | minio | 128000 / 128000 | 4 | 46.73 | 58.51 | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | minio | 128000 / 128000 | 16 | 44.41 | 42.48 | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | minio | 128000 / 128000 | 64 | 34.77 | 52.03 | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | minio | 512000 / 512000 | 0 | 50.59 | 51.37 | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | minio | 512000 / 512000 | 4 | 34.27 | 52.30 | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | minio | 512000 / 512000 | 16 | 15.60 | 67.53 | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | minio | 512000 / 512000 | 64 | 29.79 | 31.56 | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | proxy | 32000 / 32000 | 0 | 199.82 | 293.21 | `20261115T233710Z-d6e9001c` |
| v0.15.0 | proxy | 32000 / 32000 | 4 | 206.33 | 209.72 | `20261115T233710Z-d6e9001c` |
| v0.15.0 | proxy | 32000 / 32000 | 16 | 201.40 | 215.28 | `20261115T233710Z-d6e9001c` |
| v0.15.0 | proxy | 32000 / 32000 | 64 | 199.80 | 205.09 | `20261115T233710Z-d6e9001c` |
| v0.15.0 | proxy | 128000 / 128000 | 0 | 215.55 | 298.82 | `20261115T233710Z-d6e9001c` |
| v0.15.0 | proxy | 128000 / 128000 | 4 | 210.97 | 196.64 | `20261115T233710Z-d6e9001c` |
| v0.15.0 | proxy | 128000 / 128000 | 16 | 193.19 | 183.91 | `20261115T233710Z-d6e9001c` |
| v0.15.0 | proxy | 128000 / 128000 | 64 | 205.20 | 204.43 | `20261115T233710Z-d6e9001c` |
| v0.15.0 | proxy | 512000 / 512000 | 0 | 207.83 | 275.96 | `20261115T233710Z-d6e9001c` |
| v0.15.0 | proxy | 512000 / 512000 | 4 | 171.95 | 206.96 | `20261115T233710Z-d6e9001c` |
| v0.15.0 | proxy | 512000 / 512000 | 16 | 199.26 | 179.03 | `20261115T233710Z-d6e9001c` |
| v0.15.0 | proxy | 512000 / 512000 | 64 | 202.84 | 188.49 | `20261115T233710Z-d6e9001c` |
| edge-b2dbaff | local | 32000 / 32000 | 0 | 6.35 | 8.34 | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | local | 32000 / 32000 | 4 | 6.05 | 8.24 | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | local | 32000 / 32000 | 16 | 7.37 | 6.71 | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | local | 32000 / 32000 | 64 | 7.02 | 10.13 | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | local | 128000 / 128000 | 0 | 7.58 | 8.85 | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | local | 128000 / 128000 | 4 | 6.81 | 9.75 | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | local | 128000 / 128000 | 16 | 6.97 | 10.64 | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | local | 128000 / 128000 | 64 | 7.04 | 9.73 | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | local | 512000 / 512000 | 0 | 6.99 | 9.21 | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | local | 512000 / 512000 | 4 | 7.97 | 14.62 | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | local | 512000 / 512000 | 16 | 7.63 | 10.64 | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | local | 512000 / 512000 | 64 | 10.94 | 12.19 | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | minio | 32000 / 32000 | 0 | 49.82 | 143.55 | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | minio | 32000 / 32000 | 4 | 68.14 | 113.21 | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | minio | 32000 / 32000 | 16 | 23.74 | 81.61 | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | minio | 32000 / 32000 | 64 | 44.42 | 103.32 | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | minio | 128000 / 128000 | 0 | 86.00 | 80.67 | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | minio | 128000 / 128000 | 4 | 28.36 | 53.15 | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | minio | 128000 / 128000 | 16 | 11.50 | 55.82 | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | minio | 128000 / 128000 | 64 | 25.26 | 75.69 | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | minio | 512000 / 512000 | 0 | 43.17 | 50.68 | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | minio | 512000 / 512000 | 4 | 28.58 | 75.06 | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | minio | 512000 / 512000 | 16 | 15.90 | 67.12 | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | minio | 512000 / 512000 | 64 | 50.94 | 55.05 | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | proxy | 32000 / 32000 | 0 | 199.85 | 295.74 | `20261116T001000Z-dedd3d1f` |
| edge-b2dbaff | proxy | 32000 / 32000 | 4 | 198.48 | 220.97 | `20261116T001000Z-dedd3d1f` |
| edge-b2dbaff | proxy | 32000 / 32000 | 16 | 201.27 | 210.72 | `20261116T001000Z-dedd3d1f` |
| edge-b2dbaff | proxy | 32000 / 32000 | 64 | 207.11 | 231.96 | `20261116T001000Z-dedd3d1f` |
| edge-b2dbaff | proxy | 128000 / 128000 | 0 | 206.13 | 294.73 | `20261116T001000Z-dedd3d1f` |
| edge-b2dbaff | proxy | 128000 / 128000 | 4 | 214.48 | 235.67 | `20261116T001000Z-dedd3d1f` |
| edge-b2dbaff | proxy | 128000 / 128000 | 16 | 206.77 | 221.40 | `20261116T001000Z-dedd3d1f` |
| edge-b2dbaff | proxy | 128000 / 128000 | 64 | 206.87 | 224.88 | `20261116T001000Z-dedd3d1f` |
| edge-b2dbaff | proxy | 512000 / 512000 | 0 | 208.04 | 304.04 | `20261116T001000Z-dedd3d1f` |
| edge-b2dbaff | proxy | 512000 / 512000 | 4 | 222.71 | 203.73 | `20261116T001000Z-dedd3d1f` |
| edge-b2dbaff | proxy | 512000 / 512000 | 16 | 238.48 | 214.10 | `20261116T001000Z-dedd3d1f` |
| edge-b2dbaff | proxy | 512000 / 512000 | 64 | 210.33 | 199.89 | `20261116T001000Z-dedd3d1f` |

### Copy weight

| Build | Storage | Nodes / edges | Create + claim + score + discard (ms) | Run |
|---|---|---|---|---|
| v0.15.0 | minio | 32000 / 32000 | 282.46 | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | minio | 128000 / 128000 | 362.20 | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | minio | 512000 / 512000 | 534.20 | `20261115T233008Z-ba6c2bba` |
| v0.15.0 | proxy | 32000 / 32000 | 3234.00 | `20261115T233710Z-d6e9001c` |
| v0.15.0 | proxy | 128000 / 128000 | 3439.88 | `20261115T233710Z-d6e9001c` |
| v0.15.0 | proxy | 512000 / 512000 | 7652.22 | `20261115T233710Z-d6e9001c` |
| edge-b2dbaff | local | 32000 / 32000 | 87.90 | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | local | 128000 / 128000 | 110.03 | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | local | 512000 / 512000 | 331.52 | `20261115T235639Z-1a7662ca` |
| edge-b2dbaff | minio | 32000 / 32000 | 620.79 | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | minio | 128000 / 128000 | 620.99 | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | minio | 512000 / 512000 | 582.40 | `20261116T000227Z-a91e2dae` |
| edge-b2dbaff | proxy | 32000 / 32000 | 3229.53 | `20261116T001000Z-dedd3d1f` |
| edge-b2dbaff | proxy | 128000 / 128000 | 3627.17 | `20261116T001000Z-dedd3d1f` |
| edge-b2dbaff | proxy | 512000 / 512000 | 5107.57 | `20261116T001000Z-dedd3d1f` |

## O5 cross-process read your writes

| Build | Storage | Second process | Write acknowledged | Seen | Attempts | Staleness (ms) | Run |
|---|---|---|---|---|---|---|---|
| v0.15.0 | minio | wm-omnigraph-b | yes | yes | 1 | 1439.92 | `20261115T232428Z-7b3675aa` |
| edge-b2dbaff | minio | wm-omnigraph-b | yes | yes | 1 | 1498.61 | `20261115T232445Z-74a4b9d4` |
| v0.15.0 | local | wm-omnigraph-b | yes | yes | 1 | 1644.02 | `20261115T232500Z-bc9d3caf` |
| edge-b2dbaff | local | wm-omnigraph-b | yes | yes | 1 | 1456.39 | `20261115T232509Z-b97455a1` |
