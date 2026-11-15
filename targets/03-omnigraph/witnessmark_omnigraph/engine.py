"""Core-runner adapter for an Omnigraph network server."""

from __future__ import annotations

from pathlib import Path

from witnessmark.adapters.base import Engine, EngineError, EngineUnavailable, Reply, Session

from .actors import describe as describe_actors
from .client import OmnigraphClient, OperationResult, Outcome
from .workload import load_queries


def _token(result: OperationResult) -> str | None:
    data = result.data if isinstance(result.data, dict) else {}
    if data.get("graph_commit_id"):
        return str(data["graph_commit_id"])
    commit = data.get("commit")
    return str(commit["graph_commit_id"]) if isinstance(commit, dict) and commit.get("graph_commit_id") else None


class OmnigraphSession(Session):
    def __init__(self, endpoint: str, graph: str, timeout: float, queries: dict[str, str],
                 bearer_token: str | None = None, actor: str | None = None):
        self.client = OmnigraphClient(endpoint, graph, timeout=timeout, bearer_token=bearer_token)
        self.queries = queries
        self.actor = actor

    @staticmethod
    def _raise(result: OperationResult) -> None:
        if result.outcome is Outcome.UNKNOWN:
            raise EngineUnavailable(result.kind or "unknown", result.message or "outcome unknown")
        if result.outcome is Outcome.REFUSAL:
            data = result.data if isinstance(result.data, dict) else {}
            raise EngineError(result.kind or "refusal", result.message or "operation refused",
                              str(data.get("code")) if data.get("code") is not None else None)

    def run(self, query: str, params: dict | None = None, *, write: bool = True) -> Reply:
        if query == "merge_agent_branch":
            result = self.client.merge((params or {})["source"], target="main")
            self._raise(result)
            return Reply([], [], _token(result))
        if query not in self.queries:
            raise ValueError(f"unknown Omnigraph workload query {query!r}")
        arguments = dict(params or {})
        branch = arguments.pop("_branch", None)
        snapshot = arguments.pop("_snapshot", None)
        commit_id = arguments.pop("_commit_id", None)
        if write:
            result = self.client.mutate(self.queries[query], arguments, name=query, branch=branch,
                                        commit_id=commit_id)
        else:
            result = self.client.query(self.queries[query], arguments, name=query, branch=branch, snapshot=snapshot)
        self._raise(result)
        data = result.data if isinstance(result.data, dict) else {}
        columns = [str(column) for column in data.get("columns", [])]
        rows = [[row.get(column) for column in columns] for row in data.get("rows", [])]
        return Reply(columns, rows, _token(result), dict(data))

    def ping(self) -> None:
        result = self.client.health()
        self._raise(result)
        if not result.ok:
            raise EngineUnavailable("health", "health check did not succeed")

    def dump_task(self, task: str) -> dict:
        task_reply = self.run("q_task", {"task_id": task}, write=False)
        snapshot = task_reply.token
        if snapshot is None:
            raise EngineUnavailable("protocol", "q_task did not return graph_commit_id")
        holder = self.run("q_task_holder", {"task_id": task, "_snapshot": snapshot}, write=False)
        task_rows = [dict(zip(task_reply.columns, row)) for row in task_reply.rows]
        holder_rows = [dict(zip(holder.columns, row)) for row in holder.rows]
        lease_rows = [{"id": str(row["rw"]), "task": task, "agent": str(row["holder"]),
                       "from_seq": int(row["from_seq"]), "until_seq": None,
                       "observed_graph_commit_id": snapshot, "observed_order": index + 1}
                      for index, row in enumerate(holder_rows)]
        return {
            "snapshot": snapshot,
            "tasks": task_rows,
            "holders": {task: [str(row["holder"]) for row in holder_rows]},
            "lease_records": lease_rows,
        }

    def close(self) -> None:
        pass


class OmnigraphEngine(Engine):
    name = "omnigraph"
    repo = "https://github.com/ModernRelay/omnigraph"

    def __init__(self, endpoint: str, build: str, image: str, digest: str, *, graph: str = "witnessmark",
                 storage: str = "local", queries_path: Path | None = None,
                 actor_tokens: list[tuple[str, str]] | None = None):
        self.endpoint = endpoint
        self.build = build
        self.image = image
        self.digest = digest
        self.graph = graph
        self.storage = storage
        self.queries = load_queries(queries_path)
        # Per-client actors (actors.py). The core runner opens the admin session first, then one session per
        # client in client order, so sessions take the (actor, token) pairs in that order, cycling per run.
        self.actor_tokens = actor_tokens
        self._next_token = 0

    def session(self, timeout: float = 60.0) -> OmnigraphSession:
        if not self.actor_tokens:
            return OmnigraphSession(self.endpoint, self.graph, timeout, self.queries)
        actor, token = self.actor_tokens[self._next_token % len(self.actor_tokens)]
        self._next_token += 1
        return OmnigraphSession(self.endpoint, self.graph, timeout, self.queries, bearer_token=token, actor=actor)

    def reset(self, session: Session) -> None:
        session.run("m_reset", {})

    def health(self) -> dict:
        result = OmnigraphClient(self.endpoint, self.graph, timeout=5).health()
        data = result.data if isinstance(result.data, dict) else {}
        return {"ok": result.ok, "outcome": result.outcome.value, "kind": result.kind, **data}

    def describe(self) -> dict:
        return {
            "name": "omnigraph-server",
            "version": self.build,
            "image": self.image,
            "digest": self.digest,
            "role": "sut",
            "config": {"endpoint": self.endpoint, "graph": self.graph, "storage": self.storage,
                       "actors": describe_actors(self.actor_tokens)},
        }
