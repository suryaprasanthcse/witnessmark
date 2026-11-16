# M5: Omnigraph, O1 re-run: batch `m5d-20261116T003205Z`

Regenerated from `evidence/` by `python wm.py report --memory`. Do not edit by hand.

- Harness commit: `f7ae8f2f0be485b51f7aac672507c75c904b7af3` (dirty: false)
- Host: Windows-11-10.0.26300-SP0; 11th Gen Intel(R) Core(TM) i5-11320H @ 3.20GHz; 8 logical cores; 23.8 GB
- Docker: 29.9.3; VM limits 8 CPUs, 11.6 GB
- Runs: 1 (0 races, 0 case suites, 0 visibility, 1 cost curves, 0 failover matrices, 0 I6 control runs)

## I6a and I6b controls

| Build | Storage | Source | I6a: branch prefix / main ledger | I6a gapless and non-empty | I6b isolation | Run |
|---|---|---|---|---|---|---|
| v0.15.0 | local | end of O1 curve | 5 / 20 | yes | yes | `20261116T003206Z-579fed57` |

## O1 branch-creation cost

| Build | Storage | Nodes / edges | Siblings | Create median [IQR] (ms) | Stall median (ms) | Reader p99 before / during (ms) | Merge / delete median (ms) | Object requests / bytes, one create + delete | Run |
|---|---|---|---|---|---|---|---|---|---|
| v0.15.0 | local | 32000 / 32000 | 0 | 10.57 [8.26–12.19] | 0.68 | 8.53 / 7.55 | 7.67 / 5.05 | – | `20261116T003206Z-579fed57` |
| v0.15.0 | local | 32000 / 32000 | 4 | 9.05 [8.59–12.33] | 0.41 | 8.07 / 8.35 | 8.41 / 5.57 | – | `20261116T003206Z-579fed57` |
| v0.15.0 | local | 32000 / 32000 | 16 | 8.27 [8.06–8.30] | 0 | 8.85 / 8.71 | 8.27 / 5.77 | – | `20261116T003206Z-579fed57` |
| v0.15.0 | local | 32000 / 32000 | 64 | 10.42 [9.20–10.99] | 1.72 | 8.18 / 8.88 | 21.69 / 5.30 | – | `20261116T003206Z-579fed57` |
| v0.15.0 | local | 128000 / 128000 | 0 | 9.81 [8.15–11.22] | 1.45 | 8.79 / 10.05 | 9.16 / 5.35 | – | `20261116T003206Z-579fed57` |
| v0.15.0 | local | 128000 / 128000 | 4 | 10.61 [10.30–11.58] | 0.67 | 8.15 / 9.00 | 9.04 / 5.25 | – | `20261116T003206Z-579fed57` |
| v0.15.0 | local | 128000 / 128000 | 16 | 15.34 [12.42–25.79] | 1.34 | 8.73 / 9.60 | 9.03 / 6.00 | – | `20261116T003206Z-579fed57` |
| v0.15.0 | local | 128000 / 128000 | 64 | 9.81 [9.64–11.76] | 1.30 | 8.32 / 7.54 | 9.86 / 5.88 | – | `20261116T003206Z-579fed57` |
| v0.15.0 | local | 512000 / 512000 | 0 | 10.11 [9.67–10.95] | 1.40 | 8.98 / 9.39 | 13.59 / 6.28 | – | `20261116T003206Z-579fed57` |
| v0.15.0 | local | 512000 / 512000 | 4 | 10.43 [9.27–15.51] | 1.10 | 10.12 / 10.39 | 13.41 / 6.68 | – | `20261116T003206Z-579fed57` |
| v0.15.0 | local | 512000 / 512000 | 16 | 11.32 [10.05–12.05] | 1.98 | 9.04 / 10.57 | 13.11 / 6.42 | – | `20261116T003206Z-579fed57` |
| v0.15.0 | local | 512000 / 512000 | 64 | 12.62 [11.41–14.07] | 2.96 | 9.75 / 11.58 | 13.90 / 6.65 | – | `20261116T003206Z-579fed57` |

### Unrelated graph during branch creation

| Build | Storage | Nodes / edges | Siblings | Unrelated reader stall median (ms) | Unrelated writer stall median (ms) | Run |
|---|---|---|---|---|---|---|
| v0.15.0 | local | 32000 / 32000 | 0 | 6.51 | 9.26 | `20261116T003206Z-579fed57` |
| v0.15.0 | local | 32000 / 32000 | 4 | 6.55 | 8.59 | `20261116T003206Z-579fed57` |
| v0.15.0 | local | 32000 / 32000 | 16 | 5.72 | 8.27 | `20261116T003206Z-579fed57` |
| v0.15.0 | local | 32000 / 32000 | 64 | 6.95 | 10.42 | `20261116T003206Z-579fed57` |
| v0.15.0 | local | 128000 / 128000 | 0 | 6.42 | 9.81 | `20261116T003206Z-579fed57` |
| v0.15.0 | local | 128000 / 128000 | 4 | 6.61 | 10.61 | `20261116T003206Z-579fed57` |
| v0.15.0 | local | 128000 / 128000 | 16 | 6.90 | 15.34 | `20261116T003206Z-579fed57` |
| v0.15.0 | local | 128000 / 128000 | 64 | 6.11 | 6.84 | `20261116T003206Z-579fed57` |
| v0.15.0 | local | 512000 / 512000 | 0 | 6.60 | 10.11 | `20261116T003206Z-579fed57` |
| v0.15.0 | local | 512000 / 512000 | 4 | 6.20 | 10.43 | `20261116T003206Z-579fed57` |
| v0.15.0 | local | 512000 / 512000 | 16 | 6.34 | 11.32 | `20261116T003206Z-579fed57` |
| v0.15.0 | local | 512000 / 512000 | 64 | 6.59 | 12.62 | `20261116T003206Z-579fed57` |

### Copy weight

| Build | Storage | Nodes / edges | Create + claim + score + discard (ms) | Run |
|---|---|---|---|---|
| v0.15.0 | local | 32000 / 32000 | 74.87 | `20261116T003206Z-579fed57` |
| v0.15.0 | local | 128000 / 128000 | 97.90 | `20261116T003206Z-579fed57` |
| v0.15.0 | local | 512000 / 512000 | 209.23 | `20261116T003206Z-579fed57` |

### FalkorDB `GRAPH.COPY` sanity curve

Persistence during the curve: `appendfsync always`, `appendonly yes`; found beforehand: `appendfsync everysec`, `appendonly no`.

| Nodes / edges | Copy median [IQR] (ms) | S28 reference (ms) | Inside ±50% band | Delete median (ms) | Source reader stall median (ms) | Unrelated reader stall median (ms) | Unrelated writer stall median (ms) | RSS delta median (MB) | AOF bytes (last sample) |
|---|---|---|---|---|---|---|---|---|---|
| 32000 / 32000 | 85.16 [81.08–89.88] | 165 | yes | 6.54 | 84.79 | 84.85 | 85.09 | 5.10 | 27084520 |
| 128000 / 128000 | 474.68 [344.69–502.51] | 546 | yes | 8.42 | 474.64 | 474.68 | 436.73 | 11.50 | 79418761 |
| 512000 / 512000 | 1957.26 [1913.05–2046.56] | 2400 | yes | 8.00 | 1957.21 | 1957.15 | 1923.80 | 48.40 | 101343332 |
