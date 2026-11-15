# M4: Omnigraph: batch `m4d-20261115T172246Z`

Regenerated from `evidence/` by `python wm.py report --memory`. Do not edit by hand.

- Harness commit: `2a02bd81dbf06b61949f995a039e084dd9350d88` (dirty: false)
- Host: Windows-11-10.0.26300-SP0; 11th Gen Intel(R) Core(TM) i5-11320H @ 3.20GHz; 8 logical cores; 23.8 GB
- Docker: 29.9.3; VM limits 8 CPUs, 11.6 GB
- Runs: 12 (0 races, 0 case suites, 2 visibility, 6 cost curves, 4 failover matrices, 0 I6 control runs)

## I6a and I6b controls

| Build | Storage | Source | I6a: branch prefix / main ledger | I6a gapless and non-empty | I6b isolation | Run |
|---|---|---|---|---|---|---|
| v0.15.0 | local | end of O1 curve | 0 / 20 | NO (empty prefix, not exercised) | yes | `20261115T172253Z-0adb5788` |
| v0.15.0 | minio | end of O1 curve | 0 / 20 | NO (empty prefix, not exercised) | yes | `20261115T173025Z-fc74457b` |
| v0.15.0 | proxy | end of O1 curve | 0 / 15 | NO (empty prefix, not exercised) | yes | `20261115T173716Z-d303435d` |
| edge-b2dbaff | local | end of O1 curve | 0 / 20 | NO (empty prefix, not exercised) | yes | `20261115T175653Z-12eb6ff6` |
| edge-b2dbaff | minio | end of O1 curve | 0 / 20 | NO (empty prefix, not exercised) | yes | `20261115T180251Z-742224c3` |
| edge-b2dbaff | proxy | end of O1 curve | 0 / 15 | NO (empty prefix, not exercised) | yes | `20261115T181001Z-adf60896` |

## O1 branch-creation cost

