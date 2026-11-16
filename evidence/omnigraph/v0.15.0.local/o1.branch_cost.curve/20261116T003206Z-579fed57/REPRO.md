# Reproduce run 20261116T003206Z-579fed57

From the repository root, use the pinned images and run:

```bash
python targets/03-omnigraph/wm_omnigraph.py curve --build v0.15.0 --storage local --include-falkor --batch m5d-20261116T003205Z --evidence evidence
```

- Harness commit: `f7ae8f2f0be485b51f7aac672507c75c904b7af3` (dirty: false)
- Build: `v0.15.0`
- Storage: `local`
- omnigraph-server: `witnessmark/omnigraph:v0.15.0` (`sha256:97d4950250b20019a80b03c8fd52cf52aa6243a86058a54895ba2772f15a2159`)
- minio: `witnessmark/minio@sha256:5c9f6e9b19cdd3c333900e5102b196bfdb2e19f3e25674bfa0cef924e67dc899` (`sha256:5c9f6e9b19cdd3c333900e5102b196bfdb2e19f3e25674bfa0cef924e67dc899`)
