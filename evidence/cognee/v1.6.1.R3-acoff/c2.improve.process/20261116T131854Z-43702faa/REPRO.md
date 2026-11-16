# Reproduce run 20261116T131854Z-43702faa

Start the pinned baselines, use the target's pinned environment, then run:

```bash
.state/venvs/cognee-v1.6.1-falkor/Scripts/python.exe targets/02-cognee/wm_cognee.py race --row R3 --build v1.6.1 --scenario c2.improve --mode process --trials 20 --access-control off --seed 20261119 --batch m5k-20261116T123513Z
```

- Harness commit: `951ccf9d7774dd84b0bc94dabd53ebce56bea12c` (dirty: false)
- Target: `{"commit": "eb90d03740755f5252b8b12cce91fd09970f2d81", "name": "cognee", "package_version": "1.6.1", "ref": "v1.6.1", "repo": "topoteretes/cognee"}`