| Build | Storage | Nodes / edges | Siblings | Create median [IQR] (ms) | Stall median (ms) | Reader p99 before / during (ms) | Merge / delete median (ms) | Object requests / bytes, one create + delete | Run |
|---|---|---|---|---|---|---|---|---|---|
| v0.15.0 | local | 32000 / 32000 | 0 | 6.87 [6.36–19.96] | 0 | 20.40 / 8.97 | 24.85 / 5.98 | – | `20261115T172253Z-0adb5788` |
| v0.15.0 | local | 32000 / 32000 | 4 | 6.87 [6.77–6.87] | 0 | 17.83 / 7.41 | 9.30 / 6.48 | – | `20261115T172253Z-0adb5788` |
| v0.15.0 | local | 32000 / 32000 | 16 | 7.39 [6.37–7.61] | 0 | 19.17 / 9.97 | 9.00 / 5.98 | – | `20261115T172253Z-0adb5788` |
| v0.15.0 | local | 32000 / 32000 | 64 | 8.25 [7.87–11.25] | 0 | 23.49 / 8.43 | 9.47 / 6.70 | – | `20261115T172253Z-0adb5788` |
| v0.15.0 | local | 128000 / 128000 | 0 | 6.16 [5.85–6.50] | 0 | 14.45 / 8.73 | 10.28 / 6.59 | – | `20261115T172253Z-0adb5788` |
| v0.15.0 | local | 128000 / 128000 | 4 | 7.28 [6.39–8.15] | 0.04 | 20.80 / 9.64 | 10.08 / 5.82 | – | `20261115T172253Z-0adb5788` |
| v0.15.0 | local | 128000 / 128000 | 16 | 7.05 [6.01–7.69] | 0.12 | 19.16 / 7.11 | 8.49 / 5.15 | – | `20261115T172253Z-0adb5788` |
| v0.15.0 | local | 128000 / 128000 | 64 | 6.21 [6.11–6.45] | 0.66 | 23.00 / 9.36 | 9.36 / 5.50 | – | `20261115T172253Z-0adb5788` |
| v0.15.0 | local | 512000 / 512000 | 0 | 5.98 [5.92–6.31] | 0.04 | 23.73 / 6.71 | 14.90 / 6.13 | – | `20261115T172253Z-0adb5788` |
| v0.15.0 | local | 512000 / 512000 | 4 | 6.12 [5.83–6.98] | 0 | 23.36 / 7.80 | 30.87 / 5.94 | – | `20261115T172253Z-0adb5788` |
| v0.15.0 | local | 512000 / 512000 | 16 | 6.27 [6.19–7.48] | 0.39 | 28.12 / 7.80 | 11.79 / 5.74 | – | `20261115T172253Z-0adb5788` |
| v0.15.0 | local | 512000 / 512000 | 64 | 6.64 [6.27–6.71] | 0 | 26.93 / 22.59 | 14.22 / 6.83 | – | `20261115T172253Z-0adb5788` |
| v0.15.0 | minio | 32000 / 32000 | 0 | 70.88 [67.60–82.88] | 60.25 | 29.31 / 70.16 | 22.74 / 69.85 | – | `20261115T173025Z-fc74457b` |
| v0.15.0 | minio | 32000 / 32000 | 4 | 42.91 [42.26–45.28] | 32.96 | 25.19 / 44.61 | 15.76 / 35.39 | – | `20261115T173025Z-fc74457b` |
| v0.15.0 | minio | 32000 / 32000 | 16 | 37.44 [35.42–37.50] | 31.27 | 26.04 / 41.36 | 15.72 / 33.18 | – | `20261115T173025Z-fc74457b` |
| v0.15.0 | minio | 32000 / 32000 | 64 | 45.50 [44.10–64.70] | 35.20 | 23.81 / 44.68 | 22.39 / 32.75 | – | `20261115T173025Z-fc74457b` |
| v0.15.0 | minio | 128000 / 128000 | 0 | 40.90 [36.31–52.75] | 28.14 | 28.80 / 39.93 | 16.98 / 32.33 | – | `20261115T173025Z-fc74457b` |
| v0.15.0 | minio | 128000 / 128000 | 4 | 36.47 [33.82–37.95] | 27.27 | 27.91 / 38.52 | 36.10 / 30.59 | – | `20261115T173025Z-fc74457b` |
| v0.15.0 | minio | 128000 / 128000 | 16 | 36.16 [36.02–37.95] | 29.64 | 29.29 / 40.36 | 28.40 / 32.28 | – | `20261115T173025Z-fc74457b` |
| v0.15.0 | minio | 128000 / 128000 | 64 | 41.97 [41.94–45.53] | 33.95 | 23.42 / 46.21 | 18.64 / 33.64 | – | `20261115T173025Z-fc74457b` |
| v0.15.0 | minio | 512000 / 512000 | 0 | 42.31 [40.10–51.70] | 30.94 | 29.50 / 46.48 | 35.96 / 42.61 | – | `20261115T173025Z-fc74457b` |
| v0.15.0 | minio | 512000 / 512000 | 4 | 41.73 [40.24–51.41] | 32.25 | 26.06 / 45.92 | 30.08 / 44.25 | – | `20261115T173025Z-fc74457b` |
| v0.15.0 | minio | 512000 / 512000 | 16 | 41.14 [37.89–41.44] | 30.40 | 22.43 / 41.69 | 33.18 / 41.12 | – | `20261115T173025Z-fc74457b` |
| v0.15.0 | minio | 512000 / 512000 | 64 | 49.57 [45.27–50.43] | 42.72 | 24.37 / 57.36 | 40.06 / 41.57 | – | `20261115T173025Z-fc74457b` |
| v0.15.0 | proxy | 32000 / 32000 | 0 | – | 386.87 | 104.74 / 509.52 | 417.30 / 614.25 | 34 / 61784 | `20261115T173716Z-d303435d` |
| v0.15.0 | proxy | 32000 / 32000 | 4 | – | 305.50 | 105.36 / 430.26 | 388.31 / 574.96 | 34 / 66758 | `20261115T173716Z-d303435d` |
| v0.15.0 | proxy | 32000 / 32000 | 16 | – | 301.00 | 123.84 / 423.01 | 382.65 / 568.77 | 34 / 81710 | `20261115T173716Z-d303435d` |
| v0.15.0 | proxy | 32000 / 32000 | 64 | – | 314.25 | 104.73 / 438.34 | 391.99 / 576.71 | 34 / 141422 | `20261115T173716Z-d303435d` |
| v0.15.0 | proxy | 128000 / 128000 | 0 | – | 388.30 | 108.17 / 513.18 | 431.91 / 630.36 | 34 / 123215 | `20261115T173716Z-d303435d` |
| v0.15.0 | proxy | 128000 / 128000 | 4 | – | 301.92 | 108.12 / 424.53 | 383.99 / 589.81 | 34 / 128191 | `20261115T173716Z-d303435d` |
| v0.15.0 | proxy | 128000 / 128000 | 16 | – | 290.51 | 119.65 / 420.74 | 391.94 / 577.37 | 34 / 143139 | `20261115T173716Z-d303435d` |
| v0.15.0 | proxy | 128000 / 128000 | 64 | – | 306.06 | 116.80 / 434.90 | 386.62 / 581.06 | 38 / 203955 | `20261115T173716Z-d303435d` |
| v0.15.0 | proxy | 512000 / 512000 | 0 | – | 398.85 | 110.06 / 523.10 | 484.60 / 639.11 | 37 / 422120 | `20261115T173716Z-d303435d` |
| v0.15.0 | proxy | 512000 / 512000 | 4 | – | 311.74 | 115.94 / 438.14 | 434.48 / 610.02 | 37 / 427096 | `20261115T173716Z-d303435d` |
| v0.15.0 | proxy | 512000 / 512000 | 16 | – | 320.03 | 113.66 / 452.53 | 436.95 / 595.30 | 37 / 442047 | `20261115T173716Z-d303435d` |
| v0.15.0 | proxy | 512000 / 512000 | 64 | – | 303.70 | 123.64 / 428.75 | 435.01 / 587.02 | 39 / 502201 | `20261115T173716Z-d303435d` |
| edge-b2dbaff | local | 32000 / 32000 | 0 | 6.99 [5.82–7.49] | 0.75 | 24.95 / 18.53 | 9.61 / 5.75 | – | `20261115T175653Z-12eb6ff6` |
| edge-b2dbaff | local | 32000 / 32000 | 4 | 5.69 [5.37–6.08] | 0 | 25.14 / 6.86 | 10.64 / 5.67 | – | `20261115T175653Z-12eb6ff6` |
| edge-b2dbaff | local | 32000 / 32000 | 16 | 8.26 [6.26–8.38] | 0 | 23.05 / 7.57 | 8.13 / 5.14 | – | `20261115T175653Z-12eb6ff6` |
| edge-b2dbaff | local | 32000 / 32000 | 64 | 7.86 [6.55–9.09] | 0 | 17.53 / 7.69 | 21.24 / 5.62 | – | `20261115T175653Z-12eb6ff6` |
| edge-b2dbaff | local | 128000 / 128000 | 0 | 6.43 [6.11–6.46] | 0 | 19.02 / 24.16 | 13.07 / 5.83 | – | `20261115T175653Z-12eb6ff6` |
| edge-b2dbaff | local | 128000 / 128000 | 4 | 7.32 [7.02–7.85] | 0 | 19.70 / 7.53 | 11.71 / 6.34 | – | `20261115T175653Z-12eb6ff6` |
| edge-b2dbaff | local | 128000 / 128000 | 16 | 8.64 [7.92–9.84] | 0 | 27.00 / 10.45 | 11.38 / 6.10 | – | `20261115T175653Z-12eb6ff6` |
| edge-b2dbaff | local | 128000 / 128000 | 64 | 11.25 [8.94–12.25] | 0 | 19.30 / 10.47 | 10.58 / 7.03 | – | `20261115T175653Z-12eb6ff6` |
| edge-b2dbaff | local | 512000 / 512000 | 0 | 5.35 [5.21–5.53] | 0 | 26.53 / 7.97 | 19.95 / 5.74 | – | `20261115T175653Z-12eb6ff6` |
| edge-b2dbaff | local | 512000 / 512000 | 4 | 5.72 [5.56–11.51] | 0 | 27.21 / 7.73 | 13.35 / 6.14 | – | `20261115T175653Z-12eb6ff6` |
| edge-b2dbaff | local | 512000 / 512000 | 16 | 7.77 [5.54–8.21] | 0 | 19.06 / 8.84 | 19.90 / 8.53 | – | `20261115T175653Z-12eb6ff6` |
| edge-b2dbaff | local | 512000 / 512000 | 64 | 6.95 [6.83–14.78] | 0.24 | 24.40 / 9.15 | 26.88 / 6.97 | – | `20261115T175653Z-12eb6ff6` |
| edge-b2dbaff | minio | 32000 / 32000 | 0 | 48.77 [42.09–49.95] | 36.91 | 19.95 / 47.32 | 15.27 / 39.49 | – | `20261115T180251Z-742224c3` |
| edge-b2dbaff | minio | 32000 / 32000 | 4 | 40.93 [38.97–45.15] | 32.53 | 28.68 / 44.37 | 17.33 / 36.21 | – | `20261115T180251Z-742224c3` |
| edge-b2dbaff | minio | 32000 / 32000 | 16 | 47.20 [41.41–49.45] | 39.61 | 30.34 / 49.62 | 15.41 / 34.87 | – | `20261115T180251Z-742224c3` |
| edge-b2dbaff | minio | 32000 / 32000 | 64 | 88.58 [54.16–97.31] | 80.59 | 21.76 / 96.65 | 19.36 / 70.19 | – | `20261115T180251Z-742224c3` |
| edge-b2dbaff | minio | 128000 / 128000 | 0 | 48.12 [46.36–72.58] | 40.60 | 29.83 / 51.14 | 16.72 / 45.52 | – | `20261115T180251Z-742224c3` |
| edge-b2dbaff | minio | 128000 / 128000 | 4 | 86.91 [61.66–151.49] | 75.28 | 24.74 / 86.42 | 28.72 / 97.52 | – | `20261115T180251Z-742224c3` |
| edge-b2dbaff | minio | 128000 / 128000 | 16 | 46.16 [41.02–55.47] | 35.45 | 24.45 / 59.02 | 23.88 / 37.85 | – | `20261115T180251Z-742224c3` |
| edge-b2dbaff | minio | 128000 / 128000 | 64 | 49.08 [49.05–57.29] | 38.27 | 20.11 / 48.76 | 19.38 / 35.76 | – | `20261115T180251Z-742224c3` |
| edge-b2dbaff | minio | 512000 / 512000 | 0 | 40.93 [38.17–45.57] | 28.98 | 32.48 / 42.61 | 32.65 / 37.03 | – | `20261115T180251Z-742224c3` |
| edge-b2dbaff | minio | 512000 / 512000 | 4 | 38.18 [37.59–54.20] | 28.47 | 33.52 / 39.49 | 43.04 / 37.43 | – | `20261115T180251Z-742224c3` |
| edge-b2dbaff | minio | 512000 / 512000 | 16 | 37.37 [37.34–39.44] | 29.98 | 29.03 / 40.59 | 34.94 / 37.84 | – | `20261115T180251Z-742224c3` |
| edge-b2dbaff | minio | 512000 / 512000 | 64 | 43.66 [43.45–64.79] | 34.43 | 29.74 / 45.13 | 55.27 / 38.72 | – | `20261115T180251Z-742224c3` |
| edge-b2dbaff | proxy | 32000 / 32000 | 0 | – | 401.02 | 99.76 / 521.10 | 424.64 / 620.05 | 34 / 62142 | `20261115T181001Z-adf60896` |
| edge-b2dbaff | proxy | 32000 / 32000 | 4 | – | 294.79 | 118.27 / 421.26 | 384.80 / 575.76 | 34 / 67198 | `20261115T181001Z-adf60896` |
| edge-b2dbaff | proxy | 32000 / 32000 | 16 | – | 307.03 | 108.30 / 433.40 | 377.52 / 585.59 | 34 / 82390 | `20261115T181001Z-adf60896` |
| edge-b2dbaff | proxy | 32000 / 32000 | 64 | – | 298.09 | 112.59 / 426.30 | 379.39 / 573.14 | 34 / 143060 | `20261115T181001Z-adf60896` |
| edge-b2dbaff | proxy | 128000 / 128000 | 0 | – | 392.61 | 105.12 / 527.16 | 416.29 / 631.06 | 34 / 123995 | `20261115T181001Z-adf60896` |
| edge-b2dbaff | proxy | 128000 / 128000 | 4 | – | 303.99 | 122.52 / 432.34 | 381.63 / 588.82 | 34 / 129051 | `20261115T181001Z-adf60896` |
| edge-b2dbaff | proxy | 128000 / 128000 | 16 | – | 308.70 | 116.69 / 439.10 | 388.26 / 577.33 | 34 / 144241 | `20261115T181001Z-adf60896` |
| edge-b2dbaff | proxy | 128000 / 128000 | 64 | – | 319.43 | 104.12 / 444.00 | 383.19 / 592.84 | 34 / 204913 | `20261115T181001Z-adf60896` |
| edge-b2dbaff | proxy | 512000 / 512000 | 0 | – | 408.87 | 120.37 / 527.74 | 473.26 / 637.76 | 37 / 425485 | `20261115T181001Z-adf60896` |
| edge-b2dbaff | proxy | 512000 / 512000 | 4 | – | 300.97 | 110.60 / 428.03 | 436.30 / 601.38 | 37 / 430541 | `20261115T181001Z-adf60896` |
| edge-b2dbaff | proxy | 512000 / 512000 | 16 | – | 301.09 | 115.81 / 431.21 | 437.82 / 585.77 | 37 / 445731 | `20261115T181001Z-adf60896` |
| edge-b2dbaff | proxy | 512000 / 512000 | 64 | – | 305.00 | 117.09 / 429.73 | 440.83 / 584.32 | 37 / 506403 | `20261115T181001Z-adf60896` |

