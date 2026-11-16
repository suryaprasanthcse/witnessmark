# Reproduce run 20261116T053508Z-67de8ce9

Start the pinned baselines, use the target's pinned environment, then run:

```bash
.state/venvs/graphiti-main-ebef986a/Scripts/python.exe targets/01-zep-graphiti/wm_graphiti.py startup --scenario g6b.populated --backend falkordb --trials 10 --build main-ebef986a --commit ebef986a0b2360211b65751c111cacb4a7d790eb --seed 20261121 --batch m5g-20261116T051149Z --evidence evidence --anchor 2026-11-16T05:35:05Z
```

- Harness commit: `8b9785af52e2b5f3466700831dde9518c2d99c33` (dirty: false)
- Target: `{"commit": "ebef986a0b2360211b65751c111cacb4a7d790eb", "name": "graphiti", "package_version": "0.31.2", "ref": "main-ebef986a", "repo": "getzep/graphiti"}`
