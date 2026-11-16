# Reproduce run 20261115T231348Z-552b23e0

Start the pinned baseline, then run the same configuration from the repository root:

```bash
docker compose -f baselines/docker-compose.yml up -d falkordb
python targets/03-omnigraph/wm_omnigraph.py costcurve --engine falkordb --spread-gate-ms 40 --batch m5b-20261115T230235Z --evidence evidence
```

- Harness commit: `6a15b9c950505f412ddd17891f3b2f16be3bc8e5` (dirty: false)
- Engine: falkordb 6.0.4 (graph module 60004)
- Image: `falkordb/falkordb@sha256:bef8acb1d8ed9ff8d2ea251767e75c6c05cfa759f7c6bc7e1c122f27d0ea4d7f`
- Digest: `sha256:bef8acb1d8ed9ff8d2ea251767e75c6c05cfa759f7c6bc7e1c122f27d0ea4d7f`
