# Reproduce run 20261115T223017Z-22107db4

Start the pinned baselines, then run the same configuration:

```bash
docker compose -f baselines/docker-compose.yml up -d
python targets/03-omnigraph/wm_omnigraph.py race --scenario o2a --build v0.15.0 --storage local --clients 50 --trials 20 --no-spread-gate --provision --batch m5-20261115T222957Z --evidence evidence
```

- Harness commit: `772ef9601ead98e750aa0a45a9b146bff6423e35` (dirty: false)
- Engine: omnigraph-server v0.15.0
- Image: `witnessmark/omnigraph:v0.15.0`
- Digest: `sha256:97d4950250b20019a80b03c8fd52cf52aa6243a86058a54895ba2772f15a2159`
- minio: `witnessmark/minio@sha256:5c9f6e9b19cdd3c333900e5102b196bfdb2e19f3e25674bfa0cef924e67dc899` (digest: `sha256:5c9f6e9b19cdd3c333900e5102b196bfdb2e19f3e25674bfa0cef924e67dc899`)
- Clients: 50; trials: 20; seed: 0
