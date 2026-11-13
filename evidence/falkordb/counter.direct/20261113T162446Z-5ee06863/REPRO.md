# Reproduce run 20261113T162446Z-5ee06863

Start the pinned baselines, then run the same configuration:

```bash
docker compose -f baselines/docker-compose.yml up -d
python wm.py run --engine falkordb --scenario counter --shape direct --clients 50 --trials 20 --seed 20261115
```

- Harness commit: `c31758306e38ea3a8b40af98b965a31900e5e6b5` (dirty: false)
- Engine: falkordb 6.0.4 (graph module 60004)
- Image: `falkordb/falkordb@sha256:bef8acb1d8ed9ff8d2ea251767e75c6c05cfa759f7c6bc7e1c122f27d0ea4d7f`
- Digest: `sha256:bef8acb1d8ed9ff8d2ea251767e75c6c05cfa759f7c6bc7e1c122f27d0ea4d7f`
- Clients: 50; trials: 20; seed: 20261115
