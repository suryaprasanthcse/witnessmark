# M5: Graphiti: batch `m5g-20261116T051149Z`

Regenerated from `evidence/` by `python wm.py report --memory`. Do not edit by hand.

- Harness commit: `8b9785af52e2b5f3466700831dde9518c2d99c33` (dirty: false)
- Host: Windows-11-10.0.26300-SP0; 11th Gen Intel(R) Core(TM) i5-11320H @ 3.20GHz; 8 logical cores; 23.8 GB
- Docker: 29.9.3; VM limits 8 CPUs, 11.6 GB
- Runs: 22 (5 races, 0 case suites, 0 visibility)
- Runs added in M5 Phase C: 11 G6a/G6b startup runs, 3 G6c races, 6 G7 persistence runs, 2 G8 races
- Harness commits in this batch: `8b9785a`

## Races

| Build | Backend | Scenario | Sequential control | Overlap control | Verdicts | Run |
|---|---|---|---|---|---|---|
| v0.31.2 | falkordb | g6c.many_groups.asyncio | met | 20 of 20 valid trials had two or more in flight | I2 PASS 0/20; I1B PASS 0/20; I4 PASS 0/20 | `20261116T054448Z-74713339` |
| main-ebef986a | falkordb | g6c.many_groups.asyncio | met | 20 of 20 valid trials had two or more in flight | I2 PASS 0/20; I1B PASS 0/20; I4 PASS 0/20 | `20261116T054508Z-0928df36` |
| pr2119-b2b727e0 | falkordb | g6c.many_groups.asyncio | met | 20 of 20 valid trials had two or more in flight | I2 PASS 0/20; I1B PASS 0/20; I4 PASS 0/20 | `20261116T054530Z-07a4e09a` |
| v0.31.2 | falkordb | g8.remove_vs_add.asyncio | met | 20 of 20 valid trials had two or more in flight | I5 PASS 0/20; I2 PASS 0/20; I1B PASS 0/20 | `20261116T071319Z-334d816c` |
| v0.31.2 | neo4j | g8.remove_vs_add.asyncio | met | 20 of 20 valid trials had two or more in flight | I5 PASS 0/20; I2 OBSERVED 20/20 (max 2 items lost to the delete); I1B PASS 0/20 | `20261116T071325Z-4bc1eaa9` |

Sequential controls met: 5 of 5 race runs.

### Release spread by mode (valid race trials)

| Mode | Trials | p50 | p95 | p99 | max |
|---|---|---|---|---|---|
| asyncio | 100 | 0.85 | 2.83 | 3.49 | 5.87 |

## G6 index readiness at startup

Each valid trial runs the ten-query suite at once and again after every expected index is ready; each query's answer is compared, as a multiset, with the control's.

| Build | Backend | Scenario | Sequential control | Valid trials | First query met an index that was not ready | At once: identical / different / error | After ready: identical / different / error | Never-retrieved task exceptions | Error log records | Run |
|---|---|---|---|---|---|---|---|---|---|---|
| v0.31.2 | falkordb | g6a.fresh.startup | met | 20 of 20 | 20 of 20 | 200 / 0 / 0 | 200 / 0 / 0 | 0 | 0 | `20261116T051153Z-2e987ec0` |
| main-ebef986a | falkordb | g6a.fresh.startup | met | 20 of 20 | 20 of 20 | 200 / 0 / 0 | 200 / 0 / 0 | 0 | 0 | `20261116T051801Z-c9fd6666` |
| pr2119-b2b727e0 | falkordb | g6a.fresh.startup | met | 20 of 20 | 20 of 20 | 200 / 0 / 0 | 200 / 0 / 0 | 0 | 0 | `20261116T052409Z-5885a291` |
| v0.31.2 | falkordb | g6b.populated.startup | met | 10 of 10 | 0 of 10 | 100 / 0 / 0 | 100 / 0 / 0 | 0 | 0 | `20261116T053018Z-2290cc18` |
| main-ebef986a | falkordb | g6b.populated.startup | met | 10 of 10 | 0 of 10 | 100 / 0 / 0 | 100 / 0 / 0 | 0 | 0 | `20261116T053508Z-67de8ce9` |
| pr2119-b2b727e0 | falkordb | g6b.populated.startup | met | 10 of 10 | 0 of 10 | 100 / 0 / 0 | 100 / 0 / 0 | 0 | 0 | `20261116T053958Z-f4b4332f` |
| v0.31.2 | neo4j | g6a.fresh.startup | met | 20 of 20 | 20 of 20 | 161 / 0 / 39 | 200 / 0 / 0 | 0 | 39 | `20261116T054555Z-85bc1662` |
| pr2119-b2b727e0 | neo4j | g6a.fresh.startup | met | 20 of 20 | 20 of 20 | 174 / 0 / 26 | 200 / 0 / 0 | 0 | 26 | `20261116T064351Z-20ab7a28` |
| v0.31.2 | neo4j | g6b.populated.startup | met | 10 of 10 | 0 of 10 | 100 / 0 / 0 | 100 / 0 / 0 | 0 | 0 | `20261116T064831Z-bea83c1a` |
| main-ebef986a | neo4j | g6b.populated.startup | met | 10 of 10 | 0 of 10 | 100 / 0 / 0 | 100 / 0 / 0 | 0 | 0 | `20261116T065525Z-d552844d` |
| pr2119-b2b727e0 | neo4j | g6b.populated.startup | met | 10 of 10 | 0 of 10 | 100 / 0 / 0 | 100 / 0 / 0 | 0 | 0 | `20261116T070159Z-af2cbe2f` |

