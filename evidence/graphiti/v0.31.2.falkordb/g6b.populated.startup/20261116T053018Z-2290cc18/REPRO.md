# Reproduce run 20261116T053018Z-2290cc18

Start the pinned baselines, use the target's pinned environment, then run:

```bash
.state/venvs/graphiti-v0.31.2/Scripts/python.exe targets/01-zep-graphiti/wm_graphiti.py startup --scenario g6b.populated --backend falkordb --trials 10 --seed 20261120 --batch m5g-20261116T051149Z --evidence evidence --anchor 2026-11-16T05:30:16Z
```

- Harness commit: `8b9785af52e2b5f3466700831dde9518c2d99c33` (dirty: false)
- Target: `{"name": "graphiti", "package_version": "0.31.2", "ref": "v0.31.2", "repo": "getzep/graphiti"}`
