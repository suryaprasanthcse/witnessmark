# M5: Graphiti, G7 appendonly control: batch `m5i-20261116T092138Z`

Regenerated from `evidence/` by `python wm.py report --memory`. Do not edit by hand.

- Harness commit: `03957995f2ef5b528bd02b95b8ccbcccf279bad1` (dirty: false)
- Host: Windows-11-10.0.26300-SP0; 11th Gen Intel(R) Core(TM) i5-11320H @ 3.20GHz; 8 logical cores; 23.8 GB
- Docker: 29.9.3; VM limits 8 CPUs, 11.6 GB
- Runs: 2 (0 races, 0 case suites, 0 visibility)
- Runs added in M5 Phase C: 0 G6a/G6b startup runs, 0 G6c races, 2 G7 persistence runs, 0 G8 races
- Harness commits in this batch: `0395799`

## G7 persistence across container actions

| Variant | Action | Sequential control | Valid trials | Trials with loss | Items lost per trial (episodes / entities / facts, largest) | appendonly / appendfsync / save | Graph module arguments | Volume at | Verdict | Run |
|---|---|---|---|---|---|---|---|---|---|---|
| root | kill_start | met | 10 of 10 | 0 of 10 | 0 / 0 / 0 | yes / everysec / 3600 1 300 100 60 10000 | none | /data | I2 PASS 0/10 | `20261116T092142Z-a5ceedc5` |
| mcp | kill_start | met | 10 of 10 | 0 of 10 | 0 / 0 / 0 | yes / everysec / 3600 1 300 100 60 10000 | MAX_QUEUED_QUERIES 25 TIMEOUT 1000 RESULTSET_SIZE 10000 | /var/lib/falkordb/data | I2 PASS 0/10 | `20261116T092229Z-98725745` |
