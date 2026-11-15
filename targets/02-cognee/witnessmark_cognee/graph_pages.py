"""Graph dumps for Cognee's supported backends."""

import os


async def _graph_data(engine) -> tuple[list, list]:
    """Every node and edge of the graph store.

    FalkorDB truncates every result set at its RESULTSET_SIZE (10,000 by default in 6.0.4), and the community
    adapter's get_graph_data asks for everything in one query, so on that store it silently returns at most
    10,000 nodes and 10,000 edges (target blueprint C28). The dump pages through the same queries instead.
    """
    # cognee 1.6.1 hands out a _GraphEngineHandle that forwards attribute access to the adapter, so the class name
    # says nothing; the row's provider does.
    if os.environ.get("GRAPH_DATABASE_PROVIDER") != "falkor":
        return await engine.get_graph_data()
    page, nodes, edges = 5000, [], []
    skip = 0
    while True:
        result = await engine.query("MATCH (n) RETURN ID(n) AS id, labels(n) AS labels, properties(n) AS properties "
                                    "ORDER BY ID(n) SKIP $skip LIMIT $limit", {"skip": skip, "limit": page})
        rows = result.result_set
        nodes += [(record[2]["id"], engine._deserialize_node_properties(record[2])) for record in rows]
        if len(rows) < page:
            break
        skip += page
    skip = 0
    while True:
        result = await engine.query("MATCH (n)-[r]->(m) RETURN n.id AS source, m.id AS target, TYPE(r) AS type, "
                                    "properties(r) AS properties ORDER BY ID(r) SKIP $skip LIMIT $limit",
                                    {"skip": skip, "limit": page})
        rows = result.result_set
        edges += [(str(record[0]), str(record[1]), record[2], record[3]) for record in rows]
        if len(rows) < page:
            break
        skip += page
    return nodes, edges
