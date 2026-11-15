# M4: Omnigraph, fourth batch (I6 and O4 re-run): batch `m4e-20261115T183929Z`

Regenerated from `evidence/` by `python wm.py report --memory`. Do not edit by hand.

- Harness commit: `8bc5fd32b7dbc664205b8803a3f8b900e3c797f9` (dirty: false)
- Host: Windows-11-10.0.26300-SP0; 11th Gen Intel(R) Core(TM) i5-11320H @ 3.20GHz; 8 logical cores; 23.8 GB
- Docker: 29.9.3; VM limits 8 CPUs, 11.6 GB
- Runs: 10 (0 races, 0 case suites, 0 visibility, 0 cost curves, 4 failover matrices, 6 I6 control runs)

## I6a and I6b controls

| Build | Storage | Source | I6a: branch prefix / main ledger | I6a gapless and non-empty | I6b isolation | Run |
|---|---|---|---|---|---|---|
| v0.15.0 | local | controls only | 5 / 20 | yes | yes | `20261115T183931Z-fa543284` |
| v0.15.0 | minio | controls only | 5 / 20 | yes | yes | `20261115T183939Z-2b18faf7` |
| v0.15.0 | proxy | controls only | 5 / 20 | yes | yes | `20261115T183955Z-401500b4` |
| edge-b2dbaff | local | controls only | 5 / 20 | yes | yes | `20261115T184035Z-505c2756` |
| edge-b2dbaff | minio | controls only | 5 / 20 | yes | yes | `20261115T184042Z-d51c234e` |
| edge-b2dbaff | proxy | controls only | 5 / 20 | yes | yes | `20261115T184058Z-df6399b2` |

## O4 failover acceptance matrix

| Build | Storage | Phase | Variant | Successor ready | A result | B result | Fence | Scanned via | Integrity scan | Acknowledged writes missing | Classification | Run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v0.15.0 | local | p1 | a | no | ok | – | not engaged | wm-omnigraph-a | ok | none | NOT_EXERCISED | `20261115T184136Z-24a2c040` |
| v0.15.0 | local | p1 | b | no | ok | – | not engaged | wm-omnigraph-a | ok | none | NOT_EXERCISED | `20261115T184136Z-24a2c040` |
| v0.15.0 | local | p2 | a | no | ok | – | not engaged | wm-omnigraph-a | ok | none | NOT_EXERCISED | `20261115T184136Z-24a2c040` |
| v0.15.0 | local | p2 | b | no | ok | – | not engaged | wm-omnigraph-a | ok | none | NOT_EXERCISED | `20261115T184136Z-24a2c040` |
| v0.15.0 | local | p3 | a | no | ok | – | not engaged | wm-omnigraph-a | ok | none | NOT_EXERCISED | `20261115T184136Z-24a2c040` |
| v0.15.0 | local | p3 | b | no | ok | – | not engaged | wm-omnigraph-a | ok | none | NOT_EXERCISED | `20261115T184136Z-24a2c040` |
| v0.15.0 | minio | p1 | a | yes | service_unavailable | – | not engaged | wm-omnigraph-b | ok | none | BOUNDARY | `20261115T184233Z-3a4a4f31` |
| v0.15.0 | minio | p1 | b | yes | connection | ok | not engaged | wm-omnigraph-b | ok | none | BOUNDARY | `20261115T184233Z-3a4a4f31` |
| v0.15.0 | minio | p2 | a | yes | internal | – | not engaged | wm-omnigraph-b | ok | none | BOUNDARY | `20261115T184233Z-3a4a4f31` |
| v0.15.0 | minio | p2 | b | yes | internal | ok | not engaged | wm-omnigraph-b | ok | none | BOUNDARY | `20261115T184233Z-3a4a4f31` |
| v0.15.0 | minio | p3 | a | yes | internal | – | not engaged | wm-omnigraph-b | ok | none | BOUNDARY | `20261115T184233Z-3a4a4f31` |
| v0.15.0 | minio | p3 | b | yes | internal | ok | not engaged | wm-omnigraph-b | ok | none | BOUNDARY | `20261115T184233Z-3a4a4f31` |
| edge-b2dbaff | local | p1 | a | no | ok | – | not engaged | wm-omnigraph-a | ok | none | NOT_EXERCISED | `20261115T184426Z-ba1673ab` |
| edge-b2dbaff | local | p1 | b | no | ok | – | not engaged | wm-omnigraph-a | ok | none | NOT_EXERCISED | `20261115T184426Z-ba1673ab` |
| edge-b2dbaff | local | p2 | a | no | ok | – | not engaged | wm-omnigraph-a | ok | none | NOT_EXERCISED | `20261115T184426Z-ba1673ab` |
| edge-b2dbaff | local | p2 | b | no | ok | – | not engaged | wm-omnigraph-a | ok | none | NOT_EXERCISED | `20261115T184426Z-ba1673ab` |
| edge-b2dbaff | local | p3 | a | no | ok | – | not engaged | wm-omnigraph-a | ok | none | NOT_EXERCISED | `20261115T184426Z-ba1673ab` |
| edge-b2dbaff | local | p3 | b | no | ok | – | not engaged | wm-omnigraph-a | ok | none | NOT_EXERCISED | `20261115T184426Z-ba1673ab` |
| edge-b2dbaff | minio | p1 | a | yes | connection | – | not engaged | wm-omnigraph-b | ok | none | NOT_EXERCISED | `20261115T184523Z-2ae7e967` |
| edge-b2dbaff | minio | p1 | b | yes | connection | ok | not engaged | wm-omnigraph-b | ok | none | NOT_EXERCISED | `20261115T184523Z-2ae7e967` |
| edge-b2dbaff | minio | p2 | a | yes | internal | – | not engaged | wm-omnigraph-b | ok | none | NOT_EXERCISED | `20261115T184523Z-2ae7e967` |
| edge-b2dbaff | minio | p2 | b | yes | internal | ok | not engaged | wm-omnigraph-b | ok | none | NOT_EXERCISED | `20261115T184523Z-2ae7e967` |
| edge-b2dbaff | minio | p3 | a | yes | internal | – | not engaged | wm-omnigraph-b | ok | none | NOT_EXERCISED | `20261115T184523Z-2ae7e967` |
| edge-b2dbaff | minio | p3 | b | yes | internal | ok | not engaged | wm-omnigraph-b | ok | none | NOT_EXERCISED | `20261115T184523Z-2ae7e967` |

BOUNDARY: a failover took place on the stable release, which predates the epoch fence; its documented deployment rule is its only protection. NOT_EXERCISED: the harness did not perform a documented step (the epoch claim, an embedding-program call, or the local ownership transfer), so the cell says nothing about the fence. No cell is a fence pass, and none is a fence failure.
