# Reproduce run 20261115T231405Z-2793c658

Start the pinned baselines, then run the same configuration:

```bash
docker compose -f baselines/docker-compose.yml up -d
python wm.py run --engine neo4j --scenario claim.state --shape naive --clients 50 --trials 20 --seed 20261118 --no-spread-gate --batch m5b-20261115T230235Z --evidence evidence
```

- Harness commit: `6a15b9c950505f412ddd17891f3b2f16be3bc8e5` (dirty: false)
- Engine: neo4j 5.26.2 community
- Image: `neo4j:5.26.2@sha256:099b9f74968c123209972835417985ed2a1cc19c0422c0753a313e26a736c365`
- Digest: `sha256:099b9f74968c123209972835417985ed2a1cc19c0422c0753a313e26a736c365`
- Clients: 50; trials: 20; seed: 20261118
