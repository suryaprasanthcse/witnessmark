# Reproduce run 20261115T223541Z-d507952d

Start the pinned baselines, then run the same configuration:

```bash
docker compose -f baselines/docker-compose.yml up -d
python wm.py run --engine neo4j --scenario claim.state --shape naive --clients 50 --trials 20 --seed 20261118 --no-spread-gate --batch m5c-20261115T223540Z --evidence evidence
```

- Harness commit: `772ef9601ead98e750aa0a45a9b146bff6423e35` (dirty: false)
- Engine: neo4j 5.26.2 community
- Image: `neo4j:5.26.2@sha256:099b9f74968c123209972835417985ed2a1cc19c0422c0753a313e26a736c365`
- Digest: `sha256:099b9f74968c123209972835417985ed2a1cc19c0422c0753a313e26a736c365`
- Clients: 50; trials: 20; seed: 20261118
