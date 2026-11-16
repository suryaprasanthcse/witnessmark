# Reproduce run 20261116T054508Z-0928df36

Start the pinned baselines, use the target's pinned environment, then run:

```bash
.state/venvs/graphiti-main-ebef986a/Scripts/python.exe targets/01-zep-graphiti/wm_graphiti.py race --scenario g6c.many_groups --backend falkordb --trials 20 --build main-ebef986a --commit ebef986a0b2360211b65751c111cacb4a7d790eb --seed 20261124 --batch m5g-20261116T051149Z --evidence evidence --anchor 2026-11-16T05:45:05Z
```

- Harness commit: `8b9785af52e2b5f3466700831dde9518c2d99c33` (dirty: false)
- Target: `{"commit": "ebef986a0b2360211b65751c111cacb4a7d790eb", "name": "graphiti", "package_version": "0.31.2", "ref": "main-ebef986a", "repo": "getzep/graphiti"}`
