# M6: Omnigraph O2a on v0.16.0: batch `m6o-20261122T2102Z`

Regenerated from `evidence/` by `python wm.py report --memory`. Do not edit by hand.

- Harness commit: `73cd8e0d32a3ae8ab0876a2f165a2abfb636feaf` (dirty: false)
- Host: Windows-11-10.0.26300-SP0; 11th Gen Intel(R) Core(TM) i5-11320H @ 3.20GHz; 8 logical cores; 23.8 GB
- Docker: 29.9.3; VM limits 8 CPUs, 11.6 GB
- Runs: 3 (0 races, 0 case suites, 0 visibility)
- Runs added in M5: 3 thread-mode races, 0 O2b cost curves, 0 O6 parity runs, 0 O4 clean-stop transfers
- Harness commits in this batch: `73cd8e0`

## Baseline claim controls (thread mode)

The M1 control matrix, run in this batch. FalkorDB 6.0.4 is the negative control; Neo4j 5.26.2's naive shapes are the positive control (master blueprint section 6.2).

| Engine | Build | Storage | Scenario | Role | Clients | Gate (ms) | Sequential control | Role control | Valid trials | Violating trials | Outcomes ok / fail / unknown (valid trials) | Release spread p50 / max (ms) | Valid of declared | Verdict | Run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| falkordb | 6.0.4 (graph module 60004) | – | claim.state.naive | negative | 50 | off | met | met | 20 of 20 | 0 of 20 | 20 / 980 / 0 | 5.30 / 9.66 | 20 of 20 | PASS | `20261122T210451Z-59533624` |
| neo4j | 5.26.2 community | – | claim.state.naive | positive | 50 | off | met | met | 20 of 20 | 18 of 20 | 170 / 830 / 0 | 9.28 / 18.39 | 20 of 20 | KNOWN_DEVIATION | `20261122T210453Z-47fd8e3a` |

## Omnigraph races (thread mode)

| Engine | Build | Storage | Scenario | Role | Clients | Gate (ms) | Sequential control | Role control | Valid trials | Violating trials | Outcomes ok / fail / unknown (valid trials) | Release spread p50 / max (ms) | Valid of declared | Verdict | Run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| omnigraph | v0.16.0 | local | o2a.conditional_one_task.thread | negative | 50 | 55 | met | met | 20 of 20 | 0 of 20 | 20 / 980 / 0 | 7.74 / 16.95 | 20 of 20 | PASS | `20261122T210504Z-cf3d6bc6` |

### Race outcomes by error type

Counted from `history.jsonl` over every race trial of the run.

| Engine | Build | Scenario | Race operations | Acknowledged | Refusals by error type (count) | Unknown | Run |
|---|---|---|---|---|---|---|---|
| omnigraph | v0.16.0 | o2a.conditional_one_task.thread | 1000 | 20 | `precondition_failure` 980 | 0 | `20261122T210504Z-cf3d6bc6` |

### Release spread, thread mode (valid trials)

| Engine | Scenarios | Valid trials | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | 1.5 × p99, rounded up (ms) |
|---|---|---|---|---|---|---|---|
| falkordb | claim.state.naive | 20 | 5.30 | 8.63 | 9.66 | 9.66 | 15 |
| neo4j | claim.state.naive | 20 | 9.28 | 18.32 | 18.39 | 18.39 | 28 |
| omnigraph | o2a.conditional_one_task.thread | 20 | 7.74 | 16.86 | 16.95 | 16.95 | 26 |
