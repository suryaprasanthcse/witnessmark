# M5: Omnigraph, Neo4j control re-run: batch `m5c-20261115T223540Z`

Regenerated from `evidence/` by `python wm.py report --memory`. Do not edit by hand.

- Harness commit: `772ef9601ead98e750aa0a45a9b146bff6423e35` (dirty: false)
- Host: Windows-11-10.0.26300-SP0; 11th Gen Intel(R) Core(TM) i5-11320H @ 3.20GHz; 8 logical cores; 23.8 GB
- Docker: 29.9.3; VM limits 8 CPUs, 11.6 GB
- Runs: 7 (0 races, 0 case suites, 0 visibility)
- Runs added in M5: 7 thread-mode races, 0 O2b cost curves, 0 O6 parity runs, 0 O4 clean-stop transfers
- Harness commits in this batch: `772ef96`

## Baseline claim controls (thread mode)

The M1 control matrix, run in this batch. FalkorDB 6.0.4 is the negative control; Neo4j 5.26.2's naive shapes are the positive control (master blueprint section 6.2).

| Engine | Build | Storage | Scenario | Role | Clients | Gate (ms) | Sequential control | Role control | Valid trials | Violating trials | Outcomes ok / fail / unknown (valid trials) | Release spread p50 / max (ms) | Verdict | Run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| neo4j | 5.26.2 community | – | claim.state.naive | positive | 50 | off | met | met | 20 of 20 | 20 of 20 | 201 / 799 / 0 | 7.69 / 21.15 | KNOWN_DEVIATION | `20261115T223541Z-d507952d` |
| neo4j | 5.26.2 community | – | claim.state.lock_first | negative | 50 | off | met | met | 20 of 20 | 0 of 20 | 20 / 980 / 0 | 7.18 / 15.13 | PASS | `20261115T223551Z-36ddd91e` |
| neo4j | 5.26.2 community | – | claim.lease.naive | positive | 50 | off | met | met | 20 of 20 | 20 of 20 | 182 / 818 / 0 | 7.43 / 15.01 | KNOWN_DEVIATION | `20261115T223556Z-0c7fd4ab` |
| neo4j | 5.26.2 community | – | claim.lease.lock_first | negative | 50 | off | met | met | 20 of 20 | 0 of 20 | 20 / 980 / 0 | 6.89 / 8.77 | PASS | `20261115T223602Z-b838cc27` |
| neo4j | 5.26.2 community | – | counter.direct | negative | 50 | off | met | met | 20 of 20 | 0 of 20 | 1000 / 0 / 0 | 6.73 / 10.72 | PASS | `20261115T223608Z-4c7cea08` |
| neo4j | 5.26.2 community | – | counter.via_with | positive | 50 | off | met | met | 20 of 20 | 20 of 20 | 1000 / 0 / 0 | 7.43 / 10.76 | KNOWN_DEVIATION | `20261115T223616Z-c2fb1473` |
| neo4j | 5.26.2 community | – | disjoint.set | negative | 50 | off | met | met | 20 of 20 | 0 of 20 | 1000 / 0 / 0 | 7.54 / 16.33 | PASS | `20261115T223623Z-ed33ecfc` |

### Release spread, thread mode (valid trials)

| Engine | Scenarios | Valid trials | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) | 1.5 × p99, rounded up (ms) |
|---|---|---|---|---|---|---|---|
| neo4j | claim.lease.lock_first, claim.lease.naive, claim.state.lock_first, claim.state.naive, counter.direct, counter.via_with, disjoint.set | 140 | 7.49 | 10.91 | 16.33 | 21.15 | 25 |
