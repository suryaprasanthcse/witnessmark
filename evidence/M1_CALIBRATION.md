# M1 calibration: batch `m1-20261113T162442Z`

Regenerated from `evidence/` by `python wm.py report`. Do not edit by hand.

- Harness commit: `c31758306e38ea3a8b40af98b965a31900e5e6b5` (dirty: false)
- Host: Windows-11-10.0.26300-SP0; 11th Gen Intel(R) Core(TM) i5-11320H @ 3.20GHz; 8 logical cores; 23.8 GB; Python 3.14.7
- Docker: 29.9.3; VM limits 8 CPUs, 11.6 GB
- falkordb: 6.0.4 (graph module 60004); image `falkordb/falkordb@sha256:bef8acb1d8ed9ff8d2ea251767e75c6c05cfa759f7c6bc7e1c122f27d0ea4d7f`; digest `sha256:bef8acb1d8ed9ff8d2ea251767e75c6c05cfa759f7c6bc7e1c122f27d0ea4d7f`
- neo4j: 5.26.2 community; image `neo4j:5.26.2@sha256:099b9f74968c123209972835417985ed2a1cc19c0422c0753a313e26a736c365`; digest `sha256:099b9f74968c123209972835417985ed2a1cc19c0422c0753a313e26a736c365`
- Mode: thread; 50 clients; 20 trials per run

## Runs

| Engine | Scenario | Role | Sequential control | Role control | Violating trials | Magnitude (min / median / max) | Release spread p50 / max (ms) | Verdict | Run |
|---|---|---|---|---|---|---|---|---|---|
| falkordb | claim.state.naive | negative | met | met | 0 of 20 | 1 / 1 / 1 winners | 6.45 / 10.14 | PASS | `20261113T162442Z-2b5b4d8b` |
| falkordb | claim.lease.naive | negative | met | met | 0 of 20 | 1 / 1 / 1 winners | 6.01 / 10.15 | PASS | `20261113T162444Z-63fe20dc` |
| falkordb | counter.direct | negative | met | met | 0 of 20 | 0 / 0 / 0 lost updates | 5.99 / 10.55 | PASS | `20261113T162446Z-5ee06863` |
| falkordb | counter.via_with | negative | met | met | 0 of 20 | 0 / 0 / 0 lost updates | 6.15 / 12.79 | PASS | `20261113T162447Z-f7be912f` |
| falkordb | disjoint.set | negative | met | met | 0 of 20 | 0 / 0 / 0 lost writes | 7.02 / 12.49 | PASS | `20261113T162449Z-c1edb70c` |
| neo4j | claim.state.naive | positive | met | met | 20 of 20 | 4 / 10.50 / 13 winners | 10.32 / 21.13 | KNOWN_DEVIATION | `20261113T162451Z-8e8ec093` |
| neo4j | claim.state.lock_first | negative | met | met | 0 of 20 | 1 / 1 / 1 winners | 12.67 / 32.53 | PASS | `20261113T162457Z-9b9b7901` |
| neo4j | claim.lease.naive | positive | met | met | 20 of 20 | 2 / 10 / 13 winners | 8.69 / 20.45 | KNOWN_DEVIATION | `20261113T162503Z-8816c993` |
| neo4j | claim.lease.lock_first | negative | met | met | 0 of 20 | 1 / 1 / 1 winners | 8.38 / 12.22 | PASS | `20261113T162508Z-ac1b5b81` |
| neo4j | counter.direct | negative | met | met | 0 of 20 | 0 / 0 / 0 lost updates | 7.65 / 10.43 | PASS | `20261113T162513Z-0c119b4f` |
| neo4j | counter.via_with | positive | met | met | 20 of 20 | 40 / 46 / 49 lost updates | 8.32 / 14.53 | KNOWN_DEVIATION | `20261113T162519Z-3e877443` |
| neo4j | disjoint.set | negative | met | met | 0 of 20 | 0 / 0 / 0 lost writes | 7.60 / 11.99 | PASS | `20261113T162524Z-67988486` |

## Release spread (thread mode, every valid race trial)

- Trials: 240
- p50 7.88 ms; p95 14.97 ms; p99 26.65 ms; max 32.53 ms
- Proposed gate δ for thread mode (1.5 × p99, rounded up): 40 ms

## M1 exit check (master blueprint section 12)

- Sequential controls met: 12 of 12 runs
- Negative controls met: 9 of 9 runs
- Positive controls fired: 3 of 3 runs
- INVALID verdicts: 0
- Exit criterion MET
