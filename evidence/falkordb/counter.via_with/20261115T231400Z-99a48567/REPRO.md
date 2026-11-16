# Reproduce run 20261115T231400Z-99a48567

Start the pinned baselines, then run the same configuration:

```bash
docker compose -f baselines/docker-compose.yml up -d
python wm.py run --engine falkordb --scenario counter --shape via_with --clients 50 --trials 20 --seed 20261116 --no-spread-gate --batch m5b-20261115T230235Z --evidence evidence
```

- Harness commit: `6a15b9c950505f412ddd17891f3b2f16be3bc8e5` (dirty: false)
- Engine: falkordb 6.0.4 (graph module 60004)
- Image: `falkordb/falkordb@sha256:bef8acb1d8ed9ff8d2ea251767e75c6c05cfa759f7c6bc7e1c122f27d0ea4d7f`
- Digest: `sha256:bef8acb1d8ed9ff8d2ea251767e75c6c05cfa759f7c6bc7e1c122f27d0ea4d7f`
- Clients: 50; trials: 20; seed: 20261116