### Copy weight

| Build | Storage | Nodes / edges | Create + claim + score + discard (ms) | Run |
|---|---|---|---|---|
| v0.15.0 | local | 32000 / 32000 | 87.18 | `20261115T172253Z-0adb5788` |
| v0.15.0 | local | 128000 / 128000 | 90.00 | `20261115T172253Z-0adb5788` |
| v0.15.0 | local | 512000 / 512000 | 200.64 | `20261115T172253Z-0adb5788` |
| v0.15.0 | minio | 32000 / 32000 | 248.12 | `20261115T173025Z-fc74457b` |
| v0.15.0 | minio | 128000 / 128000 | 274.87 | `20261115T173025Z-fc74457b` |
| v0.15.0 | minio | 512000 / 512000 | 578.77 | `20261115T173025Z-fc74457b` |
| v0.15.0 | proxy | 32000 / 32000 | 3225.30 | `20261115T173716Z-d303435d` |
| v0.15.0 | proxy | 128000 / 128000 | 3296.11 | `20261115T173716Z-d303435d` |
| v0.15.0 | proxy | 512000 / 512000 | 11207.02 | `20261115T173716Z-d303435d` |
| edge-b2dbaff | local | 32000 / 32000 | 83.72 | `20261115T175653Z-12eb6ff6` |
| edge-b2dbaff | local | 128000 / 128000 | 115.07 | `20261115T175653Z-12eb6ff6` |
| edge-b2dbaff | local | 512000 / 512000 | 195.66 | `20261115T175653Z-12eb6ff6` |
| edge-b2dbaff | minio | 32000 / 32000 | 2111.24 | `20261115T180251Z-742224c3` |
| edge-b2dbaff | minio | 128000 / 128000 | 319.12 | `20261115T180251Z-742224c3` |
| edge-b2dbaff | minio | 512000 / 512000 | 576.71 | `20261115T180251Z-742224c3` |
| edge-b2dbaff | proxy | 32000 / 32000 | 3193.78 | `20261115T181001Z-adf60896` |
| edge-b2dbaff | proxy | 128000 / 128000 | 3435.95 | `20261115T181001Z-adf60896` |
| edge-b2dbaff | proxy | 512000 / 512000 | 5280.35 | `20261115T181001Z-adf60896` |

