# Reproduce run 20261113T162508Z-ac1b5b81

Start the pinned baselines, then run the same configuration:

```bash
docker compose -f baselines/docker-compose.yml up -d
python wm.py run --engine neo4j --scenario claim.lease --shape lock_first --clients 50 --trials 20 --seed 20261121
```

- Harness commit: `c31758306e38ea3a8b40af98b965a31900e5e6b5` (dirty: false)
- Engine: neo4j 5.26.2 community
- Image: `neo4j:5.26.2@sha256:099b9f74968c123209972835417985ed2a1cc19c0422c0753a313e26a736c365`
- Digest: `sha256:099b9f74968c123209972835417985ed2a1cc19c0422c0753a313e26a736c365`
- Clients: 50; trials: 20; seed: 20261121
