# Reproduce run 20261116T021606Z-a0862379

From the repository root, use the pinned images and run:

```bash
python targets/03-omnigraph/wm_omnigraph.py costcurve --engine omnigraph --build v0.15.0 --storage local --spread-gate-ms 55 --batch m5f-20261116T021553Z --evidence evidence
```

- Harness commit: `4212c994a384b7a887b34ba6ec88fc5c5afa731a` (dirty: false)
- Build: `v0.15.0`
- Storage: `local`
- omnigraph-server: `witnessmark/omnigraph:v0.15.0` (`sha256:97d4950250b20019a80b03c8fd52cf52aa6243a86058a54895ba2772f15a2159`)
- minio: `witnessmark/minio@sha256:5c9f6e9b19cdd3c333900e5102b196bfdb2e19f3e25674bfa0cef924e67dc899` (`sha256:5c9f6e9b19cdd3c333900e5102b196bfdb2e19f3e25674bfa0cef924e67dc899`)
