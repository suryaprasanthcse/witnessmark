# Reproduce run 20261115T232412Z-8935cb2f

From the repository root, use the pinned images and run:

```bash
python targets/03-omnigraph/wm_omnigraph.py parity --build v0.15.0 --storage local --batch m5b-20261115T230235Z --evidence evidence
```

- Harness commit: `6a15b9c950505f412ddd17891f3b2f16be3bc8e5` (dirty: false)
- Build: `v0.15.0`
- Storage: `local`
- omnigraph-server: `witnessmark/omnigraph:v0.15.0` (`sha256:97d4950250b20019a80b03c8fd52cf52aa6243a86058a54895ba2772f15a2159`)
- minio: `witnessmark/minio@sha256:5c9f6e9b19cdd3c333900e5102b196bfdb2e19f3e25674bfa0cef924e67dc899` (`sha256:5c9f6e9b19cdd3c333900e5102b196bfdb2e19f3e25674bfa0cef924e67dc899`)
- neo4j: `neo4j:5.26.2@sha256:099b9f74968c123209972835417985ed2a1cc19c0422c0753a313e26a736c365` (`sha256:099b9f74968c123209972835417985ed2a1cc19c0422c0753a313e26a736c365`)
- falkordb: `falkordb/falkordb@sha256:bef8acb1d8ed9ff8d2ea251767e75c6c05cfa759f7c6bc7e1c122f27d0ea4d7f` (`sha256:bef8acb1d8ed9ff8d2ea251767e75c6c05cfa759f7c6bc7e1c122f27d0ea4d7f`)
