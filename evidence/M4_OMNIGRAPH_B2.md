# M4: Omnigraph, second batch (stopped at the FalkorDB sanity band): batch `m4b-20261115T164749Z`

Regenerated from `evidence/` by `python wm.py report --memory`. Do not edit by hand.

- Harness commit: `48737aa9db52b3c2a9952646db4c6db2a1dac6d2` (dirty: false)
- Host: Windows-11-10.0.26300-SP0; 11th Gen Intel(R) Core(TM) i5-11320H @ 3.20GHz; 8 logical cores; 23.8 GB
- Docker: 29.9.3; VM limits 8 CPUs, 11.6 GB
- Runs: 1 (0 races, 0 case suites, 0 visibility, 1 cost curves, 0 failover matrices, 0 I6 control runs)

## I6a and I6b controls

| Build | Storage | Source | I6a: branch prefix / main ledger | I6a gapless and non-empty | I6b isolation | Run |
|---|---|---|---|---|---|---|
| v0.15.0 | local | end of O1 curve | 0 / 20 | NO (empty prefix, not exercised) | yes | `20261115T164756Z-236def5c` |

## O1 branch-creation cost

| Build | Storage | Nodes / edges | Siblings | Create median [IQR] (ms) | Stall median (ms) | Reader p99 before / during (ms) | Merge / delete median (ms) | Object requests / bytes, one create + delete | Run |
|---|---|---|---|---|---|---|---|---|---|
| v0.15.0 | local | 32000 / 32000 | 0 | 6.29 [5.68–6.40] | 0.87 | 27.44 / 6.07 | 14.09 / 5.76 | – | `20261115T164756Z-236def5c` |
| v0.15.0 | local | 32000 / 32000 | 4 | 5.98 [5.43–6.09] | 0 | 21.99 / 6.81 | 7.33 / 4.61 | – | `20261115T164756Z-236def5c` |
| v0.15.0 | local | 32000 / 32000 | 16 | 5.80 [5.40–5.80] | 0 | 26.47 / 5.48 | 8.70 / 5.21 | – | `20261115T164756Z-236def5c` |
| v0.15.0 | local | 32000 / 32000 | 64 | 6.68 [6.44–6.71] | 0.12 | 26.01 / 8.53 | 8.55 / 7.03 | – | `20261115T164756Z-236def5c` |
| v0.15.0 | local | 128000 / 128000 | 0 | 5.57 [5.25–5.99] | 0 | 26.57 / 5.75 | 8.30 / 5.17 | – | `20261115T164756Z-236def5c` |
| v0.15.0 | local | 128000 / 128000 | 4 | 6.12 [5.98–7.47] | 0 | 22.96 / 6.34 | 8.89 / 5.54 | – | `20261115T164756Z-236def5c` |
| v0.15.0 | local | 128000 / 128000 | 16 | 5.99 [5.80–6.15] | 0 | 26.01 / 7.90 | 9.50 / 5.56 | – | `20261115T164756Z-236def5c` |
| v0.15.0 | local | 128000 / 128000 | 64 | 6.18 [5.84–7.50] | 0 | 25.07 / 7.23 | 8.89 / 5.42 | – | `20261115T164756Z-236def5c` |
| v0.15.0 | local | 512000 / 512000 | 0 | 6.37 [6.28–20.11] | 0 | 28.05 / 16.99 | 38.50 / 5.99 | – | `20261115T164756Z-236def5c` |
| v0.15.0 | local | 512000 / 512000 | 4 | 9.64 [8.54–11.72] | 0.53 | 24.89 / 13.02 | 18.45 / 6.69 | – | `20261115T164756Z-236def5c` |
| v0.15.0 | local | 512000 / 512000 | 16 | 7.55 [6.58–9.24] | 0.10 | 23.49 / 6.78 | 14.80 / 7.17 | – | `20261115T164756Z-236def5c` |
| v0.15.0 | local | 512000 / 512000 | 64 | 7.61 [7.19–9.64] | 0 | 19.37 / 6.80 | 12.24 / 6.08 | – | `20261115T164756Z-236def5c` |

### Copy weight

| Build | Storage | Nodes / edges | Create + claim + score + discard (ms) | Run |
|---|---|---|---|---|
| v0.15.0 | local | 32000 / 32000 | 62.28 | `20261115T164756Z-236def5c` |
| v0.15.0 | local | 128000 / 128000 | 89.34 | `20261115T164756Z-236def5c` |
| v0.15.0 | local | 512000 / 512000 | 214.26 | `20261115T164756Z-236def5c` |

### FalkorDB `GRAPH.COPY` sanity curve

| Nodes / edges | Copy median [IQR] (ms) | S28 reference (ms) | Inside ±50% band | Delete median (ms) | Source reader stall median (ms) | Unrelated reader stall median (ms) | Unrelated writer stall median (ms) | RSS delta median (MB) | AOF bytes (last sample) |
|---|---|---|---|---|---|---|---|---|---|
| 32000 / 32000 | 64.29 [63.91–65.01] | 165 | NO | 1.21 | 64.16 | 64.19 | 64.13 | 4.96 | – |
| 128000 / 128000 | 279.17 [256.11–417.56] | 546 | yes | 1.28 | 278.76 | 278.82 | 278.87 | 9.50 | – |
| 512000 / 512000 | 1025.05 [1023.18–1045.23] | 2400 | NO | 1.23 | 1024.63 | 1024.60 | 1025.02 | 53.60 | – |
