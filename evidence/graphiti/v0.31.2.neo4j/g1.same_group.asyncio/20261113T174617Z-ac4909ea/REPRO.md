# Reproduce run 20261113T174617Z-ac4909ea

Start the pinned baselines, use the target's pinned environment, then run:

```bash
.state/venvs/graphiti-v0.31.2/Scripts/python.exe targets/01-zep-graphiti/wm_graphiti.py race --backend neo4j --scenario g1.same_group --mode asyncio --trials 20 --batch m2-20261113T174128Z --anchor 2026-11-13T17:46:15Z
```

- Harness commit: `526e98fbe59f602b33d6e84588e91159eafbd7af` (dirty: false)
- Target: `{"name": "graphiti", "package_version": "0.31.2", "ref": "v0.31.2", "repo": "getzep/graphiti"}`
