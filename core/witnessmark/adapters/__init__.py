"""Engine adapters (master blueprint section 4.1). Adapters translate; they never check."""

from .base import Engine, EngineError, EngineUnavailable, Reply, Session

__all__ = ["Engine", "EngineError", "EngineUnavailable", "Reply", "Session", "make_engine"]


def make_engine(name: str, **options) -> Engine:
    if name == "falkordb":
        from .falkordb import FalkorDB

        return FalkorDB(**options)
    if name == "neo4j":
        from .neo4j import Neo4j

        return Neo4j(**options)
    raise ValueError(f"unknown engine {name!r}; expected falkordb or neo4j")