### Index state after creation returned (KD-F4)

Bounds come from discrete samples of the index state: at least until the last sample that still saw an index not ready was taken, at most until the first sample that saw every index ready returned.

| Build | Backend | Scenario | Observations | UNDER CONSTRUCTION seen | Not ready after creation returned, ms (largest lower bound / largest upper bound) | Why not ready | Probe rows while UNDER CONSTRUCTION (min / max; control) | Run |
|---|---|---|---|---|---|---|---|---|
| v0.31.2 | falkordb | g6a.fresh.startup | 20 | 20 of 20 | 0 / 166.89 | – | 0 / 2000; 2000 | `20261116T051153Z-2e987ec0` |
| main-ebef986a | falkordb | g6a.fresh.startup | 20 | 20 of 20 | 0.22 / 167.78 | under construction | 0 / 2000; 2000 | `20261116T051801Z-c9fd6666` |
| pr2119-b2b727e0 | falkordb | g6a.fresh.startup | 20 | 20 of 20 | 17.18 / 36.66 | under construction | 0 / 2000; 2000 | `20261116T052409Z-5885a291` |
| v0.31.2 | falkordb | g6b.populated.startup | 10 | 0 of 10 | 0 / 0 | – | – | `20261116T053018Z-2290cc18` |
| main-ebef986a | falkordb | g6b.populated.startup | 10 | 0 of 10 | 0 / 0 | – | – | `20261116T053508Z-67de8ce9` |
| pr2119-b2b727e0 | falkordb | g6b.populated.startup | 10 | 0 of 10 | 0 / 0 | – | – | `20261116T053958Z-f4b4332f` |
| v0.31.2 | neo4j | g6a.fresh.startup | 20 | 20 of 20 | 245.77 / 902.26 | under construction | 2000 / 2000; 2000 | `20261116T054555Z-85bc1662` |
| pr2119-b2b727e0 | neo4j | g6a.fresh.startup | 20 | 20 of 20 | 95.18 / 1405.61 | under construction | 2000 / 2000; 2000 | `20261116T064351Z-20ab7a28` |
| v0.31.2 | neo4j | g6b.populated.startup | 10 | 0 of 10 | 0 / 0 | – | – | `20261116T064831Z-bea83c1a` |
| main-ebef986a | neo4j | g6b.populated.startup | 10 | 0 of 10 | 0 / 0 | – | – | `20261116T065525Z-d552844d` |
| pr2119-b2b727e0 | neo4j | g6b.populated.startup | 10 | 0 of 10 | 0 / 0 | – | – | `20261116T070159Z-af2cbe2f` |
| v0.31.2 | falkordb | g6c.many_groups.asyncio | 160 | 0 of 160 | 0 / 113.49 | – | – | `20261116T054448Z-74713339` |
| main-ebef986a | falkordb | g6c.many_groups.asyncio | 160 | 0 of 160 | 0 / 120.03 | – | – | `20261116T054508Z-0928df36` |
| pr2119-b2b727e0 | falkordb | g6c.many_groups.asyncio | 160 | 1 of 160 | 0 / 283.69 | – | – | `20261116T054530Z-07a4e09a` |

## G7 persistence across container actions

| Variant | Action | Sequential control | Valid trials | Trials with loss | Items lost per trial (episodes / entities / facts, largest) | appendonly / appendfsync / save | Graph module arguments | Volume at | Verdict | Run |
|---|---|---|---|---|---|---|---|---|---|---|
| root | compose_restart | met | 10 of 10 | 0 of 10 | 0 / 0 / 0 | no / everysec / 3600 1 300 100 60 10000 | none | /data | I2 PASS 0/10 | `20261116T070849Z-c09d11b2` |
| root | down_up | met | 10 of 10 | 0 of 10 | 0 / 0 / 0 | no / everysec / 3600 1 300 100 60 10000 | none | /data | I2 PASS 0/10 | `20261116T070935Z-cdf2ec96` |
| root | kill_start | met | 10 of 10 | 10 of 10 | 10 / 2 / 10 | no / everysec / 3600 1 300 100 60 10000 | none | /data | I2 OBSERVED 10/10 (max 22 items lost) | `20261116T071025Z-e638bddf` |
| mcp | compose_restart | met | 10 of 10 | 0 of 10 | 0 / 0 / 0 | no / everysec / 3600 1 300 100 60 10000 | MAX_QUEUED_QUERIES 25 TIMEOUT 1000 RESULTSET_SIZE 10000 | /var/lib/falkordb/data | I2 PASS 0/10 | `20261116T071106Z-079f03e1` |
| mcp | down_up | met | 10 of 10 | 0 of 10 | 0 / 0 / 0 | no / everysec / 3600 1 300 100 60 10000 | MAX_QUEUED_QUERIES 25 TIMEOUT 1000 RESULTSET_SIZE 10000 | /var/lib/falkordb/data | I2 PASS 0/10 | `20261116T071148Z-932b738f` |
| mcp | kill_start | met | 10 of 10 | 10 of 10 | 10 / 2 / 10 | no / everysec / 3600 1 300 100 60 10000 | MAX_QUEUED_QUERIES 25 TIMEOUT 1000 RESULTSET_SIZE 10000 | /var/lib/falkordb/data | I2 OBSERVED 10/10 (max 22 items lost) | `20261116T071238Z-cfee79ff` |

