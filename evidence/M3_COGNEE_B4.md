# M3: Cognee, fourth batch: batch `m3d-20261114T233706Z`

Regenerated from `evidence/` by `python wm.py report --memory`. Do not edit by hand.

- Harness commit: `5747966e04fc75fe461c3d26cc9bbeecaba0476b` (dirty: false)
- Host: Windows-11-10.0.26300-SP0; 11th Gen Intel(R) Core(TM) i5-11320H @ 3.20GHz; 8 logical cores; 23.8 GB
- Docker: 29.9.3; VM limits 8 CPUs, 11.6 GB
- Runs: 1 (0 races, 0 case suites, 0 visibility)

## Scale ladder

**v1.6.1 R3 (access control off)**, run `20261114T233713Z-ea3ee4af`

| Rung | Documents | Elapsed (s) | Batch p50 / max (s) | Peak memory, helper / workers (MB) | Graph store (MB) | Nodes | Entities | Stub calls (LLM / embed) | Crash |
|---|---|---|---|---|---|---|---|---|---|
| 448 | 448 | 96.10 | 3.24 / 4.38 | 374 / 0 | 0 | 2688 | 1341 | 897 / 449 | no |
| 1000 | 1000 | 274.10 | 4.93 / 6.03 | 383.70 / 0 | 0 | 5995 | 2992 | 1104 / 552 | no |
| 1650 | 1650 | 575.40 | 7.28 / 8.54 | 428.30 / 0 | 0 | 9890 | 4937 | 1300 / 650 | no |
| 2500 | 2500 | 1126.60 | 9.98 / 11.58 | 441 / 0 | 0 | 14980 | 7477 | 1700 / 850 | no |
| 5401 | 5401 | 4275.30 | 17.22 / 22.73 | 444.70 / 0 | 0 | 32304 | 16098 | 5802 / 2901 | no |

Reopened afterwards in a fresh process: read_only: n/a (no Ladybug store); read_write: n/a

## Invariants by backend

Each cell: valid trials with a violation / valid trials that carry the check. Trials a gate made invalid are counted in the next table, not here.

| Build | Backend | Scenario | Valid trials | Duplicate entities (I1B) | Duplicate vector ids (I1B) | Artefacts in one store only (I4) | Lost acknowledged items (I2) | Deletion permanence (I5) | Crash ceiling (documents) | Store reopens after the run | Run |
|---|---|---|---|---|---|---|---|---|---|---|---|
| v1.6.1 | R3 (access control off) | c4.ladder | 5/5 | – | – | – | 0/5 | – | none up to 5401 | read-only n/a (no Ladybug store); read-write n/a | `20261114T233713Z-ea3ee4af` |

## Checks outside the invariants

| Backend | Scenario | Check | Trials where it did not hold | Details (first trials) | Run |
|---|---|---|---|---|---|
| R3 (access control off) | c4.ladder | CRASH | 0 of 5 | – | `20261114T233713Z-ea3ee4af` |
