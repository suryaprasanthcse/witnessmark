# M5: Omnigraph, spread calibration: batch `m5-20261115T222957Z`

Regenerated from `evidence/` by `python wm.py report --memory`. Do not edit by hand.

- Harness commit: `772ef9601ead98e750aa0a45a9b146bff6423e35` (dirty: false)
- Host: Windows-11-10.0.26300-SP0; 11th Gen Intel(R) Core(TM) i5-11320H @ 3.20GHz; 8 logical cores; 23.8 GB
- Docker: 29.9.3; VM limits 8 CPUs, 11.6 GB
- Runs: 9 (0 races, 0 case suites, 0 visibility)
- Runs added in M5: 9 thread-mode races, 0 O2b cost curves, 0 O6 parity runs, 0 O4 clean-stop transfers
- Harness commits in this batch: `772ef96`

## Baseline claim controls (thread mode)

The M1 control matrix, run in this batch. FalkorDB 6.0.4 is the negative control; Neo4j 5.26.2's naive shapes are the positive control (master blueprint section 6.2).

| Engine | Build | Storage | Scenario | Role | Clients | Gate (ms) | Sequential control | Role control | Valid trials | Violating trials | Outcomes ok / fail / unknown (valid trials) | Release spread p50 / max (ms) | Verdict | Run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| falkordb | 6.0.4 (graph module 60004) | – | claim.state.naive | negative | 50 | off | met | met | 20 of 20 | 0 of 20 | 20 / 980 / 0 | 5.30 / 11.50 | PASS | `20261115T222959Z-dd58c949` |
| falkordb | 6.0.4 (graph module 60004) | – | claim.lease.naive | negative | 50 | off | met | met | 20 of 20 | 0 of 20 | 20 / 980 / 0 | 3.64 / 12.47 | PASS | `20261115T223002Z-1cc6e5c3` |
| falkordb | 6.0.4 (graph module 60004) | – | counter.direct | negative | 50 | off | met | met | 20 of 20 | 0 of 20 | 724 / 276 / 0 | 3.52 / 9.55 | PASS | `20261115T223005Z-c8302f31` |
| falkordb | 6.0.4 (graph module 60004) | – | counter.via_with | negative | 50 | off | met | met | 20 of 20 | 0 of 20 | 844 / 156 / 0 | 4.33 / 12.07 | PASS | `20261115T223008Z-6cc2bc17` |
| falkordb | 6.0.4 (graph module 60004) | – | disjoint.set | negative | 50 | off | met | met | 20 of 20 | 0 of 20 | 901 / 99 / 0 | 5.55 / 12.15 | PASS | `20261115T223011Z-f2f25b0b` |

## Omnigraph races (thread mode)

| Engine | Build | Storage | Scenario | Role | Clients | Gate (ms) | Sequential control | Role control | Valid trials | Violating trials | Outcomes ok / fail / unknown (valid trials) | Release spread p50 / max (ms) | Verdict | Run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| omnigraph | v0.15.0 | local | o2a.conditional_one_task.thread | negative | 50 | off | met | NOT met | 20 of 20 | 20 of 20 | 20 / 980 / 0 | 8.75 / 36.37 | FAIL | `20261115T223017Z-22107db4` |
| omnigraph | edge-b2dbaff | local | o2a.conditional_one_task.thread | negative | 50 | off | met | NOT met | 20 of 20 | 20 of 20 | 20 / 980 / 0 | 8.69 / 23.12 | FAIL | `20261115T223104Z-bcff6931` |
| omnigraph | v0.15.0 | local | o2c.cardinality_one_task.thread | negative | 50 | off | met | NOT met | 20 of 20 | 20 of 20 | 20 / 980 / 0 | 8.13 / 20.20 | FAIL | `20261115T223149Z-b1b52c9c` |
| omnigraph | edge-b2dbaff | local | o2c.cardinality_one_task.thread | negative | 50 | off | met | NOT met | 20 of 20 | 20 of 20 | 20 / 980 / 0 | 8.48 / 26.69 | FAIL | `20261115T223237Z-3658b53d` |

### Race outcomes by error type

Counted from `history.jsonl` over every race trial of the run.

| Engine | Build | Scenario | Race operations | Acknowledged | Refusals by error type (count) | Unknown | Run |
|---|---|---|---|---|---|---|---|
| omnigraph | v0.15.0 | o2a.conditional_one_task.thread | 1000 | 20 | `too_many_requests` 680; `precondition_failure` 266; `CardinalityViolation` 34 | 0 | `20261115T223017Z-22107db4` |
| omnigraph | edge-b2dbaff | o2a.conditional_one_task.thread | 1000 | 20 | `too_many_requests` 680; `precondition_failure` 262; `CardinalityViolation` 38 | 0 | `20261115T223104Z-bcff6931` |
| omnigraph | v0.15.0 | o2c.cardinality_one_task.thread | 1000 | 20 | `too_many_requests` 680; `conflict` 263; `CardinalityViolation` 37 | 0 | `20261115T223149Z-b1b52c9c` |
| omnigraph | edge-b2dbaff | o2c.cardinality_one_task.thread | 1000 | 20 | `too_many_requests` 680; `CardinalityViolation` 300 | 0 | `20261115T223237Z-3658b53d` |

### Release spread, thread mode (valid trials)

| Engine | Scenarios | Valid trials | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | 1.5 × p99, rounded up (ms) |
|---|---|---|---|---|---|---|---|
| falkordb | claim.lease.naive, claim.state.naive, counter.direct, counter.via_with, disjoint.set | 100 | 4.44 | 9.55 | 12.15 | 12.47 | 19 |
| omnigraph | o2a.conditional_one_task.thread, o2c.cardinality_one_task.thread | 80 | 8.67 | 23.12 | 36.37 | 36.37 | 55 |
