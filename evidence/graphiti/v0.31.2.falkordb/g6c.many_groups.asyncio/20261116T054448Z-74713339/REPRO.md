# Reproduce run 20261116T054448Z-74713339

Start the pinned baselines, use the target's pinned environment, then run:

```bash
.state/venvs/graphiti-v0.31.2/Scripts/python.exe targets/01-zep-graphiti/wm_graphiti.py race --scenario g6c.many_groups --backend falkordb --trials 20 --seed 20261123 --batch m5g-20261116T051149Z --evidence evidence --anchor 2026-11-16T05:44:46Z
```

- Harness commit: `8b9785af52e2b5f3466700831dde9518c2d99c33` (dirty: false)
- Target: `{"name": "graphiti", "package_version": "0.31.2", "ref": "v0.31.2", "repo": "getzep/graphiti"}`
