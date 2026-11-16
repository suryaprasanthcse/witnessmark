# Reproduce run 20261116T053958Z-f4b4332f

Start the pinned baselines, use the target's pinned environment, then run:

```bash
.state/venvs/graphiti-pr2119-b2b727e0/Scripts/python.exe targets/01-zep-graphiti/wm_graphiti.py startup --scenario g6b.populated --backend falkordb --trials 10 --build pr2119-b2b727e0 --commit b2b727e05467346b6516e2c68e193f8142ef208b --seed 20261122 --batch m5g-20261116T051149Z --evidence evidence --anchor 2026-11-16T05:39:55Z
```

- Harness commit: `8b9785af52e2b5f3466700831dde9518c2d99c33` (dirty: false)
- Target: `{"commit": "b2b727e05467346b6516e2c68e193f8142ef208b", "name": "graphiti", "package_version": "0.31.2", "ref": "pr2119-b2b727e0", "repo": "getzep/graphiti"}`
