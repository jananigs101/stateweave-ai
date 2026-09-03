"""
core/action_engine.py

STATEWEAVE CORE :: Action Generation Layer
-----------------------------------------------
An Action is a domain-independent unit of intervention: it has a name,
a resource cost, and a pure function State -> State (the actual effect
is implemented by the domain layer, e.g. domains/disaster_response.py,
and registered here).

The ActionEngine's job is purely to hold/generate the *set* of actions
that are applicable to a given state -- the "what could we do right now"
question. The *effect* of each action is delegated to the transition
engine, which calls back into the domain-specific effect function.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from core.state_engine import State


EffectFn = Callable[[State, dict], State]  # (state, params) -> new_state


@dataclass
class Action:
    """A single possible intervention.

    Attributes:
        name: short unique identifier, e.g. "deploy_rescue_units"
        label: human-readable label, e.g. "Deploy Rescue Units"
        category: grouping used for UI + explanations, e.g. "Resource"
        resource_cost: normalized 0..1 cost used in decision scoring
        params: action-specific parameters (e.g. how many units)
        effect_fn: the domain function implementing State -> State
        precondition: optional function State -> bool; if False the
            action is not applicable to that state
        description: short explanation for the UI / report
    """

    name: str
    label: str
    category: str
    resource_cost: float
    effect_fn: EffectFn
    params: Dict = field(default_factory=dict)
    precondition: Optional[Callable[[State], bool]] = None
    description: str = ""

    def is_applicable(self, state: State) -> bool:
        if self.precondition is None:
            return True
        return self.precondition(state)

    def apply(self, state: State) -> State:
        return self.effect_fn(state, self.params)


class ActionRegistry:
    """Holds all actions known to the current domain and can generate
    the applicable subset for a given state, plus useful combinations.
    """

    def __init__(self):
        self._actions: Dict[str, Action] = {}

    def register(self, action: Action):
        self._actions[action.name] = action

    def register_many(self, actions: List[Action]):
        for a in actions:
            self.register(a)

    def all(self) -> List[Action]:
        return list(self._actions.values())

    def get(self, name: str) -> Action:
        return self._actions[name]

    def applicable_actions(self, state: State) -> List[Action]:
        """Actions whose preconditions currently hold for this state."""
        return [a for a in self._actions.values() if a.is_applicable(state)]

    def generate_combinations(self, state: State, max_combo_size: int = 2) -> List[List[Action]]:
        """Generate single actions plus small combinations of actions
        (e.g. "Evacuate Zone" + "Emergency Corridor"), used so the search
        can consider joint interventions, not just single moves.

        Kept small (max_combo_size default 2) to avoid combinatorial
        explosion -- this is intentional, not an oversight.
        """
        from itertools import combinations

        applicable = self.applicable_actions(state)
        combos: List[List[Action]] = [[a] for a in applicable]

        if max_combo_size >= 2:
            for a, b in combinations(applicable, 2):
                # avoid pairing an action with itself or incompatible pairs
                if a.category == b.category and a.name == b.name:
                    continue
                combos.append([a, b])

        return combos


def combo_label(actions: List[Action]) -> str:
    return " + ".join(a.label for a in actions)


def combo_cost(actions: List[Action]) -> float:
    return sum(a.resource_cost for a in actions)