## Checks outside the invariants

| Backend | Scenario | Check | Trials where it did not hold | Details (first trials) | Run |
|---|---|---|---|---|---|
| falkordb | g6a.fresh.startup | ERR | 0 of 20 | – | `20261116T051153Z-2e987ec0` |
| falkordb | g6a.fresh.startup | TASK | 0 of 20 | – | `20261116T051153Z-2e987ec0` |
| falkordb | g6a.fresh.startup | ERR | 0 of 20 | – | `20261116T051801Z-c9fd6666` |
| falkordb | g6a.fresh.startup | TASK | 0 of 20 | – | `20261116T051801Z-c9fd6666` |
| falkordb | g6a.fresh.startup | ERR | 0 of 20 | – | `20261116T052409Z-5885a291` |
| falkordb | g6a.fresh.startup | TASK | 0 of 20 | – | `20261116T052409Z-5885a291` |
| falkordb | g6b.populated.startup | ERR | 0 of 10 | – | `20261116T053018Z-2290cc18` |
| falkordb | g6b.populated.startup | TASK | 0 of 10 | – | `20261116T053018Z-2290cc18` |
| falkordb | g6b.populated.startup | ERR | 0 of 10 | – | `20261116T053508Z-67de8ce9` |
| falkordb | g6b.populated.startup | TASK | 0 of 10 | – | `20261116T053508Z-67de8ce9` |
| falkordb | g6b.populated.startup | ERR | 0 of 10 | – | `20261116T053958Z-f4b4332f` |
| falkordb | g6b.populated.startup | TASK | 0 of 10 | – | `20261116T053958Z-f4b4332f` |
| falkordb | g6c.many_groups.asyncio | ERR | 0 of 20 | – | `20261116T054448Z-74713339` |
| falkordb | g6c.many_groups.asyncio | TASK | 0 of 20 | – | `20261116T054448Z-74713339` |
| falkordb | g6c.many_groups.asyncio | ERR | 0 of 20 | – | `20261116T054508Z-0928df36` |
| falkordb | g6c.many_groups.asyncio | TASK | 0 of 20 | – | `20261116T054508Z-0928df36` |
| falkordb | g6c.many_groups.asyncio | ERR | 0 of 20 | – | `20261116T054530Z-07a4e09a` |
| falkordb | g6c.many_groups.asyncio | TASK | 0 of 20 | – | `20261116T054530Z-07a4e09a` |
| neo4j | g6a.fresh.startup | ERR | 11 of 20 | 1 log record(s) at ERROR, 0 at WARNING; 2 log record(s) at ERROR, 0 at WARNING; 4 log record(s) at ERROR, 0 at WARNING | `20261116T054555Z-85bc1662` |
| neo4j | g6a.fresh.startup | TASK | 0 of 20 | – | `20261116T054555Z-85bc1662` |
| neo4j | g6a.fresh.startup | ERR | 8 of 20 | 1 log record(s) at ERROR, 0 at WARNING; 2 log record(s) at ERROR, 0 at WARNING; 4 log record(s) at ERROR, 0 at WARNING | `20261116T064351Z-20ab7a28` |
| neo4j | g6a.fresh.startup | TASK | 0 of 20 | – | `20261116T064351Z-20ab7a28` |
| neo4j | g6b.populated.startup | ERR | 0 of 10 | – | `20261116T064831Z-bea83c1a` |
| neo4j | g6b.populated.startup | TASK | 0 of 10 | – | `20261116T064831Z-bea83c1a` |
| neo4j | g6b.populated.startup | ERR | 0 of 10 | – | `20261116T065525Z-d552844d` |
| neo4j | g6b.populated.startup | TASK | 0 of 10 | – | `20261116T065525Z-d552844d` |
| neo4j | g6b.populated.startup | ERR | 0 of 10 | – | `20261116T070159Z-af2cbe2f` |
| neo4j | g6b.populated.startup | TASK | 0 of 10 | – | `20261116T070159Z-af2cbe2f` |
