# Reproduce run 20261122T210504Z-cf3d6bc6

Start the pinned baselines, then run the same configuration:

```bash
docker compose -f baselines/docker-compose.yml up -d
python targets/03-omnigraph/wm_omnigraph.py race --scenario o2a --build v0.16.0 --storage local --clients 50 --trials 20 --spread-gate-ms 55 --provision --batch m6o-20261122T2102Z --evidence evidence
```

- Harness commit: `73cd8e0d32a3ae8ab0876a2f165a2abfb636feaf` (dirty: false)
- Engine: omnigraph-server v0.16.0
- Image: `witnessmark/omnigraph:v0.16.0`
- Digest: `sha256:5e6f483634c49d471485047a5b06841aa1bc4d55aa27971832bc0a5fef5451da`
- minio: `witnessmark/minio@sha256:5c9f6e9b19cdd3c333900e5102b196bfdb2e19f3e25674bfa0cef924e67dc899` (digest: `sha256:5c9f6e9b19cdd3c333900e5102b196bfdb2e19f3e25674bfa0cef924e67dc899`)
- Clients: 50; trials: 20; seed: 0
