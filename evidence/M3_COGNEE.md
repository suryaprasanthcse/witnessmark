# M3: Cognee: batch `m3-20261114T131136Z`

Regenerated from `evidence/` by `python wm.py report --memory`. Do not edit by hand.

- Harness commit: `1fd4dd02eed7b65664b0749181150abffcc8ce68` (dirty: false)
- Host: Windows-11-10.0.26300-SP0; 11th Gen Intel(R) Core(TM) i5-11320H @ 3.20GHz; 8 logical cores; 23.8 GB
- Docker: 29.9.3; VM limits 8 CPUs, 11.6 GB
- Runs: 44 (23 races, 13 case suites, 4 visibility)

## Races

| Build | Backend | Scenario | Sequential control | Overlap control | Verdicts | Run |
|---|---|---|---|---|---|---|
| v1.6.8 | R1 | c1.k2.process | met | 0 of 0 valid trials had two or more in flight | I1B INVALID 0/0; I2 INVALID 0/0; I4 INVALID 0/0 | `20261114T131228Z-5b47435a` |
| v1.6.8 | R2 (access control off) | c1.k2.process | met | 20 of 20 valid trials had two or more in flight | I1B PASS 0/20; I2 PASS 0/20; I4 PASS 0/20 | `20261114T131236Z-6344cb3f` |
| v1.6.8 | R1 | c1.k4.process | met | 0 of 0 valid trials had two or more in flight | I1B INVALID 0/0; I2 INVALID 0/0; I4 INVALID 0/0 | `20261114T132931Z-134a3280` |
| v1.6.8 | R2 (access control off) | c1.k4.process | met | 2 of 2 valid trials had two or more in flight | I1B BOUNDARY 2/2 (max 3 records per key); I2 PASS 0/2; I4 PASS 0/2 | `20261114T133423Z-70f45910` |
| v1.6.8 | R1 | c1.k8.process | met | 0 of 0 valid trials had two or more in flight | I1B INVALID 0/0; I2 INVALID 0/0; I4 INVALID 0/0 | `20261114T134920Z-186e234c` |
| v1.6.8 | R1 | c1.disjoint.k4.process | met | 14 of 14 valid trials had two or more in flight | I1B PASS 0/14; I2 PASS 0/14; I4 PASS 0/14 | `20261114T141347Z-b025f668` |
| v1.6.8 | R2 (access control off) | c1.disjoint.k4.process | NOT met | 9 of 9 valid trials had two or more in flight | I1B INVALID 0/9; I2 INVALID 0/9; I4 INVALID 0/9 | `20261114T143626Z-f94d7606` |
| v1.6.8 | R1 (access control off) | c2.writers.process | met | 0 of 0 valid trials had two or more in flight | I1B INVALID 0/0; I2 INVALID 0/0; I4 INVALID 0/0; I5 INVALID 0/0 | `20261114T143808Z-c442cc14` |
| v1.6.8 | R2 (access control off) | c2.writers.process | met | 12 of 12 valid trials had two or more in flight | I1B BOUNDARY 9/12 (max 2 records per key); I2 BOUNDARY 12/12 (max 8 missing entities in the shared store); I4 PASS 0/12; I5 PASS 0/12 | `20261114T145753Z-d168cf57` |
| v1.6.8 | R1 | c3.cross_process.process | met | 36 of 36 valid trials had two or more in flight | I2 PASS 0/36; I5 PASS 0/36 | `20261114T145945Z-0fdd119f` |
| v1.6.8 | R2 (access control off) | c3.cross_process.process | met | 36 of 36 valid trials had two or more in flight | I2 PASS 0/36; I5 PASS 0/36 | `20261114T151804Z-ffa7ede5` |
| v1.6.1 | R3 (access control off) | c1.k2.process | met | 20 of 20 valid trials had two or more in flight | I1B PASS 0/20; I2 PASS 0/20; I4 PASS 0/20 | `20261114T174759Z-d5488c9a` |
| v1.6.1 | R3 (access control off) | c1.k4.process | met | 20 of 20 valid trials had two or more in flight | I1B PASS 0/20; I2 PASS 0/20; I4 PASS 0/20 | `20261114T180028Z-c3232177` |
| v1.6.1 | R3 (access control off) | c1.k8.process | met | 17 of 17 valid trials had two or more in flight | I1B PASS 0/17; I2 PASS 0/17; I4 PASS 0/17 | `20261114T181325Z-73c88163` |
| v1.6.8 | R1i | c1.k2.process | met | 0 of 0 valid trials had two or more in flight | I1B INVALID 0/0; I2 INVALID 0/0; I4 INVALID 0/0 | `20261114T182011Z-03b8761e` |
| v1.6.1 | R3 (access control off) | c1.disjoint.k4.process | NOT met | 20 of 20 valid trials had two or more in flight | I1B INVALID 0/20; I2 INVALID 0/20; I4 INVALID 0/20 | `20261114T182730Z-214444fc` |
| v1.6.1 | R3 (access control off) | c2.writers.process | NOT met | 16 of 16 valid trials had two or more in flight | I1B INVALID 0/16; I2 INVALID 16/16 (max 8 missing entities in the shared store); I4 INVALID 0/16; I5 INVALID 0/16 | `20261114T183825Z-c97d0d06` |
| v1.6.8 | R1i | c1.k4.process | met | 0 of 0 valid trials had two or more in flight | I1B INVALID 0/0; I2 INVALID 0/0; I4 INVALID 0/0 | `20261114T183831Z-97e05ac3` |
| v1.6.1 | R3 (access control off) | c3.cross_process.process | NOT met | 0 of 0 valid trials had two or more in flight | I2 INVALID 0/0; I5 INVALID 0/0 | `20261114T185051Z-97edaf64` |
| v1.6.8 | R1i | c1.k8.process | met | 0 of 0 valid trials had two or more in flight | I1B INVALID 0/0; I2 INVALID 0/0; I4 INVALID 0/0 | `20261114T185431Z-95507ca8` |
| v1.6.8 | R1i | c1.disjoint.k4.process | met | 19 of 19 valid trials had two or more in flight | I1B PASS 0/19; I2 PASS 0/19; I4 PASS 0/19 | `20261114T191301Z-63ab727b` |
| v1.6.8 | R1i (access control off) | c2.writers.process | met | 0 of 0 valid trials had two or more in flight | I1B INVALID 0/0; I2 INVALID 0/0; I4 INVALID 0/0; I5 INVALID 0/0 | `20261114T193043Z-188df5a9` |
| v1.6.8 | R1i | c3.cross_process.process | met | 36 of 36 valid trials had two or more in flight | I2 PASS 0/36; I5 PASS 0/36 | `20261114T195002Z-d40746c3` |

