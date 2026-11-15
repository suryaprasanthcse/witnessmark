"""One Omnigraph actor per race client (M5 Phase B).

Batch m5-20261115T222957Z ran 50 unauthenticated clients, which the server
treated as one actor: 34 of 50 claims per trial were refused with HTTP 429,
"actor in-flight count cap 16 exceeded". The pinned server guide documents an
actor-to-token object, ``OMNIGRAPH_SERVER_BEARER_TOKENS_JSON``, in which the
token selects the actor, and a graph policy bound in ``cluster.yaml`` and
installed by ``cluster apply`` (docs/user/operations/server.md and policy.md at
v0.15.0 and b2dbaff). Each client therefore gets its own actor and token.

Tokens are random per run, live only in memory and in the server container's
environment, and are never written to evidence: manifests record actor names
and the token source only.
"""

from __future__ import annotations

import secrets
from pathlib import Path

from witnessmark.scenarios import client_name

ADMIN_ACTOR = "wm-admin"
MAX_CLIENTS = 50
TOKEN_SOURCE = "OMNIGRAPH_SERVER_BEARER_TOKENS_JSON"
CLUSTER_CONFIG = "cluster-actors.yaml"
POLICY_FILE = "actors.policy.yaml"
# policy.md: a rule sets branch_scope (source branch) or target_branch_scope (destination), not both, and
# graph-wide invoke_query rules take no branch scope. The pinned validator refuses branch_scope on
# branch_create, so the branch actions are scoped by their target.
POLICY_RULES = (
    ("agents-read-and-change", ("read", "change"), "branch_scope"),
    ("agents-branch-and-merge", ("branch_create", "branch_delete", "branch_merge"), "target_branch_scope"),
    ("agents-invoke-queries", ("invoke_query",), None),
)
POLICY_ACTIONS = tuple(action for _, actions, _ in POLICY_RULES for action in actions)
TOKEN_PREFIX = "wmtok-"


def client_actor(i: int) -> str:
    return f"wm-{client_name(i)}"


def all_actors() -> list[str]:
    """Every actor the checked-in policy names: the admin first, then c00..c49."""
    return [ADMIN_ACTOR] + [client_actor(i) for i in range(MAX_CLIENTS)]


def make_tokens(clients: int) -> list[tuple[str, str]]:
    """(actor, token) pairs: the admin first, then one per client in client order."""
    if not 1 <= clients <= MAX_CLIENTS:
        raise ValueError(f"per-client actors support 1 to {MAX_CLIENTS} clients, not {clients}")
    actors = [ADMIN_ACTOR] + [client_actor(i) for i in range(clients)]
    return [(actor, TOKEN_PREFIX + secrets.token_hex(16)) for actor in actors]


def describe(tokens: list[tuple[str, str]] | None) -> dict:
    """What a manifest records about authentication; never a token."""
    if not tokens:
        return {"mode": "shared", "note": "unauthenticated server (--unauthenticated); every client is one actor"}
    return {"mode": "per-client", "token_source": TOKEN_SOURCE, "admin_actor": tokens[0][0],
            "client_actors": [actor for actor, _ in tokens[1:]],
            "policy": f"targets/03-omnigraph/workload/{POLICY_FILE}",
            "cluster_config": f"targets/03-omnigraph/workload/{CLUSTER_CONFIG}",
            "policy_actions": list(POLICY_ACTIONS)}


def policy_text() -> str:
    """The checked-in policy file's exact text (a unit test keeps the two equal)."""
    lines = ["# One actor per race client (targets/03-omnigraph/witnessmark_omnigraph/actors.py).",
             "# Format: docs/user/operations/policy.md at v0.15.0 and b2dbaff.",
             "version: 1",
             "groups:",
             f"  agents: [{', '.join(all_actors())}]",
             "rules:"]
    for rule_id, actions, scope in POLICY_RULES:
        lines += [f"  - id: {rule_id}",
                  "    allow:",
                  "      actors: { group: agents }",
                  f"      actions: [{', '.join(actions)}]"]
        if scope:
            lines.append(f"      {scope}: any")
    return "\n".join(lines) + "\n"


def policy_path(repo: Path) -> Path:
    return repo / "targets" / "03-omnigraph" / "workload" / POLICY_FILE
