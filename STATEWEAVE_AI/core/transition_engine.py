"""
core/transition_engine.py

STATEWEAVE CORE :: State Transition Layer
-----------------------------------------------
Implements:   Next State = Transition(Current State, Action, Environment)

This module is domain-independent: it takes a state, a list of one or
more Actions (a "combo"), and an Environment (global stochastic/severity
context), and produces the resulting State by folding each action's
effect function over the state in sequence, then applying environment
drift (e.g. rain keeps falling regardless of what you do).

Determinism vs stochasticity:
  * Action effects are deterministic functions of (state, params) --
    the same action always moves the same variables in the same
    logical direction. This is what "Do NOT simply generate random
    numbers without logical relationships" means in practice.
  * Environment drift and Monte Carlo layers (simulation/monte_carlo.py)
    are where controlled randomness enters, sampling *around* the
    deterministic transition, not replacing it.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List

from core.action_engine import Action, combo_label
from core.state_engine import State, clamp


@dataclass
class Environment:
    """Global environmental context that drifts the state regardless of
    which action is chosen -- e.g. rainfall keeps rising, time keeps
    passing. `severity` in [0,1] scales how aggressive natural drift is.
    """

    severity: float = 0.5
    stochastic: bool = False
    rng: random.Random = field(default_factory=random.Random)

    def drift(self, state: State) -> State:
        """Apply passive environmental change to a state (independent of
        the chosen action). Deterministic unless `stochastic=True`, in
        which case small noise (bounded by severity) is added -- this is
        the hook Monte Carlo uses to perturb a path many times.
        """
        rainfall = state.get("rainfall", 0.0)
        road = state.get("road_availability", 1.0)
        elec = state.get("electricity", 1.0)
        water = state.get("water", 1.0)
        comm = state.get("communication", 1.0)
        time_remaining = state.get("time_remaining", 0.0)

        rain_drift = 2.0 * self.severity
        infra_decay = 0.01 * self.severity

        if self.stochastic:
            rain_drift += self.rng.uniform(-1.5, 3.0) * self.severity
            infra_decay += self.rng.uniform(-0.01, 0.03) * self.severity

        new_state = state.clone(
            rainfall=max(0.0, rainfall + rain_drift),
            road_availability=clamp(road - infra_decay),
            electricity=clamp(elec - infra_decay * 0.6),
            water=clamp(water - infra_decay * 0.4),
            communication=clamp(comm - infra_decay * 0.5),
            time_remaining=max(0.0, time_remaining - 1.0),
        )
        return new_state


def transition(state: State, actions: List[Action], environment: Environment) -> State:
    """Apply a combination of actions to `state`, then apply environment
    drift, and return the fully-formed child State with correct
    provenance fields (parent_id, action label, depth).
    """
    working = state
    for action in actions:
        working = action.apply(working)

    working = environment.drift(working)

    child = State(
        variables=working.variables,
        parent_id=state.state_id,
        action=combo_label(actions),
        depth=state.depth + 1,
    )
    # carry forward cascading-effect trail if present, so downstream
    # explanation layers can show the full lineage
    child.meta["applied_actions"] = [a.name for a in actions]
    child.meta["action_labels"] = [a.label for a in actions]
    return child