### FalkorDB `GRAPH.COPY` sanity curve

Persistence during the curve: `appendfsync always`, `appendonly yes`; found beforehand: `appendfsync everysec`, `appendonly no`.

| Nodes / edges | Copy median [IQR] (ms) | S28 reference (ms) | Inside ±50% band | Delete median (ms) | Source reader stall median (ms) | Unrelated reader stall median (ms) | Unrelated writer stall median (ms) | RSS delta median (MB) | AOF bytes (last sample) |
|---|---|---|---|---|---|---|---|---|---|
| 32000 / 32000 | 95.34 [87.34–118.16] | 165 | yes | 8.24 | 95.08 | 95.11 | 95.28 | 3.60 | 50756284 |
| 128000 / 128000 | 441.65 [379.38–471.21] | 546 | yes | 8.78 | 441.65 | 441.65 | 419.16 | 9.30 | 79417718 |
| 512000 / 512000 | 1820.03 [1594.88–1823.30] | 2400 | yes | 8.91 | 1819.98 | 1819.85 | 1799.04 | 47.20 | 101372512 |

## O4 failover acceptance matrix

| Build | Storage | Phase | Variant | Successor ready | A result | B result | Fence | Scanned via | Integrity scan | Acknowledged writes missing | Classification | Run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v0.15.0 | local | p1 | a | no | ok | – | not engaged | A (stale server) | ok | – | NOT_EXERCISED | `20261115T182902Z-7b344b82` |
| v0.15.0 | local | p1 | b | no | ok | – | not engaged | A (stale server) | ok | – | NOT_EXERCISED | `20261115T182902Z-7b344b82` |
| v0.15.0 | local | p2 | a | no | ok | – | not engaged | A (stale server) | ok | – | NOT_EXERCISED | `20261115T182902Z-7b344b82` |
| v0.15.0 | local | p2 | b | no | ok | – | not engaged | A (stale server) | ok | – | NOT_EXERCISED | `20261115T182902Z-7b344b82` |
| v0.15.0 | local | p3 | a | no | ok | – | not engaged | A (stale server) | ok | – | NOT_EXERCISED | `20261115T182902Z-7b344b82` |
| v0.15.0 | local | p3 | b | no | ok | – | not engaged | A (stale server) | ok | – | NOT_EXERCISED | `20261115T182902Z-7b344b82` |
| v0.15.0 | minio | p1 | a | yes | service_unavailable | – | not engaged | A (stale server) | NOT checked | – | BOUNDARY | `20261115T183001Z-3dcbea3c` |
| v0.15.0 | minio | p1 | b | yes | connection | ok | not engaged | A (stale server) | NOT checked | – | BOUNDARY | `20261115T183001Z-3dcbea3c` |
| v0.15.0 | minio | p2 | a | yes | internal | – | not engaged | A (stale server) | NOT checked | – | BOUNDARY | `20261115T183001Z-3dcbea3c` |
| v0.15.0 | minio | p2 | b | yes | ok | ok | not engaged | A (stale server) | NOT checked | – | BOUNDARY | `20261115T183001Z-3dcbea3c` |
| v0.15.0 | minio | p3 | a | yes | internal | – | not engaged | A (stale server) | NOT checked | – | BOUNDARY | `20261115T183001Z-3dcbea3c` |
| v0.15.0 | minio | p3 | b | yes | internal | ok | not engaged | A (stale server) | NOT checked | – | BOUNDARY | `20261115T183001Z-3dcbea3c` |
| edge-b2dbaff | local | p1 | a | no | ok | – | not engaged | A (stale server) | ok | – | NOT_EXERCISED | `20261115T183207Z-7c770991` |
| edge-b2dbaff | local | p1 | b | no | ok | – | not engaged | A (stale server) | ok | – | NOT_EXERCISED | `20261115T183207Z-7c770991` |
| edge-b2dbaff | local | p2 | a | no | ok | – | not engaged | A (stale server) | ok | – | NOT_EXERCISED | `20261115T183207Z-7c770991` |
| edge-b2dbaff | local | p2 | b | no | ok | – | not engaged | A (stale server) | ok | – | NOT_EXERCISED | `20261115T183207Z-7c770991` |
| edge-b2dbaff | local | p3 | a | no | ok | – | not engaged | A (stale server) | ok | – | NOT_EXERCISED | `20261115T183207Z-7c770991` |
| edge-b2dbaff | local | p3 | b | no | ok | – | not engaged | A (stale server) | ok | – | NOT_EXERCISED | `20261115T183207Z-7c770991` |
| edge-b2dbaff | minio | p1 | a | yes | connection | – | not engaged | A (stale server) | NOT checked | – | NOT_EXERCISED | `20261115T183306Z-1727e3ef` |
| edge-b2dbaff | minio | p1 | b | yes | connection | ok | not engaged | A (stale server) | NOT checked | – | NOT_EXERCISED | `20261115T183306Z-1727e3ef` |
| edge-b2dbaff | minio | p2 | a | yes | internal | – | not engaged | A (stale server) | NOT checked | – | NOT_EXERCISED | `20261115T183306Z-1727e3ef` |
| edge-b2dbaff | minio | p2 | b | yes | internal | ok | not engaged | A (stale server) | NOT checked | – | NOT_EXERCISED | `20261115T183306Z-1727e3ef` |
| edge-b2dbaff | minio | p3 | a | yes | internal | – | not engaged | A (stale server) | NOT checked | – | NOT_EXERCISED | `20261115T183306Z-1727e3ef` |
| edge-b2dbaff | minio | p3 | b | yes | internal | ok | not engaged | A (stale server) | NOT checked | – | NOT_EXERCISED | `20261115T183306Z-1727e3ef` |

BOUNDARY: a failover took place on the stable release, which predates the epoch fence; its documented deployment rule is its only protection. NOT_EXERCISED: the harness did not perform a documented step (the epoch claim, an embedding-program call, or the local ownership transfer), so the cell says nothing about the fence. No cell is a fence pass, and none is a fence failure.

## O5 cross-process read your writes

| Build | Storage | Second process | Write acknowledged | Seen | Attempts | Staleness (ms) | Run |
|---|---|---|---|---|---|---|---|
| v0.15.0 | local | wm-omnigraph-b | yes | yes | 1 | 1523.79 | `20261115T183504Z-eb41bb89` |
| edge-b2dbaff | local | wm-omnigraph-b | yes | yes | 1 | 1334.60 | `20261115T183511Z-4d593c85` |
