# M4: Omnigraph, third batch (driver crash and lease setting): batch `m4c-20261115T165831Z`

Regenerated from `evidence/` by `python wm.py report --memory`. Do not edit by hand.

- Harness commit: `8f7bb3b75c7570ebc433706456b90db6c4eb7e0a` (dirty: false)
- Host: Windows-11-10.0.26300-SP0; 11th Gen Intel(R) Core(TM) i5-11320H @ 3.20GHz; 8 logical cores; 23.8 GB
- Docker: 29.9.3; VM limits 8 CPUs, 11.6 GB
- Runs: 3 (0 races, 0 case suites, 0 visibility, 3 cost curves, 0 failover matrices, 0 I6 control runs)

## Runs that did not complete

[measured] These runs wrote their planned manifest and then stopped; no result was inferred from them.

| Build | Storage | Scenario | Error | Run |
|---|---|---|---|---|
| v0.15.0 | minio | o1.branch_cost | RuntimeError: create branch o1-measure-512000-0-2: unknown connection: Remote end closed connection without response | `20261115T170604Z-7d473a53` |
| v0.15.0 | proxy | o1.branch_cost | RuntimeError: load edges 205824:209920: unknown internal: storage: LanceError(IO): single PUT of wm-m4-o1-v0-15-0-proxy/graphs/witnessmark.omni/edges/0000000000000008-000000000000001d/data/000000000101010101110010a2ec76452b896411c9c656a935.lance failed after 25.223µs (98156 bytes, LANCE_INITIAL_UPLOAD_SIZE=5242880 bytes, LANCE_UPLOAD_CONCURRENCY=10): Generic owned storage error: storage mutation admission is closed,  | `20261115T171130Z-e052669e` |

## I6a and I6b controls

| Build | Storage | Source | I6a: branch prefix / main ledger | I6a gapless and non-empty | I6b isolation | Run |
|---|---|---|---|---|---|---|
| v0.15.0 | local | end of O1 curve | 0 / 20 | NO (empty prefix, not exercised) | yes | `20261115T165838Z-b4925bd5` |

## O1 branch-creation cost

| Build | Storage | Nodes / edges | Siblings | Create median [IQR] (ms) | Stall median (ms) | Reader p99 before / during (ms) | Merge / delete median (ms) | Object requests / bytes, one create + delete | Run |
|---|---|---|---|---|---|---|---|---|---|
| v0.15.0 | local | 32000 / 32000 | 0 | 5.42 [5.07–5.43] | 0 | 26.85 / 7.32 | 25.04 / 5.03 | – | `20261115T165838Z-b4925bd5` |
| v0.15.0 | local | 32000 / 32000 | 4 | 5.17 [5.04–5.51] | 0.17 | 25.66 / 21.02 | 14.76 / 4.67 | – | `20261115T165838Z-b4925bd5` |
| v0.15.0 | local | 32000 / 32000 | 16 | 6.12 [5.84–6.49] | 0.58 | 28.25 / 8.81 | 14.99 / 5.66 | – | `20261115T165838Z-b4925bd5` |
| v0.15.0 | local | 32000 / 32000 | 64 | 6.21 [6.00–6.83] | 0 | 24.06 / 20.85 | 20.19 / 5.15 | – | `20261115T165838Z-b4925bd5` |
| v0.15.0 | local | 128000 / 128000 | 0 | 5.56 [5.37–5.90] | 0 | 24.72 / 6.19 | 9.16 / 5.27 | – | `20261115T165838Z-b4925bd5` |
| v0.15.0 | local | 128000 / 128000 | 4 | 6.13 [5.85–7.28] | 0 | 25.39 / 7.36 | 10.08 / 5.27 | – | `20261115T165838Z-b4925bd5` |
| v0.15.0 | local | 128000 / 128000 | 16 | 6.48 [6.38–16.74] | 0 | 21.88 / 5.93 | 12.02 / 5.45 | – | `20261115T165838Z-b4925bd5` |
| v0.15.0 | local | 128000 / 128000 | 64 | 7.35 [6.45–19.98] | 0 | 28.26 / 7.27 | 9.49 / 5.70 | – | `20261115T165838Z-b4925bd5` |
| v0.15.0 | local | 512000 / 512000 | 0 | 7.31 [6.72–18.56] | 0.38 | 25.24 / 9.56 | 13.38 / 5.80 | – | `20261115T165838Z-b4925bd5` |
| v0.15.0 | local | 512000 / 512000 | 4 | 6.45 [6.42–7.39] | 0 | 28.10 / 9.04 | 13.35 / 6.97 | – | `20261115T165838Z-b4925bd5` |
| v0.15.0 | local | 512000 / 512000 | 16 | 8.24 [7.55–10.00] | 0.13 | 25.79 / 11.03 | 11.91 / 5.84 | – | `20261115T165838Z-b4925bd5` |
| v0.15.0 | local | 512000 / 512000 | 64 | 7.77 [7.74–8.71] | 0 | 20.51 / 7.73 | 14.18 / 8.01 | – | `20261115T165838Z-b4925bd5` |

### Copy weight

| Build | Storage | Nodes / edges | Create + claim + score + discard (ms) | Run |
|---|---|---|---|---|
| v0.15.0 | local | 32000 / 32000 | 105.76 | `20261115T165838Z-b4925bd5` |
| v0.15.0 | local | 128000 / 128000 | 91.88 | `20261115T165838Z-b4925bd5` |
| v0.15.0 | local | 512000 / 512000 | 325.33 | `20261115T165838Z-b4925bd5` |

### FalkorDB `GRAPH.COPY` sanity curve

Persistence during the curve: `appendfsync always`, `appendonly yes`; found beforehand: `appendfsync everysec`, `appendonly no`.

| Nodes / edges | Copy median [IQR] (ms) | S28 reference (ms) | Inside ±50% band | Delete median (ms) | Source reader stall median (ms) | Unrelated reader stall median (ms) | Unrelated writer stall median (ms) | RSS delta median (MB) | AOF bytes (last sample) |
|---|---|---|---|---|---|---|---|---|---|
| 32000 / 32000 | 105.15 [90.41–126.33] | 165 | yes | 6.93 | 105.15 | 105.06 | 104.07 | 5.30 | 27065562 |
| 128000 / 128000 | 320.27 [315.11–455.50] | 546 | yes | 6.46 | 315.11 | 315.11 | 314.61 | 10.30 | 73668117 |
| 512000 / 512000 | 1502.80 [1243.74–1595.14] | 2400 | yes | 9.27 | 1502.80 | 1502.75 | 1498.16 | 44.20 | 101365815 |
