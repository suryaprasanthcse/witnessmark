# Reproduce run 20261116T092229Z-98725745

Start the pinned baselines, use the target's pinned environment, then run:

```bash
.state/venvs/graphiti-v0.31.2/Scripts/python.exe targets/01-zep-graphiti/wm_graphiti.py persistence --variant mcp --action kill_start --appendonly --trials 10 --seed 20261141 --batch m5i-20261116T092138Z --evidence evidence --anchor 2026-11-16T09:22:28Z
```

- Harness commit: `03957995f2ef5b528bd02b95b8ccbcccf279bad1` (dirty: false)
- Target: `{"name": "graphiti", "package_version": "0.31.2", "ref": "v0.31.2", "repo": "getzep/graphiti"}`
