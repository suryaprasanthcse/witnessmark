# M2: Graphiti: batch `m2-20261113T174128Z`

Regenerated from `evidence/` by `python wm.py report --memory`. Do not edit by hand.

- Harness commit: `526e98fbe59f602b33d6e84588e91159eafbd7af` (dirty: false)
- Host: Windows-11-10.0.26300-SP0; 11th Gen Intel(R) Core(TM) i5-11320H @ 3.20GHz; 8 logical cores; 23.8 GB
- Docker: 29.9.3; VM limits 8 CPUs, 11.6 GB
- Runs: 30 (11 races, 17 case suites, 2 visibility)

## Races

| Build | Backend | Scenario | Sequential control | Overlap control | Verdicts | Run |
|---|---|---|---|---|---|---|
| v0.31.2 | falkordb | g1.same_group.asyncio | met | 20 of 20 valid trials had two or more in flight | I1B BOUNDARY 20/20 (max 20 records per key); I2 PASS 0/20 | `20261113T174130Z-100f7bf5` |
| v0.31.2 | falkordb | g1.same_group.queue | met | 20 of 20 valid trials had two or more in flight | I1B PASS 0/20; I2 PASS 0/20 | `20261113T174153Z-7ca0b640` |
| v0.31.2 | falkordb | g1.same_group.process | met | 20 of 20 valid trials had two or more in flight | I1B BOUNDARY 20/20 (max 16 records per key); I2 PASS 0/20 | `20261113T174316Z-628f05db` |
| v0.31.2 | falkordb | g1.cross_group.asyncio | met | 20 of 20 valid trials had two or more in flight | I1B PASS 0/20; I2 PASS 0/20 | `20261113T174516Z-9870126f` |
| v0.31.2 | falkordb | g2.contradictions.asyncio | met | 20 of 20 valid trials had two or more in flight | I7A BOUNDARY 20/20 (max 10 current versions) | `20261113T174534Z-dbb28e9f` |
| v0.31.2 | neo4j | g1.same_group.asyncio | met | 20 of 20 valid trials had two or more in flight | I1B BOUNDARY 20/20 (max 20 records per key); I2 PASS 0/20 | `20261113T174617Z-ac4909ea` |
| v0.31.2 | neo4j | g1.same_group.queue | met | 20 of 20 valid trials had two or more in flight | I1B PASS 0/20; I2 PASS 0/20 | `20261113T174650Z-6df7654b` |
| v0.31.2 | neo4j | g1.same_group.process | met | 20 of 20 valid trials had two or more in flight | I1B BOUNDARY 20/20 (max 8 records per key); I2 PASS 0/20 | `20261113T174754Z-2d06b857` |
| v0.31.2 | neo4j | g1.cross_group.asyncio | met | 20 of 20 valid trials had two or more in flight | I1B PASS 0/20; I2 PASS 0/20 | `20261113T174942Z-64833bf9` |
| v0.31.2 | neo4j | g2.contradictions.asyncio | met | 20 of 20 valid trials had two or more in flight | I7A BOUNDARY 20/20 (max 10 current versions) | `20261113T175013Z-78adabfc` |
| v0.31.2 | falkordb (default pool) | g1.same_group.asyncio | met | 0 of 0 valid trials had two or more in flight | I1B INVALID 0/0; I2 INVALID 0/0 | `20261113T175104Z-2e069ccc` |

Sequential controls met: 11 of 11 race runs.

### Release spread by mode (valid race trials)

| Mode | Trials | p50 | p95 | p99 | max |
|---|---|---|---|---|---|
| asyncio | 120 | 6.08 | 21.59 | 61.27 | 66.09 |
| queue | 40 | 0.86 | 1.40 | 1.65 | 1.65 |
| process | 40 | 0.12 | 0.20 | 0.26 | 0.26 |

## Known-answer suites

A cell lists the checks that failed for that case; `ok` means none did.

