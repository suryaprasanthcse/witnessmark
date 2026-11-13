# Run 20261113T175500Z-dce0eb46 crashed

```text
Traceback (most recent call last):
  File "C:\myspace\hacckathons\gnomon-b2b-harness\core\witnessmark\memory.py", line 525, in run_cases
    await target.reset(case.group)
  File "C:\myspace\hacckathons\gnomon-b2b-harness\targets\01-zep-graphiti\witnessmark_graphiti\target.py", line 124, in reset
    await driver.build_indices_and_constraints()
  File "C:\myspace\hacckathons\gnomon-b2b-harness\.state\venvs\graphiti-pr1867-a30934e1\Lib\site-packages\graphiti_core\driver\falkordb_driver.py", line 329, in build_indices_and_constraints
    await self.execute_query(query)
  File "C:\myspace\hacckathons\gnomon-b2b-harness\.state\venvs\graphiti-pr1867-a30934e1\Lib\site-packages\graphiti_core\driver\falkordb_driver.py", line 246, in execute_query
    result = await graph.query(cypher_query_, params)  # type: ignore[reportUnknownArgumentType]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\myspace\hacckathons\gnomon-b2b-harness\.state\venvs\graphiti-pr1867-a30934e1\Lib\site-packages\falkordb\asyncio\graph.py", line 114, in query
    return await self._query(q, params=params, timeout=timeout, read_only=False)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\myspace\hacckathons\gnomon-b2b-harness\.state\venvs\graphiti-pr1867-a30934e1\Lib\site-packages\falkordb\asyncio\graph.py", line 84, in _query
    response = await self.execute_command(*command)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\myspace\hacckathons\gnomon-b2b-harness\.state\venvs\graphiti-pr1867-a30934e1\Lib\site-packages\redis\asyncio\client.py", line 946, in execute_command
    result = await conn.retry.call_with_retry(
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\myspace\hacckathons\gnomon-b2b-harness\.state\venvs\graphiti-pr1867-a30934e1\Lib\site-packages\redis\asyncio\retry.py", line 69, in call_with_retry
    return await do()
           ^^^^^^^^^^
  File "C:\myspace\hacckathons\gnomon-b2b-harness\.state\venvs\graphiti-pr1867-a30934e1\Lib\site-packages\redis\asyncio\client.py", line 871, in _send_command_parse_response
    return await self.parse_response(conn, command_name, **options)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\myspace\hacckathons\gnomon-b2b-harness\.state\venvs\graphiti-pr1867-a30934e1\Lib\site-packages\redis\asyncio\client.py", line 993, in parse_response
    response = await connection.read_response()
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\myspace\hacckathons\gnomon-b2b-harness\.state\venvs\graphiti-pr1867-a30934e1\Lib\site-packages\redis\asyncio\connection.py", line 1328, in read_response
    raise response from None
redis.exceptions.ResponseError: Received 5 arguments to procedure 'db.idx.fulltext.createNodeIndex', expected at most 1
```
