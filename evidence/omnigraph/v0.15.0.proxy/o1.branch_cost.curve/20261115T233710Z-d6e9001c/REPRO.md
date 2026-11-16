# Reproduce run 20261115T233710Z-d6e9001c

From the repository root, use the pinned images and run:

```bash
python targets/03-omnigraph/wm_omnigraph.py curve --build v0.15.0 --storage proxy --batch m5b-20261115T230235Z --evidence evidence
```

- Harness commit: `6a15b9c950505f412ddd17891f3b2f16be3bc8e5` (dirty: false)
- Build: `v0.15.0`
- Storage: `proxy`
- omnigraph-server: `witnessmark/omnigraph:v0.15.0` (`sha256:97d4950250b20019a80b03c8fd52cf52aa6243a86058a54895ba2772f15a2159`)
- minio: `witnessmark/minio@sha256:5c9f6e9b19cdd3c333900e5102b196bfdb2e19f3e25674bfa0cef924e67dc899` (`sha256:5c9f6e9b19cdd3c333900e5102b196bfdb2e19f3e25674bfa0cef924e67dc899`)
- delay-proxy: `witnessmark/proxy@sha256:a865395be1e245d04d4e0b5a8bcc0813272a8e056f18b2cd94cb5a7230fc3e23` (`sha256:a865395be1e245d04d4e0b5a8bcc0813272a8e056f18b2cd94cb5a7230fc3e23`)
