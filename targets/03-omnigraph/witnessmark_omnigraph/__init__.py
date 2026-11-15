"""Witnessmark's standard-library client and scenario scaffolding for Omnigraph.

Phase 2 TODO: implement O1, O4 and O5 and wire O2, O3 and O6 to runners.
"""

from .client import OmnigraphClient, OperationResult, Outcome

__all__ = ["OmnigraphClient", "OperationResult", "Outcome"]
