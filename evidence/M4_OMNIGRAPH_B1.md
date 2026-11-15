# M4: Omnigraph, first batch (harness failures): batch `m4-20261115T153804Z`

Regenerated from `evidence/` by `python wm.py report --memory`. Do not edit by hand.

- Harness commit: `46adb1de2d26c14e5056499079fe18d651afbc2e` (dirty: false)
- Host: Windows-11-10.0.26300-SP0; 11th Gen Intel(R) Core(TM) i5-11320H @ 3.20GHz; 8 logical cores; 23.8 GB
- Docker: 29.9.3; VM limits 8 CPUs, 11.6 GB
- Runs: 10 (0 races, 0 case suites, 2 visibility, 6 cost curves, 2 failover matrices, 0 I6 control runs)

## Runs that did not complete

[measured] These runs wrote their planned manifest and then stopped; no result was inferred from them.

| Build | Storage | Scenario | Error | Run |
|---|---|---|---|---|
| v0.15.0 | local | o1.branch_cost | UnboundLocalError: cannot access local variable 'samples' where it is not associated with a value | `20261115T153805Z-21f470bd` |
| v0.15.0 | minio | o1.branch_cost | RuntimeError: command failed (1): docker compose -p wm-m4-o1-v0-15-0-minio -f <repo>\targets\03-omnigraph\docker\compose.yml run --rm --no-deps --entrypoint /usr/local/bin/omnigraph wm-omnigraph-a cluster apply --target s3://witnessmark/wm-m4-o1-v0-15-0-minio --config /config --as witnessmark --json | `20261115T154341Z-842ecd36` |
| v0.15.0 | proxy | o1.branch_cost | RuntimeError: command failed (1): docker compose -p wm-m4-o1-v0-15-0-proxy -f <repo>\targets\03-omnigraph\docker\compose.yml run --rm --no-deps --entrypoint /usr/local/bin/omnigraph wm-omnigraph-a cluster apply --target s3://witnessmark/wm-m4-o1-v0-15-0-proxy --config /config --as witnessmark --json | `20261115T154348Z-5d605f74` |
| edge-b2dbaff | minio | o1.branch_cost | RuntimeError: command failed (1): docker compose -p wm-m4-o1-edge-b2dbaff-minio -f <repo>\targets\03-omnigraph\docker\compose.yml run --rm --no-deps --entrypoint /usr/local/bin/omnigraph wm-omnigraph-a cluster apply --target s3://witnessmark/wm-m4-o1-edge-b2dbaff-minio --config /config --as witnessmark --json | `20261115T154927Z-a633e066` |
| edge-b2dbaff | proxy | o1.branch_cost | RuntimeError: command failed (1): docker compose -p wm-m4-o1-edge-b2dbaff-proxy -f <repo>\targets\03-omnigraph\docker\compose.yml run --rm --no-deps --entrypoint /usr/local/bin/omnigraph wm-omnigraph-a cluster apply --target s3://witnessmark/wm-m4-o1-edge-b2dbaff-proxy --config /config --as witnessmark --json | `20261115T154932Z-37662ff0` |

## I6a and I6b controls

| Build | Storage | Source | I6a: branch prefix / main ledger | I6a gapless and non-empty | I6b isolation | Run |
|---|---|---|---|---|---|---|
| edge-b2dbaff | local | end of O1 curve | 0 / 20 | NO (empty prefix, not exercised) | yes | `20261115T154356Z-9ebd8e7e` |

## O1 branch-creation cost

| Build | Storage | Nodes / edges | Siblings | Create median [IQR] (ms) | Stall median (ms) | Reader p99 before / during (ms) | Merge / delete median (ms) | Object requests / bytes, one create + delete | Run |
|---|---|---|---|---|---|---|---|---|---|
| edge-b2dbaff | local | 32000 / 32000 | 0 | 4.95 [4.78–5.05] | 0 | 19.52 / 6.01 | 7.43 / 4.81 | – | `20261115T154356Z-9ebd8e7e` |
| edge-b2dbaff | local | 32000 / 32000 | 4 | 4.89 [4.88–5.61] | 0 | 23.09 / 5.36 | 7.64 / 5.28 | – | `20261115T154356Z-9ebd8e7e` |
| edge-b2dbaff | local | 32000 / 32000 | 16 | 6.02 [5.77–6.07] | 0 | 24.21 / 5.87 | 7.09 / 5.08 | – | `20261115T154356Z-9ebd8e7e` |
| edge-b2dbaff | local | 32000 / 32000 | 64 | 6.27 [6.19–6.90] | 1.42 | 19.84 / 10.55 | 7.94 / 5.15 | – | `20261115T154356Z-9ebd8e7e` |
| edge-b2dbaff | local | 128000 / 128000 | 0 | 5.21 [4.84–5.83] | 0 | 26.86 / 7.61 | 8.31 / 5.76 | – | `20261115T154356Z-9ebd8e7e` |
| edge-b2dbaff | local | 128000 / 128000 | 4 | 5.90 [5.46–6.41] | 0.44 | 23.66 / 14.95 | 8.10 / 5.26 | – | `20261115T154356Z-9ebd8e7e` |
| edge-b2dbaff | local | 128000 / 128000 | 16 | 5.63 [5.36–6.08] | 0.11 | 23.89 / 7.79 | 10.51 / 5.20 | – | `20261115T154356Z-9ebd8e7e` |
| edge-b2dbaff | local | 128000 / 128000 | 64 | 18.71 [6.29–23.88] | 2.19 | 25.70 / 15.04 | 8.38 / 5.66 | – | `20261115T154356Z-9ebd8e7e` |
| edge-b2dbaff | local | 512000 / 512000 | 0 | 5.58 [5.12–6.34] | 0 | 27.63 / 8.26 | 23.00 / 6.24 | – | `20261115T154356Z-9ebd8e7e` |
| edge-b2dbaff | local | 512000 / 512000 | 4 | 5.43 [5.26–5.49] | 0 | 24.45 / 7.77 | 30.68 / 5.86 | – | `20261115T154356Z-9ebd8e7e` |
| edge-b2dbaff | local | 512000 / 512000 | 16 | 5.85 [5.73–6.42] | 0 | 20.86 / 5.73 | 11.39 / 5.79 | – | `20261115T154356Z-9ebd8e7e` |
| edge-b2dbaff | local | 512000 / 512000 | 64 | 6.48 [6.07–6.77] | 0.83 | 23.63 / 8.60 | 11.73 / 5.89 | – | `20261115T154356Z-9ebd8e7e` |

