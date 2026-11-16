# Reproduce run 20261116T071325Z-4bc1eaa9

Start the pinned baselines, use the target's pinned environment, then run:

```bash
.state/venvs/graphiti-v0.31.2/Scripts/python.exe targets/01-zep-graphiti/wm_graphiti.py race --scenario g8.remove_vs_add --backend neo4j --trials 20 --seed 20261139 --batch m5g-20261116T051149Z --evidence evidence --anchor 2026-11-16T07:13:24Z
```

- Harness commit: `8b9785af52e2b5f3466700831dde9518c2d99c33` (dirty: false)
- Target: `{"name": "graphiti", "package_version": "0.31.2", "ref": "v0.31.2", "repo": "getzep/graphiti"}`