Sequential controls met: 19 of 23 race runs.

### Release spread by mode (valid race trials)

| Mode | Trials | p50 | p95 | p99 | max |
|---|---|---|---|---|---|
| process | 277 | 0.08 | 0.46 | 0.89 | 0.95 |

## Known-answer suites

A cell lists the checks that failed for that case; `ok` means none did.

| Build | Backend | Suite | data_per_batch_1 | default_20 | paused | gather | delete | delete_during_cognify | Run |
|---|---|---|---|---|---|---|---|---|---|
| v1.6.8 | R1 | c0.single_call | ok | I1B | – | – | – | – | `20261114T131142Z-daa65b09` |
| v1.6.8 | R2 (access control off) | c0.single_call | ok | I1B | – | – | – | – | `20261114T131148Z-0fb02db6` |
| v1.6.8 | R1 | c3.in_process | – | – | ok | ok | – | – | `20261114T152617Z-7e5a1c73` |
| v1.6.8 | R1 | c6.deletion | – | – | – | – | ok | ok | `20261114T152659Z-66cfc612` |
| v1.6.8 | R2 (access control off) | c3.in_process | – | – | ok | ok | – | – | `20261114T154549Z-43f96cf5` |
| v1.6.8 | R2 (access control off) | c6.deletion | – | – | – | – | ok | ok | `20261114T154636Z-4a6b3bf3` |
| v1.6.1 | R3 (access control off) | c0.single_call | ok | ok | – | – | – | – | `20261114T174729Z-62211812` |
| v1.6.8 | R1 (access control off) | c6.deletion | – | – | – | – | ok | ok | `20261114T181813Z-32bb61bd` |
| v1.6.8 | R1i | c0.single_call | ok | I1B | – | – | – | – | `20261114T181918Z-b9974e3e` |
| v1.6.1 | R3 (access control off) | c3.in_process | – | – | ok | ok | – | – | `20261114T191258Z-e09326c6` |
| v1.6.1 | R3 (access control off) | c6.deletion | – | – | – | – | ok | ok | `20261114T191322Z-30040411` |
| v1.6.8 | R1i | c3.in_process | – | – | ok | ok | – | – | `20261114T201828Z-f6cda825` |
| v1.6.8 | R1i | c6.deletion | – | – | – | – | ok | ok | `20261114T201915Z-d2b863b9` |

