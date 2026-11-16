# M5: Cognee: batch `m5k-20261116T123513Z`

Regenerated from `evidence/` by `python wm.py report --memory`. Do not edit by hand.

- Harness commit: `951ccf9d7774dd84b0bc94dabd53ebce56bea12c` (dirty: false)
- Host: Windows-11-10.0.26300-SP0; 11th Gen Intel(R) Core(TM) i5-11320H @ 3.20GHz; 8 logical cores; 23.8 GB
- Docker: 29.9.3; VM limits 8 CPUs, 11.6 GB
- Runs: 3 (3 races, 0 case suites, 0 visibility)

## Races

| Build | Backend | Scenario | Sequential control | Overlap control | Verdicts | Run |
|---|---|---|---|---|---|---|
| v1.6.8 | R1 (access control off) | c2.improve.process | met | 1 of 1 valid trials had two or more in flight | I1B PASS 0/1; I2 PASS 0/1; I4 PASS 0/1; I5 PASS 0/1 | `20261116T123522Z-49f0100f` |
| v1.6.8 | R2 (access control off) | c2.improve.process | met | 20 of 20 valid trials had two or more in flight | I1B PASS 0/20; I2 PASS 0/20; I4 PASS 0/20; I5 PASS 0/20 | `20261116T125700Z-b7ebcfbc` |
| v1.6.1 | R3 (access control off) | c2.improve.process | NOT met | 20 of 20 valid trials had two or more in flight | I1B INVALID 0/20; I2 INVALID 0/20; I4 INVALID 0/20; I5 INVALID 0/20 | `20261116T131854Z-43702faa` |

Sequential controls met: 2 of 3 race runs.

### Release spread by mode (valid race trials)

| Mode | Trials | p50 | p95 | p99 | max |
|---|---|---|---|---|---|
| process | 41 | 0.09 | 0.12 | 0.13 | 0.13 |

## Invariants by backend

Each cell: valid trials with a violation / valid trials that carry the check. Trials a gate made invalid are counted in the next table, not here.

| Build | Backend | Scenario | Valid trials | Duplicate entities (I1B) | Duplicate vector ids (I1B) | Artefacts in one store only (I4) | Lost acknowledged items (I2) | Deletion permanence (I5) | Crash ceiling (documents) | Store reopens after the run | Run |
|---|---|---|---|---|---|---|---|---|---|---|---|
| v1.6.8 | R1 (access control off) | c2.improve.process | 1/20 | 0/1 | 0/1 | 0/1 | 0/1 | 0/1 | – | – | `20261116T123522Z-49f0100f` |
| v1.6.8 | R2 (access control off) | c2.improve.process | 20/20 | 0/20 | 0/20 | 0/20 | 0/20 | 0/20 | – | – | `20261116T125700Z-b7ebcfbc` |
| v1.6.1 | R3 (access control off) | c2.improve.process | 20/20 | 0/20 | 0/20 | 0/20 | 0/20 | 0/20 | – | – | `20261116T131854Z-43702faa` |

## Checks outside the invariants

| Backend | Scenario | Check | Trials where it did not hold | Details (first trials) | Run |
|---|---|---|---|---|---|
| R1 (access control off) | c2.improve.process | C2P | 0 of 20 | – | `20261116T123522Z-49f0100f` |
| R1 (access control off) | c2.improve.process | C2W | 0 of 20 | – | `20261116T123522Z-49f0100f` |
| R1 (access control off) | c2.improve.process | ERR | 19 of 20 | ladybug file lock x1 | `20261116T123522Z-49f0100f` |
| R1 (access control off) | c2.improve.process | IMP | 1 of 20 | feedback_weights skipped; persist_session_qa skipped; persist_agent_traces skipped; extrac | `20261116T123522Z-49f0100f` |
| R2 (access control off) | c2.improve.process | C2P | 0 of 20 | – | `20261116T125700Z-b7ebcfbc` |
| R2 (access control off) | c2.improve.process | C2W | 0 of 20 | – | `20261116T125700Z-b7ebcfbc` |
| R2 (access control off) | c2.improve.process | ERR | 0 of 20 | – | `20261116T125700Z-b7ebcfbc` |
| R2 (access control off) | c2.improve.process | IMP | 0 of 20 | – | `20261116T125700Z-b7ebcfbc` |
| R3 (access control off) | c2.improve.process | C2P | 0 of 20 | – | `20261116T131854Z-43702faa` |
| R3 (access control off) | c2.improve.process | C2W | 0 of 20 | – | `20261116T131854Z-43702faa` |
| R3 (access control off) | c2.improve.process | ERR | 0 of 20 | – | `20261116T131854Z-43702faa` |
| R3 (access control off) | c2.improve.process | IMP | 0 of 20 | – | `20261116T131854Z-43702faa` |

## Invalid trials

| Backend | Scenario | Invalid trials | Reasons (distinct, first three) | Run |
|---|---|---|---|---|
| R1 (access control off) | c2.improve.process | 19 of 20 | 1 of 3 operations had an unknown outcome | `20261116T123522Z-49f0100f` |
