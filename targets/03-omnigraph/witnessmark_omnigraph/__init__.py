"""Witnessmark's standard-library client and scenario scaffolding for Omnigraph.

The package contains the network adapter plus the O1–O6 controls and runners.
"""

from .client import OmnigraphClient, OperationResult, Outcome

__all__ = ["OmnigraphClient", "OperationResult", "Outcome"]
