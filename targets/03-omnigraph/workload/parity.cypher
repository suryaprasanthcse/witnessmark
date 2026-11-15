// Witnessmark M4 O6 parity queries for FalkorDB 6.0.4 and Neo4j 5.26.2.
// Omnigraph equivalents: q_eligible and q_live in queries.gq.

// q_eligible
MATCH (agent:Agent)-[:HasSkill]->(:Skill)<-[:Needs]-(task:Task)
RETURN DISTINCT agent.id AS agent, task.id AS task
ORDER BY agent, task;

// q_live; $task_id identifies the task whose live HeldBy edges are counted.
MATCH (task:Task {id: $task_id})
OPTIONAL MATCH (task)-[:HeldBy]->(holder:Agent)
RETURN count(holder) AS live;
