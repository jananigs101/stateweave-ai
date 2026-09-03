"""
core/state_engine.py

STATEWEAVE CORE :: State Representation Layer
-----------------------------------------------
Defines the canonical State object used across the entire engine.
A State is a structured, hashable, comparable snapshot of a scenario
at one point in the state-space search.

Design goals:
  * Domain-independent: only knows about generic numeric "variables".
  * Hashable + comparable, so BFS/DFS/A* can deduplicate visited states.
  * Carries provenance (which action produced it, from which parent)
    so the search tree / graph can be reconstructed and explained.
"""

from __future__ import annotations

import hashlib
import itertools
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


_id_counter = itertools.count(1)


def _round_variables(variables: Dict[str, float], ndigits: int = 4) -> Dict[str, float]:
    """Round numeric variables so near-identical states hash identically.

    Without this, floating point drift would make deduplication useless
    (two practically-equal states would never compare equal).
    """
    rounded = {}
    for key, value in variables.items():
        if isinstance(value, (int, float)):
            rounded[key] = round(float(value), ndigits)
        else:
            rounded[key] = value
    return rounded


@dataclass
class State:
    """A single point in the state space.

    Attributes:
        variables: dict of scenario variables (population_at_risk, shelters, ...)
        state_id: unique integer id assigned on creation (for graph rendering)
        parent_id: id of the state this one was derived from (None for root)
        action: human-readable label of the action that produced this state
        depth: how many transitions away from the root state
        risk: cached risk score (filled in by the RiskEngine), 0..1
        meta: free-form dictionary for engine-specific annotations
              (e.g. cascading effects, monte carlo results, explanations)
    """

    variables: Dict[str, float]
    state_id: int = field(default_factory=lambda: next(_id_counter))
    parent_id: Optional[int] = None
    action: str = "INITIAL_STATE"
    depth: int = 0
    risk: Optional[float] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.variables = _round_variables(self.variables)

    # ------------------------------------------------------------------
    # Hashing / equality — required for deduplication during search
    # ------------------------------------------------------------------
    def signature(self) -> str:
        """A stable string signature representing the *content* of the state
        (independent of state_id/parent/depth, which are provenance, not content).
        """
        items = sorted(self.variables.items())
        payload = "|".join(f"{k}={v}" for k, v in items)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def __hash__(self):
        return hash(self.signature())

    def __eq__(self, other):
        if not isinstance(other, State):
            return NotImplemented
        return self.signature() == other.signature()

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------
    def get(self, key: str, default: float = 0.0) -> float:
        return self.variables.get(key, default)

    def set(self, key: str, value: float):
        self.variables[key] = value

    def clone(self, **overrides) -> "State":
        """Create a derived state; does NOT copy state_id/parent/action —
        those must be set explicitly by the transition engine so provenance
        is always intentional, never accidental.
        """
        new_vars = dict(self.variables)
        new_vars.update(overrides)
        return State(variables=new_vars)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_id": self.state_id,
            "parent_id": self.parent_id,
            "action": self.action,
            "depth": self.depth,
            "risk": self.risk,
            "variables": dict(self.variables),
            "meta": dict(self.meta),
        }

    def __repr__(self):
        return f"State(id={self.state_id}, action={self.action!r}, risk={self.risk}, depth={self.depth})"


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a fractional variable (e.g. road_availability) into [low, high]."""
    return max(low, min(high, value))


def clamp_nonneg(value: float) -> float:
    """Clamp a count/quantity variable (e.g. shelters) to be non-negative."""
    return max(0.0, value)