## Read your writes

| Build | Backend | Writes | Seen on the first search, same instance | Seen on the first search, second instance | Longest lag (ms) | Run |
|---|---|---|---|---|---|---|
| v1.6.8 | R1 | 10 | 10 of 10 | 0 of 10 | 30000 | `20261114T152747Z-d7f45081` |
| v1.6.8 | R2 (access control off) | 10 | 10 of 10 | 10 of 10 | 0 | `20261114T154738Z-774cb89c` |
| v1.6.1 | R3 (access control off) | 10 | 10 of 10 | 10 of 10 | 0 | `20261114T191356Z-0363f24c` |
| v1.6.8 | R1i | 10 | 10 of 10 | 0 of 10 | 30000 | `20261114T202008Z-19bd093e` |

## Scale ladder

**v1.6.8 R1**, run `20261114T153402Z-d2bf713f`

| Rung | Documents | Elapsed (s) | Batch p50 / max (s) | Peak memory, helper / workers (MB) | Graph store (MB) | Nodes | Entities | Stub calls (LLM / embed) | Crash |
|---|---|---|---|---|---|---|---|---|---|
| 448 | 448 | 245.60 | 8.49 / 13.82 | 499.60 / 699.40 | 18.90 | 2688 | 1341 | 449 / 2689 | no |
| 1000 | 1000 | 764.40 | 15.01 / 17.23 | 526.60 / 1061.60 | 39.50 | 5995 | 2992 | 552 / 3312 | no |
| 1650 | 1650 | 1552.50 | 18.90 / 28.72 | 538.40 / 1487.10 | 59.70 | 9890 | 4937 | 650 / 3900 | no |
| 2500 | 2500 | 2878.40 | 24.11 / 41.28 | 550.10 / 1962.20 | 91.60 | 14980 | 7477 | 850 / 5100 | no |
| 5401 | 5401 | 9838.70 | 38.39 / 56.46 | 604.40 / 2694.30 | 194 | 32304 | 16098 | 2901 / 17406 | no |

Reopened afterwards in a fresh process: read_only: opened, 32306 nodes; read_write: opened, 32306 nodes

**v1.6.8 R2 (access control off)**, run `20261114T154821Z-2a544933`

| Rung | Documents | Elapsed (s) | Batch p50 / max (s) | Peak memory, helper / workers (MB) | Graph store (MB) | Nodes | Entities | Stub calls (LLM / embed) | Crash |
|---|---|---|---|---|---|---|---|---|---|
| 448 | 448 | 261.30 | 9.08 / 11.92 | 526.40 / 446.60 | 0 | 2688 | 1341 | 449 / 2689 | no |
| 1000 | 1000 | 774.90 | 14.53 / 17.42 | 555.60 / 767.20 | 0 | 5995 | 2992 | 552 / 3312 | no |
| 1650 | 1650 | 1494.70 | 16.63 / 31.03 | 571.70 / 1145.30 | 0 | 9890 | 4937 | 650 / 3900 | no |
| 2500 | 2500 | 2495.60 | 18.05 / 21.33 | 586.20 / 1629.90 | 0 | 14980 | 7477 | 850 / 5100 | no |
| 5401 | 5401 | 7126.60 | 25.10 / 33.67 | 628.50 / 2192.60 | 0 | 32304 | 16098 | 2901 / 17406 | no |

