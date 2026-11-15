# M3: Cognee, second batch (re-runs): batch `m3b-20261114T204628Z`

Regenerated from `evidence/` by `python wm.py report --memory`. Do not edit by hand.

- Harness commit: `f3dbe98e64dde54423e3905f034a8a45b697178d` (dirty: false)
- Host: Windows-11-10.0.26300-SP0; 11th Gen Intel(R) Core(TM) i5-11320H @ 3.20GHz; 8 logical cores; 23.8 GB
- Docker: 29.9.3; VM limits 8 CPUs, 11.6 GB
- Runs: 5 (5 races, 0 case suites, 0 visibility)

## Races

| Build | Backend | Scenario | Sequential control | Overlap control | Verdicts | Run |
|---|---|---|---|---|---|---|
| v1.6.1 | R3 (access control off) | c1.disjoint.k4.process | met | 15 of 15 valid trials had two or more in flight | I1B PASS 0/15; I2 PASS 0/15; I4 PASS 0/15 | `20261114T204641Z-ec73c5ad` |
| v1.6.8 | R2 (access control off) | c1.k8.process | met | 0 of 0 valid trials had two or more in flight | I1B INVALID 0/0; I2 INVALID 0/0; I4 INVALID 0/0 | `20261114T204652Z-d5f2e1c9` |
| v1.6.1 | R3 (access control off) | c2.writers.process | NOT met | 18 of 18 valid trials had two or more in flight | I1B INVALID 0/18; I2 INVALID 0/18; I4 INVALID 0/18; I5 INVALID 0/18 | `20261114T210439Z-c2c55f16` |
| v1.6.8 | R2 (access control off) | c1.disjoint.k4.process | met | 5 of 5 valid trials had two or more in flight | I1B PASS 0/5; I2 PASS 0/5; I4 PASS 0/5 | `20261114T212346Z-a6f1985e` |
| v1.6.8 | R2 (access control off) | c2.writers.process | met | 14 of 14 valid trials had two or more in flight | I1B BOUNDARY 13/14 (max 2 records per key); I2 PASS 0/14; I4 PASS 0/14; I5 PASS 0/14 | `20261114T214705Z-8a40b975` |

Sequential controls met: 4 of 5 race runs.

### Release spread by mode (valid race trials)

| Mode | Trials | p50 | p95 | p99 | max |
|---|---|---|---|---|---|
| process | 52 | 0.11 | 0.79 | 0.97 | 0.97 |

## Invariants by backend

Each cell: valid trials with a violation / valid trials that carry the check. Trials a gate made invalid are counted in the next table, not here.

| Build | Backend | Scenario | Valid trials | Duplicate entities (I1B) | Duplicate vector ids (I1B) | Artefacts in one store only (I4) | Lost acknowledged items (I2) | Deletion permanence (I5) | Crash ceiling (documents) | Store reopens after the run | Run |
|---|---|---|---|---|---|---|---|---|---|---|---|
| v1.6.1 | R3 (access control off) | c1.disjoint.k4.process | 15/20 | 0/15 | 0/15 | 0/15 | 0/15 | – | – | – | `20261114T204641Z-ec73c5ad` |
| v1.6.8 | R2 (access control off) | c1.k8.process | 0/20 | – | – | – | – | – | – | – | `20261114T204652Z-d5f2e1c9` |
| v1.6.1 | R3 (access control off) | c2.writers.process | 18/20 | 0/18 | 0/18 | 0/18 | 0/18 | 0/18 | – | – | `20261114T210439Z-c2c55f16` |
| v1.6.8 | R2 (access control off) | c1.disjoint.k4.process | 5/20 | 0/5 | 0/5 | 0/5 | 0/5 | – | – | – | `20261114T212346Z-a6f1985e` |
| v1.6.8 | R2 (access control off) | c2.writers.process | 14/20 | 0/14 | 13/14 | 0/14 | 0/14 | 0/14 | – | – | `20261114T214705Z-8a40b975` |

## Checks outside the invariants

| Backend | Scenario | Check | Trials where it did not hold | Details (first trials) | Run |
|---|---|---|---|---|---|
| R3 (access control off) | c1.disjoint.k4.process | ERR | 1 of 20 | CognifyFailedError x1 | `20261114T204641Z-ec73c5ad` |
| R2 (access control off) | c1.k8.process | ERR | 20 of 20 | AfterRunHookError x1; AfterRunHookError x2; AfterRunHookError x3 | `20261114T204652Z-d5f2e1c9` |
| R3 (access control off) | c2.writers.process | C2P | 0 of 20 | – | `20261114T210439Z-c2c55f16` |
| R3 (access control off) | c2.writers.process | C2W | 0 of 20 | – | `20261114T210439Z-c2c55f16` |
| R3 (access control off) | c2.writers.process | ERR | 0 of 20 | – | `20261114T210439Z-c2c55f16` |
| R2 (access control off) | c1.disjoint.k4.process | ERR | 15 of 20 | AfterRunHookError x1 | `20261114T212346Z-a6f1985e` |
| R2 (access control off) | c2.writers.process | C2P | 0 of 20 | – | `20261114T214705Z-8a40b975` |
| R2 (access control off) | c2.writers.process | C2W | 0 of 20 | – | `20261114T214705Z-8a40b975` |
| R2 (access control off) | c2.writers.process | ERR | 6 of 20 | AfterRunHookError x1 | `20261114T214705Z-8a40b975` |

## Invalid trials

| Backend | Scenario | Invalid trials | Reasons (distinct, first three) | Run |
|---|---|---|---|---|
| R3 (access control off) | c1.disjoint.k4.process | 5 of 20 | 1 of 8 operations had an unknown outcome; release spread 6.005 ms exceeds the process gate 1.0 ms; release spread 1.982 ms exceeds the process gate 1.0 ms; release spread 3.39 ms exceeds the process gate 1.0 ms | `20261114T204641Z-ec73c5ad` |
| R2 (access control off) | c1.k8.process | 20 of 20 | 1 of 16 operations had an unknown outcome; release spread 1.89 ms exceeds the process gate 1.0 ms; 2 of 16 operations had an unknown outcome; release spread 5.715 ms exceeds the process gate 1.0 ms; 3 of 16 operations had an unknown outcome | `20261114T204652Z-d5f2e1c9` |
| R3 (access control off) | c2.writers.process | 2 of 20 | release spread 1.436 ms exceeds the process gate 1.0 ms; release spread 6.844 ms exceeds the process gate 1.0 ms | `20261114T210439Z-c2c55f16` |
| R2 (access control off) | c1.disjoint.k4.process | 15 of 20 | 1 of 8 operations had an unknown outcome | `20261114T212346Z-a6f1985e` |
| R2 (access control off) | c2.writers.process | 6 of 20 | 1 of 3 operations had an unknown outcome | `20261114T214705Z-8a40b975` |
