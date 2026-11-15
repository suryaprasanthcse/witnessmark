# Run 20261114T140306Z-9f88c9a1 crashed

```text
Traceback (most recent call last):
  File "C:\myspace\hacckathons\gnomon-b2b-harness\core\witnessmark\memory.py", line 492, in run_race
    states = {group: await target.dump(group) for group in scenario.groups()}
                     ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\myspace\hacckathons\gnomon-b2b-harness\targets\02-cognee\witnessmark_cognee\target.py", line 169, in dump
    return await (await self._helper()).call("dump", group)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\myspace\hacckathons\gnomon-b2b-harness\targets\02-cognee\witnessmark_cognee\helper.py", line 129, in call
    return await future
           ^^^^^^^^^^^^
witnessmark_cognee.helper.RemoteError: SubprocessTransportError: SubprocessTransportError: Subprocess init exited before signalling ready after 60.0s (pid=18748 exitcode=1 alive=False) <- Empty: 
```