Reopened afterwards in a fresh process: read_only: n/a (no Ladybug store); read_write: n/a

**v1.6.1 R3 (access control off)**, run `20261114T191423Z-43cd092f`

| Rung | Documents | Elapsed (s) | Batch p50 / max (s) | Peak memory, helper / workers (MB) | Graph store (MB) | Nodes | Entities | Stub calls (LLM / embed) | Crash |
|---|---|---|---|---|---|---|---|---|---|
| 448 | 448 | 127.10 | 4.46 / 6.21 | 373.80 / 0 | 0 | 2688 | 1341 | 897 / 449 | no |
| 1000 | 1000 | 376 | 6.88 / 9.71 | 383.50 / 0 | 0 | 5995 | 2992 | 1104 / 552 | no |
| 1650 | 1650 | 805.60 | 10.25 / 14.38 | 407.20 / 0 | 0 | 9890 | 4937 | 1300 / 650 | no |
| 2500 | 2500 | 1511.90 | 12.89 / 17.08 | 415.70 / 0 | 0 | 10000 | 4991 | 1700 / 850 | no |
| 5401 | 5401 | 5455.30 | 21.40 / 30.43 | 443.30 / 0 | 0 | 10000 | 4991 | 5802 / 2901 | no |

Reopened afterwards in a fresh process: read_only: n/a (no Ladybug store); read_write: n/a

**v1.6.8 R1i**, run `20261114T202544Z-f23205b5`

| Rung | Documents | Elapsed (s) | Batch p50 / max (s) | Peak memory, helper / workers (MB) | Graph store (MB) | Nodes | Entities | Stub calls (LLM / embed) | Crash |
|---|---|---|---|---|---|---|---|---|---|
| 448 | 448 | 275.10 | 9.49 / 17.12 | 654.30 / 516.20 | 19.50 | 2688 | 1341 | 449 / 2689 | no |
| 1000 | 1000 | 806.40 | 15.09 / 16.74 | 707.20 / 858.20 | 38.90 | 5995 | 2992 | 552 / 3312 | no |
| 1650 | 1650 | 1737.10 | 18.39 / 52.50 | 749.90 / 1257.30 | 62.20 | 9890 | 4937 | 650 / 3900 | no |
| 2500 | 2500 | 3568.20 | 30.48 / 53.87 | 793.60 / 1727.70 | 95.10 | 14980 | 7477 | 850 / 5100 | no |
| 5401 | 5401 | 9487.80 | 32.93 / 44.36 | 983.50 / 2330.90 | 210.20 | 32304 | 16098 | 2901 / 17406 | no |

Reopened afterwards in a fresh process: read_only: opened, 32306 nodes; read_write: opened, 32306 nodes

## Invariants by backend

Each cell: valid trials with a violation / valid trials that carry the check. Trials a gate made invalid are counted in the next table, not here.

