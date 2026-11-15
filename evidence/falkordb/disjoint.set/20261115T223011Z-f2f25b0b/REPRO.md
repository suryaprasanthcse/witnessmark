# Reproduce run 20261115T223011Z-f2f25b0b

Start the pinned baselines, then run the same configuration:

```bash
docker compose -f baselines/docker-compose.yml up -d
python wm.py run --engine falkordb --scenario disjoint --shape set --clients 50 --trials 20 --seed 20261117 --no-spread-gate --batch m5-20261115T222957Z --evidence evidence
```

- Harness commit: `772ef9601ead98e750aa0a45a9b146bff6423e35` (dirty: false)
- Engine: falkordb 6.0.4 (graph module 60004)
- Image: `falkordb/falkordb@sha256:bef8acb1d8ed9ff8d2ea251767e75c6c05cfa759f7c6bc7e1c122f27d0ea4d7f`
- Digest: `sha256:bef8acb1d8ed9ff8d2ea251767e75c6c05cfa759f7c6bc7e1c122f27d0ea4d7f`
- Clients: 50; trials: 20; seed: 20261117
