# Reproduce run 20261115T223237Z-3658b53d

Start the pinned baselines, then run the same configuration:

```bash
docker compose -f baselines/docker-compose.yml up -d
python targets/03-omnigraph/wm_omnigraph.py race --scenario o2c --build edge-b2dbaff --storage local --clients 50 --trials 20 --no-spread-gate --provision --batch m5-20261115T222957Z --evidence evidence
```

- Harness commit: `772ef9601ead98e750aa0a45a9b146bff6423e35` (dirty: false)
- Engine: omnigraph-server edge-b2dbaff
- Image: `witnessmark/omnigraph:edge-b2dbaff`
- Digest: `sha256:b7b8edac24ff8915346cee19eb85ac89c7aeaea6a8069d68410dcbc90e266792`
- minio: `witnessmark/minio@sha256:5c9f6e9b19cdd3c333900e5102b196bfdb2e19f3e25674bfa0cef924e67dc899` (digest: `sha256:5c9f6e9b19cdd3c333900e5102b196bfdb2e19f3e25674bfa0cef924e67dc899`)
- Clients: 50; trials: 20; seed: 0
