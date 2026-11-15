# o1-stable-minio error

- Batch: `m4c-20261115T165831Z`
- Exit: `1`
- Command: `python targets/03-omnigraph/wm_omnigraph.py curve --build v0.15.0 --storage minio --batch m4c-20261115T165831Z`

```text
Traceback (most recent call last):
  File "<repo>\targets\03-omnigraph\wm_omnigraph.py", line 166, in <module>
    raise SystemExit(main())
                     ~~~~^^
  File "<repo>\targets\03-omnigraph\wm_omnigraph.py", line 107, in main
    manifest, path = run_o1(REPO, evidence, args.batch, args.build, build, args.storage,
                     ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                            include_falkor=args.include_falkor)
                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<repo>\targets\03-omnigraph\witnessmark_omnigraph\part2.py", line 426, in run_o1
    sample = _timed_branch_create(client, queries, name)
  File "<repo>\targets\03-omnigraph\witnessmark_omnigraph\part2.py", line 314, in _timed_branch_create
    _check(result, f"create branch {name}")
    ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<repo>\targets\03-omnigraph\witnessmark_omnigraph\part2.py", line 75, in _check
    raise RuntimeError(f"{action}: {result.outcome.value} {result.kind}: {result.message}")
RuntimeError: create branch o1-measure-512000-0-2: unknown connection: Remote end closed connection without response

```
