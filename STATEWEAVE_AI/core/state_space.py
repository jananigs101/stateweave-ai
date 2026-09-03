"""
core/state_space.py

STATEWEAVE CORE :: State Space Generation Layer
-----------------------------------------------
Shared infrastructure used by all three search algorithms
(algorithms/bfs.py, dfs.py, astar.py):

  * SearchConfig    - depth limit, max states, pruning knobs
  * SearchContext    - action registry + transition environment + risk engine
  * expand_state()   - given a state, generate its children (this is
                        "generate multiple possible future states from
                        the current state")
  * StateSpaceResult - the resulting tree/graph: nodes + parent/child
                        edges + convenience accessors, with dominance
                        pruning applied at the end.

Performance guarantees implemented here (Section 21 of the spec):
  - state hashing + duplicate detection (via State.signature())
  - search depth limit (SearchConfig.max_depth)
  - maximum state limit (SearchConfig.max_states)
  - risk-threshold pruning (drop branches beyond an unacceptable risk)
  - dominance pruning (drop states that are worse than a sibling on
    every tracked dimension)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.action_engine import ActionRegistry
from core.consequence_engine import ConsequenceEngine
from core.risk_engine import RiskEngine
from core.state_engine import State
from core.transition_engine import Environment, transition


@dataclass
class SearchConfig:
    max_depth: int = 3
    max_states: int = 300
    max_combo_size: int = 2
    risk_threshold: Optional[float] = None    # e.g. 0.95 to prune near-certain disasters
    enable_dominance_pruning: bool = True


@dataclass
class SearchContext:
    action_registry: ActionRegistry
    environment: Environment
    risk_engine: RiskEngine = field(default_factory=RiskEngine)
    consequence_engine: ConsequenceEngine = field(default_factory=ConsequenceEngine)


def expand_state(state: State, context: SearchContext, config: SearchConfig) -> List[State]:
    """Generate the child states reachable from `state` via every
    applicable single action or small action-combination, scoring each
    child's risk and cascading consequences as it's created.
    """
    combos = context.action_registry.generate_combinations(
        state, max_combo_size=config.max_combo_size
    )
    children: List[State] = []
    for combo in combos:
        child = transition(state, combo, context.environment)
        context.risk_engine.evaluate(child)
        context.consequence_engine.analyze(state, child)
        children.append(child)
    return children


@dataclass
class StateSpaceResult:
    root: State
    all_states: List[State] = field(default_factory=list)
    children_of: Dict[int, List[int]] = field(default_factory=dict)
    by_id: Dict[int, State] = field(default_factory=dict)

    def add_state(self, state: State, parent: Optional[State] = None):
        self.all_states.append(state)
        self.by_id[state.state_id] = state
        self.children_of.setdefault(state.state_id, [])
        if parent is not None:
            self.children_of.setdefault(parent.state_id, []).append(state.state_id)

    def leaves(self) -> List[State]:
        return [s for s in self.all_states if not self.children_of.get(s.state_id)]

    def path_to_root(self, state: State) -> List[State]:
        path = [state]
        current = state
        while current.parent_id is not None and current.parent_id in self.by_id:
            current = self.by_id[current.parent_id]
            path.append(current)
        path.reverse()
        return path

    def apply_dominance_pruning(self, config: SearchConfig):
        """Remove states dominated by a sibling: a state A (same parent)
        is dominated by sibling B if B has >= population protection AND
        <= risk AND >= resource_budget than A (i.e. B is at least as
        good on every axis STATEWEAVE tracks for decision quality).
        Dominated leaves are marked, not physically deleted, so the
        tree stays connected for visualization; they're excluded from
        decision ranking via `state.meta["dominated"] = True`.
        """
        if not config.enable_dominance_pruning:
            return

        by_parent: Dict[Optional[int], List[State]] = {}
        for s in self.all_states:
            by_parent.setdefault(s.parent_id, []).append(s)

        for parent_id, siblings in by_parent.items():
            if len(siblings) < 2:
                continue
            for a in siblings:
                for b in siblings:
                    if a.state_id == b.state_id:
                        continue
                    a_risk = a.risk if a.risk is not None else 1.0
                    b_risk = b.risk if b.risk is not None else 1.0
                    a_pop = a.get("population_at_risk")
                    b_pop = b.get("population_at_risk")
                    a_budget = a.get("resource_budget")
                    b_budget = b.get("resource_budget")

                    b_dominates = (
                        b_risk <= a_risk
                        and b_pop <= a_pop
                        and b_budget >= a_budget
                        and (b_risk < a_risk or b_pop < a_pop or b_budget > a_budget)
                    )
                    if b_dominates:
                        a.meta["dominated"] = True
                        break

    def non_dominated_states(self) -> List[State]:
        return [s for s in self.all_states if not s.meta.get("dominated")]
