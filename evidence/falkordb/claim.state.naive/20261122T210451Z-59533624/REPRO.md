# Reproduce run 20261122T210451Z-59533624

Start the pinned baselines, then run the same configuration:

```bash
docker compose -f baselines/docker-compose.yml up -d
python wm.py run --engine falkordb --scenario claim.state --shape naive --clients 50 --trials 20 --seed 20261113 --no-spread-gate --batch m6o-20261122T2102Z --evidence evidence
```

- Harness commit: `73cd8e0d32a3ae8ab0876a2f165a2abfb636feaf` (dirty: false)
- Engine: falkordb 6.0.4 (graph module 60004)
- Image: `falkordb/falkordb@sha256:bef8acb1d8ed9ff8d2ea251767e75c6c05cfa759f7c6bc7e1c122f27d0ea4d7f`
- Digest: `sha256:bef8acb1d8ed9ff8d2ea251767e75c6c05cfa759f7c6bc7e1c122f27d0ea4d7f`
- Clients: 50; trials: 20; seed: 20261113
