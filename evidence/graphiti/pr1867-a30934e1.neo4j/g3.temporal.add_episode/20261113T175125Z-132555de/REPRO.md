# Reproduce run 20261113T175125Z-132555de

Start the pinned baselines, use the target's pinned environment, then run:

```bash
.state/venvs/graphiti-pr1867-a30934e1/Scripts/python.exe targets/01-zep-graphiti/wm_graphiti.py cases --backend neo4j --suite g3 --entry add_episode --build pr1867-a30934e1 --commit a30934e18b9582fbea3aca742269fc2174b67f07 --batch m2-20261113T174128Z --anchor 2026-11-13T17:51:23Z
```

- Harness commit: `526e98fbe59f602b33d6e84588e91159eafbd7af` (dirty: false)
- Target: `{"commit": "a30934e18b9582fbea3aca742269fc2174b67f07", "name": "graphiti", "package_version": "0.30.2", "ref": "pr1867-a30934e1", "repo": "getzep/graphiti"}`