| Build | Backend | Suite | R1 | R2 | R3 | R4 | R5 | R6 | suite | default | limit1 | Run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v0.31.2 | falkordb | g3.temporal.add_episode | I7.code | I7.issue, I7.standard | I7.standard | I7.issue, I7.standard | I2 | ok | MR1 | – | – | `20261113T174543Z-20792bcd` |
| main-ebef986a | falkordb | g3.temporal.add_episode | I7.code | I7.issue, I7.standard | I7.standard | I7.issue, I7.standard | I2 | ok | MR1 | – | – | `20261113T174547Z-d27e13c1` |
| v0.31.2 | falkordb | g3.temporal.add_episode_bulk | I7.code | I7.issue, I7.standard | I7.standard | I7.issue, I7.standard | I2 | ok | MR1 | – | – | `20261113T174552Z-811a9b68` |
| main-ebef986a | falkordb | g3.temporal.add_episode_bulk | I7.code | I7.issue, I7.standard | I7.standard | I7.issue, I7.standard | I2 | ok | MR1 | – | – | `20261113T174556Z-dd694e61` |
| v0.31.2 | falkordb | g3.temporal.add_triplet | I2, I7.code | I2, I7.issue, I7.standard | I2, I7.standard | I2, I7.issue, I7.standard | I2 | I2 | MR1 | – | – | `20261113T174600Z-2f30b073` |
| main-ebef986a | falkordb | g3.temporal.add_triplet | I2, I7.code | I2, I7.issue, I7.standard | I2, I7.standard | I2, I7.issue, I7.standard | I2 | I2 | MR1 | – | – | `20261113T174604Z-56aad93f` |
| v0.31.2 | falkordb | g5.shared_search_limit | – | – | – | – | – | – | – | ok | I7A | `20261113T174608Z-dfdbbb5d` |
| v0.31.2 | neo4j | g3.temporal.add_episode | I7.code | I7.issue, I7.standard | I7.standard | I7.issue, I7.standard | I2 | ok | MR1 | – | – | `20261113T175025Z-bd31b4d3` |
| main-ebef986a | neo4j | g3.temporal.add_episode | I7.code | I7.issue, I7.standard | I7.standard | I7.issue, I7.standard | I2 | ok | MR1 | – | – | `20261113T175030Z-0fd4a167` |
| v0.31.2 | neo4j | g3.temporal.add_episode_bulk | I7.code | I7.issue, I7.standard | I7.standard | I7.issue, I7.standard | I2 | ok | MR1 | – | – | `20261113T175034Z-16b9e07a` |
| main-ebef986a | neo4j | g3.temporal.add_episode_bulk | I7.code | I7.issue, I7.standard | I7.standard | I7.issue, I7.standard | I2 | ok | MR1 | – | – | `20261113T175040Z-34530b5a` |
| v0.31.2 | neo4j | g3.temporal.add_triplet | I7.code | I7.issue, I7.standard | I7.standard | I7.issue, I7.standard | I2 | ok | MR1 | – | – | `20261113T175045Z-a2ccbf95` |
| main-ebef986a | neo4j | g3.temporal.add_triplet | I7.code | I7.issue, I7.standard | I7.standard | I7.issue, I7.standard | I2 | ok | MR1 | – | – | `20261113T175049Z-37349acd` |
| v0.31.2 | neo4j | g5.shared_search_limit | – | – | – | – | – | – | – | ok | I7A | `20261113T175054Z-3bac68be` |
| pr1867-a30934e1 | neo4j | g3.temporal.add_episode | I7.issue, I7.standard | I7.issue, I7.standard | I7.standard | I7.issue, I7.standard | ok | ok | ok | – | – | `20261113T175125Z-132555de` |
| pr1867-a30934e1 | neo4j | g3.temporal.add_episode_bulk | I7.issue, I7.standard | I7.issue, I7.standard | I7.standard | I7.issue, I7.standard | ok | ok | ok | – | – | `20261113T175130Z-d515acfd` |
| pr1867-a30934e1 | neo4j | g3.temporal.add_triplet | I7.issue, I7.standard | I7.issue, I7.standard | I7.standard | I7.issue, I7.standard | ok | ok | ok | – | – | `20261113T175135Z-95f29d0b` |

## Read your writes

| Build | Backend | Writes | Seen on the first search, same instance | Seen on the first search, second instance | Longest lag (ms) | Run |
|---|---|---|---|---|---|---|
| v0.31.2 | falkordb | 10 | 10 of 10 | 10 of 10 | 0 | `20261113T174612Z-5b18974b` |
| v0.31.2 | neo4j | 10 | 10 of 10 | 10 of 10 | 0 | `20261113T175059Z-738c7f37` |
