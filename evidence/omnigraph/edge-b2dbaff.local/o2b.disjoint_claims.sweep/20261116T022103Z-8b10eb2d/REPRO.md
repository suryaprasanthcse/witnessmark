# Reproduce run 20261116T022103Z-8b10eb2d

From the repository root, use the pinned images and run:

```bash
python targets/03-omnigraph/wm_omnigraph.py costcurve --engine omnigraph --build edge-b2dbaff --storage local --spread-gate-ms 55 --batch m5f-20261116T021553Z --evidence evidence
```

- Harness commit: `4212c994a384b7a887b34ba6ec88fc5c5afa731a` (dirty: false)
- Build: `edge-b2dbaff`
- Storage: `local`
- omnigraph-server: `witnessmark/omnigraph:edge-b2dbaff` (`sha256:b7b8edac24ff8915346cee19eb85ac89c7aeaea6a8069d68410dcbc90e266792`)
- minio: `witnessmark/minio@sha256:5c9f6e9b19cdd3c333900e5102b196bfdb2e19f3e25674bfa0cef924e67dc899` (`sha256:5c9f6e9b19cdd3c333900e5102b196bfdb2e19f3e25674bfa0cef924e67dc899`)
