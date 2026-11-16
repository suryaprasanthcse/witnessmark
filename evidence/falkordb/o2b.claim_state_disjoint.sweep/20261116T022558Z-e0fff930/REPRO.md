# Reproduce run 20261116T022558Z-e0fff930

Start the pinned baseline, then run the same configuration from the repository root:

```bash
docker compose -f baselines/docker-compose.yml up -d falkordb
python targets/03-omnigraph/wm_omnigraph.py costcurve --engine falkordb --spread-gate-ms 40 --batch m5f-20261116T021553Z --evidence evidence
```

- Harness commit: `4212c994a384b7a887b34ba6ec88fc5c5afa731a` (dirty: false)
- Engine: falkordb 6.0.4 (graph module 60004)
- Image: `falkordb/falkordb@sha256:bef8acb1d8ed9ff8d2ea251767e75c6c05cfa759f7c6bc7e1c122f27d0ea4d7f`
- Digest: `sha256:bef8acb1d8ed9ff8d2ea251767e75c6c05cfa759f7c6bc7e1c122f27d0ea4d7f`
