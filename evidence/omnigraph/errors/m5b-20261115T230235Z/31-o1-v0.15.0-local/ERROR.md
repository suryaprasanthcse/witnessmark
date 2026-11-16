# o1-v0.15.0-local error

- Batch: `m5b-20261115T230235Z`
- Exit: `1`
- Command: `python targets/03-omnigraph/wm_omnigraph.py curve --build v0.15.0 --storage local --include-falkor --batch m5b-20261115T230235Z --evidence evidence`

```text
Traceback (most recent call last):
  File "<repo>\targets\03-omnigraph\wm_omnigraph.py", line 247, in <module>
    raise SystemExit(main())
                     ~~~~^^
  File "<repo>\targets\03-omnigraph\wm_omnigraph.py", line 172, in main
    manifest, path = run_o1(REPO, evidence, args.batch, args.build, build, args.storage,
                     ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                            include_falkor=args.include_falkor, command=command, smoke=args.smoke)
                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<repo>\targets\03-omnigraph\witnessmark_omnigraph\part2.py", line 671, in run_o1
    sample = _timed_branch_create(client, queries, name, capture)
  File "<repo>\targets\03-omnigraph\witnessmark_omnigraph\part2.py", line 461, in _timed_branch_create
    raise RuntimeError(f"{client_load.thread.name} failed: {client_load.error}")
RuntimeError: wm-o1-unrelated-reader failed: unknown connection: [WinError 10048] Only one usage of each socket address (protocol/network address/port) is normally permitted

```
