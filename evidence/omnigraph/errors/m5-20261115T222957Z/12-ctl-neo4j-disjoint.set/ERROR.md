# ctl-neo4j-disjoint.set error

- Batch: `m5-20261115T222957Z`
- Exit: `1`
- Command: `python wm.py run --engine neo4j --scenario disjoint --shape set --clients 50 --trials 20 --seed 20261124 --no-spread-gate --batch m5-20261115T222957Z --evidence evidence`

```text
Traceback (most recent call last):
  File "<repo>\wm.py", line 16, in <module>
    sys.exit(main())
             ~~~~^^
  File "<repo>\core\witnessmark\cli.py", line 179, in main
    return args.func(args)
           ~~~~~~~~~^^^^^^
  File "<repo>\core\witnessmark\cli.py", line 61, in cmd_run
    manifest = run(config)
  File "<repo>\core\witnessmark\runner.py", line 212, in run
    component = engine.describe()
  File "<repo>\core\witnessmark\adapters\neo4j.py", line 126, in describe
    found = self.discovery()
  File "<repo>\core\witnessmark\adapters\neo4j.py", line 110, in discovery
    response = conn.getresponse()
  File "<user-home>", line 1478, in getresponse
    response.begin()
    ~~~~~~~~~~~~~~^^
  File "<user-home>", line 343, in begin
    version, status, reason = self._read_status()
                              ~~~~~~~~~~~~~~~~~^^
  File "<user-home>", line 312, in _read_status
    raise RemoteDisconnected("Remote end closed connection without"
                             " response")
http.client.RemoteDisconnected: Remote end closed connection without response

```