### Copy weight

| Build | Storage | Nodes / edges | Create + claim + score + discard (ms) | Run |
|---|---|---|---|---|
| edge-b2dbaff | local | 32000 / 32000 | 57.10 | `20261115T154356Z-9ebd8e7e` |
| edge-b2dbaff | local | 128000 / 128000 | 83.76 | `20261115T154356Z-9ebd8e7e` |
| edge-b2dbaff | local | 512000 / 512000 | 201.26 | `20261115T154356Z-9ebd8e7e` |

## O4 failover acceptance matrix

| Build | Storage | Phase | Variant | Successor ready | A result | B result | Fence | Scanned via | Integrity scan | Acknowledged writes missing | Classification | Run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v0.15.0 | local | p1 | a | no | ok | – | not engaged | A (stale server) | ok | – | BOUNDARY (first-version label, superseded) | `20261115T154939Z-f2418d4a` |
| v0.15.0 | local | p1 | b | no | ok | – | not engaged | A (stale server) | ok | – | BOUNDARY (first-version label, superseded) | `20261115T154939Z-f2418d4a` |
| v0.15.0 | local | p2 | a | no | ok | – | not engaged | A (stale server) | ok | – | BOUNDARY (first-version label, superseded) | `20261115T154939Z-f2418d4a` |
| v0.15.0 | local | p2 | b | no | ok | – | not engaged | A (stale server) | ok | – | BOUNDARY (first-version label, superseded) | `20261115T154939Z-f2418d4a` |
| v0.15.0 | local | p3 | a | no | ok | – | not engaged | A (stale server) | ok | – | BOUNDARY (first-version label, superseded) | `20261115T154939Z-f2418d4a` |
| v0.15.0 | local | p3 | b | no | ok | – | not engaged | A (stale server) | ok | – | BOUNDARY (first-version label, superseded) | `20261115T154939Z-f2418d4a` |
| edge-b2dbaff | local | p1 | a | no | ok | – | not engaged | A (stale server) | ok | – | BOUNDARY (first-version label, superseded) | `20261115T155029Z-e91283b5` |
| edge-b2dbaff | local | p1 | b | no | ok | – | not engaged | A (stale server) | ok | – | BOUNDARY (first-version label, superseded) | `20261115T155029Z-e91283b5` |
| edge-b2dbaff | local | p2 | a | no | ok | – | not engaged | A (stale server) | ok | – | BOUNDARY (first-version label, superseded) | `20261115T155029Z-e91283b5` |
| edge-b2dbaff | local | p2 | b | no | ok | – | not engaged | A (stale server) | ok | – | BOUNDARY (first-version label, superseded) | `20261115T155029Z-e91283b5` |
| edge-b2dbaff | local | p3 | a | no | ok | – | not engaged | A (stale server) | ok | – | BOUNDARY (first-version label, superseded) | `20261115T155029Z-e91283b5` |
| edge-b2dbaff | local | p3 | b | no | ok | – | not engaged | A (stale server) | ok | – | BOUNDARY (first-version label, superseded) | `20261115T155029Z-e91283b5` |

BOUNDARY: a failover took place on the stable release, which predates the epoch fence; its documented deployment rule is its only protection. NOT_EXERCISED: the harness did not perform a documented step (the epoch claim, an embedding-program call, or the local ownership transfer), so the cell says nothing about the fence. No cell is a fence pass, and none is a fence failure.

## O5 cross-process read your writes

| Build | Storage | Second process | Write acknowledged | Seen | Attempts | Staleness (ms) | Run |
|---|---|---|---|---|---|---|---|
| v0.15.0 | local | wm-omnigraph-b | yes | yes | 1 | 901.30 | `20261115T155117Z-ae67af00` |
| edge-b2dbaff | local | wm-omnigraph-b | yes | yes | 1 | 928.37 | `20261115T155122Z-a5071991` |
