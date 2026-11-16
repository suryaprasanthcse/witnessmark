# Reproduce run 20261116T001000Z-dedd3d1f

From the repository root, use the pinned images and run:

```bash
python targets/03-omnigraph/wm_omnigraph.py curve --build edge-b2dbaff --storage proxy --batch m5b-20261115T230235Z --evidence evidence
```

- Harness commit: `6a15b9c950505f412ddd17891f3b2f16be3bc8e5` (dirty: false)
- Build: `edge-b2dbaff`
- Storage: `proxy`
- omnigraph-server: `witnessmark/omnigraph:edge-b2dbaff` (`sha256:b7b8edac24ff8915346cee19eb85ac89c7aeaea6a8069d68410dcbc90e266792`)
- minio: `witnessmark/minio@sha256:5c9f6e9b19cdd3c333900e5102b196bfdb2e19f3e25674bfa0cef924e67dc899` (`sha256:5c9f6e9b19cdd3c333900e5102b196bfdb2e19f3e25674bfa0cef924e67dc899`)
- delay-proxy: `witnessmark/proxy@sha256:a865395be1e245d04d4e0b5a8bcc0813272a8e056f18b2cd94cb5a7230fc3e23` (`sha256:a865395be1e245d04d4e0b5a8bcc0813272a8e056f18b2cd94cb5a7230fc3e23`)