| Build | Backend | Scenario | Valid trials | Duplicate entities (I1B) | Duplicate vector ids (I1B) | Artefacts in one store only (I4) | Lost acknowledged items (I2) | Deletion permanence (I5) | Crash ceiling (documents) | Store reopens after the run | Run |
|---|---|---|---|---|---|---|---|---|---|---|---|
| v1.6.8 | R1 | c0.single_call | 2/2 | 0/2 | 1/2 | 0/2 | 0/2 | – | – | – | `20261114T131142Z-daa65b09` |
| v1.6.8 | R2 (access control off) | c0.single_call | 2/2 | 0/2 | 1/2 | 0/2 | 0/2 | – | – | – | `20261114T131148Z-0fb02db6` |
| v1.6.8 | R1 | c1.k2.process | 0/20 | – | – | – | – | – | – | – | `20261114T131228Z-5b47435a` |
| v1.6.8 | R2 (access control off) | c1.k2.process | 20/20 | 0/20 | 0/20 | 0/20 | 0/20 | – | – | – | `20261114T131236Z-6344cb3f` |
| v1.6.8 | R1 | c1.k4.process | 0/20 | – | – | – | – | – | – | – | `20261114T132931Z-134a3280` |
| v1.6.8 | R2 (access control off) | c1.k4.process | 2/20 | 0/2 | 2/2 | 0/2 | 0/2 | – | – | – | `20261114T133423Z-70f45910` |
| v1.6.8 | R1 | c1.k8.process | 0/20 | – | – | – | – | – | – | – | `20261114T134920Z-186e234c` |
| v1.6.8 | R1 | c1.disjoint.k4.process | 14/20 | 0/14 | 0/14 | 0/14 | 0/14 | – | – | – | `20261114T141347Z-b025f668` |
| v1.6.8 | R2 (access control off) | c1.disjoint.k4.process | 9/20 | 0/9 | 0/9 | 0/9 | 0/9 | – | – | – | `20261114T143626Z-f94d7606` |
| v1.6.8 | R1 (access control off) | c2.writers.process | 0/20 | – | – | – | – | – | – | – | `20261114T143808Z-c442cc14` |
| v1.6.8 | R2 (access control off) | c2.writers.process | 12/20 | 0/12 | 9/12 | 0/12 | 12/12 | 0/12 | – | – | `20261114T145753Z-d168cf57` |
| v1.6.8 | R1 | c3.cross_process.process | 36/36 | – | – | – | 0/36 | 0/36 | – | – | `20261114T145945Z-0fdd119f` |
| v1.6.8 | R2 (access control off) | c3.cross_process.process | 36/36 | – | – | – | 0/36 | 0/36 | – | – | `20261114T151804Z-ffa7ede5` |
| v1.6.8 | R1 | c3.in_process | 2/2 | – | – | – | 0/2 | 0/2 | – | – | `20261114T152617Z-7e5a1c73` |
| v1.6.8 | R1 | c6.deletion | 2/2 | – | – | – | 0/2 | 0/2 | – | – | `20261114T152659Z-66cfc612` |
| v1.6.8 | R1 | c4.ladder | 5/5 | – | – | – | 0/5 | – | none up to 5401 | read-only yes; read-write yes | `20261114T153402Z-d2bf713f` |
| v1.6.8 | R2 (access control off) | c3.in_process | 2/2 | – | – | – | 0/2 | 0/2 | – | – | `20261114T154549Z-43f96cf5` |
| v1.6.8 | R2 (access control off) | c6.deletion | 2/2 | – | – | – | 0/2 | 0/2 | – | – | `20261114T154636Z-4a6b3bf3` |
| v1.6.8 | R2 (access control off) | c4.ladder | 5/5 | – | – | – | 0/5 | – | none up to 5401 | read-only n/a (no Ladybug store); read-write n/a | `20261114T154821Z-2a544933` |
| v1.6.1 | R3 (access control off) | c0.single_call | 2/2 | 0/2 | 0/2 | 0/2 | 0/2 | – | – | – | `20261114T174729Z-62211812` |
| v1.6.1 | R3 (access control off) | c1.k2.process | 20/20 | 0/20 | 0/20 | 0/20 | 0/20 | – | – | – | `20261114T174759Z-d5488c9a` |
| v1.6.1 | R3 (access control off) | c1.k4.process | 20/20 | 0/20 | 0/20 | 0/20 | 0/20 | – | – | – | `20261114T180028Z-c3232177` |
| v1.6.1 | R3 (access control off) | c1.k8.process | 17/20 | 0/17 | 0/17 | 0/17 | 0/17 | – | – | – | `20261114T181325Z-73c88163` |
| v1.6.8 | R1 (access control off) | c6.deletion | 2/2 | – | – | – | 0/2 | 0/2 | – | – | `20261114T181813Z-32bb61bd` |
| v1.6.8 | R1i | c0.single_call | 2/2 | 0/2 | 1/2 | 0/2 | 0/2 | – | – | – | `20261114T181918Z-b9974e3e` |
| v1.6.8 | R1i | c1.k2.process | 0/20 | – | – | – | – | – | – | – | `20261114T182011Z-03b8761e` |
| v1.6.1 | R3 (access control off) | c1.disjoint.k4.process | 20/20 | 0/20 | 0/20 | 0/20 | 0/20 | – | – | – | `20261114T182730Z-214444fc` |
| v1.6.1 | R3 (access control off) | c2.writers.process | 16/20 | 0/16 | 0/16 | 0/16 | 16/16 | 0/16 | – | – | `20261114T183825Z-c97d0d06` |
| v1.6.8 | R1i | c1.k4.process | 0/20 | – | – | – | – | – | – | – | `20261114T183831Z-97e05ac3` |
| v1.6.1 | R3 (access control off) | c3.cross_process.process | 0/36 | – | – | – | – | – | – | – | `20261114T185051Z-97edaf64` |
| v1.6.8 | R1i | c1.k8.process | 0/20 | – | – | – | – | – | – | – | `20261114T185431Z-95507ca8` |
| v1.6.1 | R3 (access control off) | c3.in_process | 1/2 | – | – | – | 0/1 | – | – | – | `20261114T191258Z-e09326c6` |
| v1.6.8 | R1i | c1.disjoint.k4.process | 19/20 | 0/19 | 0/19 | 0/19 | 0/19 | – | – | – | `20261114T191301Z-63ab727b` |
| v1.6.1 | R3 (access control off) | c6.deletion | 2/2 | – | – | – | 0/2 | 0/2 | – | – | `20261114T191322Z-30040411` |
| v1.6.1 | R3 (access control off) | c4.ladder | 5/5 | – | – | – | 2/5 | – | none up to 5401 | read-only n/a (no Ladybug store); read-write n/a | `20261114T191423Z-43cd092f` |
| v1.6.8 | R1i (access control off) | c2.writers.process | 0/20 | – | – | – | – | – | – | – | `20261114T193043Z-188df5a9` |
| v1.6.8 | R1i | c3.cross_process.process | 36/36 | – | – | – | 0/36 | 0/36 | – | – | `20261114T195002Z-d40746c3` |
| v1.6.8 | R1i | c3.in_process | 2/2 | – | – | – | 0/2 | 0/2 | – | – | `20261114T201828Z-f6cda825` |
| v1.6.8 | R1i | c6.deletion | 2/2 | – | – | – | 0/2 | 0/2 | – | – | `20261114T201915Z-d2b863b9` |
| v1.6.8 | R1i | c4.ladder | 5/5 | – | – | – | 0/5 | – | none up to 5401 | read-only yes; read-write yes | `20261114T202544Z-f23205b5` |

