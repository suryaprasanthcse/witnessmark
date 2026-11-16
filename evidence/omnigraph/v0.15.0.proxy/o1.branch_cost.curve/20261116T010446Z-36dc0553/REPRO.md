# Reproduce run 20261116T010446Z-36dc0553

From the repository root, use the pinned images and run:

```bash
python targets/03-omnigraph/wm_omnigraph.py curve --build v0.15.0 --storage proxy --batch m5e-20261116T004953Z --evidence evidence
```

- Harness commit: `fb975183c263e39e27074a116f1b96721193be76` (dirty: false)
- Build: `v0.15.0`
- Storage: `proxy`
- omnigraph-server: `witnessmark/omnigraph:v0.15.0` (`sha256:97d4950250b20019a80b03c8fd52cf52aa6243a86058a54895ba2772f15a2159`)
- minio: `witnessmark/minio@sha256:5c9f6e9b19cdd3c333900e5102b196bfdb2e19f3e25674bfa0cef924e67dc899` (`sha256:5c9f6e9b19cdd3c333900e5102b196bfdb2e19f3e25674bfa0cef924e67dc899`)
- delay-proxy: `witnessmark/proxy@sha256:a865395be1e245d04d4e0b5a8bcc0813272a8e056f18b2cd94cb5a7230fc3e23` (`sha256:a865395be1e245d04d4e0b5a8bcc0813272a8e056f18b2cd94cb5a7230fc3e23`)