## Checks outside the invariants

| Backend | Scenario | Check | Trials where it did not hold | Details (first trials) | Run |
|---|---|---|---|---|---|
| R1 | c1.k2.process | ERR | 20 of 20 | ladybug file lock x2 | `20261114T131228Z-5b47435a` |
| R2 (access control off) | c1.k2.process | ERR | 0 of 20 | – | `20261114T131236Z-6344cb3f` |
| R1 | c1.k4.process | ERR | 20 of 20 | ladybug file lock x4; ladybug file lock x5; ladybug file lock x6 | `20261114T132931Z-134a3280` |
| R2 (access control off) | c1.k4.process | ERR | 18 of 20 | AfterRunHookError x1; AfterRunHookError x2 | `20261114T133423Z-70f45910` |
| R1 | c1.k8.process | ERR | 20 of 20 | ladybug file lock x11; ladybug file lock x12; ladybug file lock x13 | `20261114T134920Z-186e234c` |
| R1 | c1.disjoint.k4.process | ERR | 0 of 20 | – | `20261114T141347Z-b025f668` |
| R2 (access control off) | c1.disjoint.k4.process | ERR | 11 of 20 | AfterRunHookError x1; AfterRunHookError x2 | `20261114T143626Z-f94d7606` |
| R1 (access control off) | c2.writers.process | C2P | 0 of 20 | – | `20261114T143808Z-c442cc14` |
| R1 (access control off) | c2.writers.process | C2W | 0 of 20 | – | `20261114T143808Z-c442cc14` |
| R1 (access control off) | c2.writers.process | ERR | 20 of 20 | ladybug file lock x1; ladybug file lock x2 | `20261114T143808Z-c442cc14` |
| R2 (access control off) | c2.writers.process | C2P | 0 of 20 | – | `20261114T145753Z-d168cf57` |
| R2 (access control off) | c2.writers.process | C2W | 0 of 20 | – | `20261114T145753Z-d168cf57` |
| R2 (access control off) | c2.writers.process | ERR | 7 of 20 | AfterRunHookError x1 | `20261114T145753Z-d168cf57` |
| R1 | c3.cross_process.process | ERR | 0 of 36 | – | `20261114T145945Z-0fdd119f` |
| R2 (access control off) | c3.cross_process.process | ERR | 0 of 36 | – | `20261114T151804Z-ffa7ede5` |
| R1 | c4.ladder | CRASH | 0 of 5 | – | `20261114T153402Z-d2bf713f` |
| R2 (access control off) | c4.ladder | CRASH | 0 of 5 | – | `20261114T154821Z-2a544933` |
| R3 (access control off) | c1.k2.process | ERR | 0 of 20 | – | `20261114T174759Z-d5488c9a` |
| R3 (access control off) | c1.k4.process | ERR | 0 of 20 | – | `20261114T180028Z-c3232177` |
| R3 (access control off) | c1.k8.process | ERR | 0 of 20 | – | `20261114T181325Z-73c88163` |
| R1i | c1.k2.process | ERR | 20 of 20 | ladybug file lock x2 | `20261114T182011Z-03b8761e` |
| R3 (access control off) | c1.disjoint.k4.process | ERR | 0 of 20 | – | `20261114T182730Z-214444fc` |
| R3 (access control off) | c2.writers.process | C2P | 2 of 20 | documents with a row but no chunk, or a chunk but no row: ['C2A000', 'C2A001', 'C2A002', '; documents with a row but no chunk, or a chunk but no row: ['C2A002', 'C2B001', 'C2B003', ' | `20261114T183825Z-c97d0d06` |
| R3 (access control off) | c2.writers.process | C2W | 0 of 20 | – | `20261114T183825Z-c97d0d06` |
| R3 (access control off) | c2.writers.process | ERR | 2 of 20 | CognifyFailedError x2 | `20261114T183825Z-c97d0d06` |
| R1i | c1.k4.process | ERR | 20 of 20 | ladybug file lock x6 | `20261114T183831Z-97e05ac3` |
| R3 (access control off) | c3.cross_process.process | ERR | 36 of 36 | DocumentSubgraphNotFoundError x1 | `20261114T185051Z-97edaf64` |
| R1i | c1.k8.process | ERR | 20 of 20 | ladybug file lock x14 | `20261114T185431Z-95507ca8` |
| R1i | c1.disjoint.k4.process | ERR | 0 of 20 | – | `20261114T191301Z-63ab727b` |
| R3 (access control off) | c4.ladder | CRASH | 0 of 5 | – | `20261114T191423Z-43cd092f` |
| R1i (access control off) | c2.writers.process | C2P | 0 of 20 | – | `20261114T193043Z-188df5a9` |
| R1i (access control off) | c2.writers.process | C2W | 0 of 20 | – | `20261114T193043Z-188df5a9` |
| R1i (access control off) | c2.writers.process | ERR | 20 of 20 | ladybug file lock x2 | `20261114T193043Z-188df5a9` |
| R1i | c3.cross_process.process | ERR | 0 of 36 | – | `20261114T195002Z-d40746c3` |
| R1i | c4.ladder | CRASH | 0 of 5 | – | `20261114T202544Z-f23205b5` |

## Invalid trials

| Backend | Scenario | Invalid trials | Reasons (distinct, first three) | Run |
|---|---|---|---|---|
| R1 | c1.k2.process | 20 of 20 | 2 of 4 operations had an unknown outcome | `20261114T131228Z-5b47435a` |
| R1 | c1.k4.process | 20 of 20 | 4 of 8 operations had an unknown outcome; 5 of 8 operations had an unknown outcome; 5 of 8 operations had an unknown outcome; release spread 1.092 ms exceeds the process gate 1.0 ms | `20261114T132931Z-134a3280` |
| R2 (access control off) | c1.k4.process | 18 of 20 | 1 of 8 operations had an unknown outcome; 1 of 8 operations had an unknown outcome; release spread 3.005 ms exceeds the process gate 1.0 ms; 1 of 8 operations had an unknown outcome; release spread 5.488 ms exceeds the process gate 1.0 ms | `20261114T133423Z-70f45910` |
| R1 | c1.k8.process | 20 of 20 | 11 of 16 operations had an unknown outcome; 11 of 16 operations had an unknown outcome; release spread 1.13 ms exceeds the process gate 1.0 ms; 11 of 16 operations had an unknown outcome; release spread 1.133 ms exceeds the process gate 1.0 ms | `20261114T134920Z-186e234c` |
| R1 | c1.disjoint.k4.process | 6 of 20 | release spread 1.382 ms exceeds the process gate 1.0 ms; release spread 2.468 ms exceeds the process gate 1.0 ms; release spread 2.702 ms exceeds the process gate 1.0 ms | `20261114T141347Z-b025f668` |
| R2 (access control off) | c1.disjoint.k4.process | 11 of 20 | 1 of 8 operations had an unknown outcome; 2 of 8 operations had an unknown outcome | `20261114T143626Z-f94d7606` |
| R1 (access control off) | c2.writers.process | 20 of 20 | 1 of 3 operations had an unknown outcome; 1 of 3 operations had an unknown outcome; release spread 2.337 ms exceeds the process gate 1.0 ms; 2 of 3 operations had an unknown outcome | `20261114T143808Z-c442cc14` |
| R2 (access control off) | c2.writers.process | 8 of 20 | 1 of 3 operations had an unknown outcome; release spread 31.134 ms exceeds the process gate 1.0 ms | `20261114T145753Z-d168cf57` |
| R3 (access control off) | c1.k8.process | 3 of 20 | release spread 1.246 ms exceeds the process gate 1.0 ms; release spread 1.842 ms exceeds the process gate 1.0 ms; release spread 2.205 ms exceeds the process gate 1.0 ms | `20261114T181325Z-73c88163` |
| R1i | c1.k2.process | 20 of 20 | 2 of 4 operations had an unknown outcome | `20261114T182011Z-03b8761e` |
| R3 (access control off) | c2.writers.process | 4 of 20 | 2 of 3 operations had an unknown outcome; release spread 1.012 ms exceeds the process gate 1.0 ms; 2 of 3 operations had an unknown outcome; release spread 1.32 ms exceeds the process gate 1.0 ms; release spread 1.599 ms exceeds the process gate 1.0 ms | `20261114T183825Z-c97d0d06` |
| R1i | c1.k4.process | 20 of 20 | 6 of 8 operations had an unknown outcome; 6 of 8 operations had an unknown outcome; release spread 4.142 ms exceeds the process gate 1.0 ms | `20261114T183831Z-97e05ac3` |
| R3 (access control off) | c3.cross_process.process | 36 of 36 | 1 of 2 operations had an unknown outcome | `20261114T185051Z-97edaf64` |
| R1i | c1.k8.process | 20 of 20 | 14 of 16 operations had an unknown outcome; 14 of 16 operations had an unknown outcome; release spread 1.114 ms exceeds the process gate 1.0 ms; 14 of 16 operations had an unknown outcome; release spread 9.346 ms exceeds the process gate 1.0 ms | `20261114T185431Z-95507ca8` |
| R3 (access control off) | c3.in_process | 1 of 2 | 1 ingest(s) did not succeed: {'type': 'target.RemoteError', 'message': 'DocumentSubgraphNotFoundError: Documen | `20261114T191258Z-e09326c6` |
| R1i | c1.disjoint.k4.process | 1 of 20 | release spread 1.063 ms exceeds the process gate 1.0 ms | `20261114T191301Z-63ab727b` |
| R1i (access control off) | c2.writers.process | 20 of 20 | 2 of 3 operations had an unknown outcome | `20261114T193043Z-188df5a9` |
