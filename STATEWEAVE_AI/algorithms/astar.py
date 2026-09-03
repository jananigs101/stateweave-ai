"""
algorithms/astar.py

A* search for the single optimal decision PATH (root -> leaf) rather
than the full tree -- used to answer "what specific sequence of
actions gets us to the lowest achievable risk fastest".

Cost function:
    g(n) = cumulative resource cost spent to reach state n
    h(n) = heuristic estimate of remaining risk-to-go, using the
           state's current risk score as a lower-bound proxy for how
           much more "work" is needed to reach a safe state (risk can
           only be driven down by further intervention, so current
           risk is an admissible-ish estimate of remaining difficulty)
    f(n) = g(n) + h(n)

This is a best-first search over the SAME expand_state() used by BFS/DFS,
so all three algorithms remain consistent with one another and share
the same pruning behaviour.
"""

from __future__ import annotations

import heapq
import itertools
from typing import List

from core.state_engine import State
from core.state_space import SearchConfig, SearchContext, StateSpaceResult, expand_state


def _g_cost(state: State, initial_budget: float) -> float:
    """Cumulative resource cost spent so far (higher spend = higher g)."""
    spent = initial_budget - state.get("resource_budget")
    return max(0.0, spent)


def _h_cost(state: State) -> float:
    """Heuristic: remaining risk, scaled to be comparable to resource cost."""
    risk = state.risk if state.risk is not None else 1.0
    return risk * 100.0  # scale to be roughly comparable to resource_budget units


def run_astar(root: State, context: SearchContext, config: SearchConfig) -> StateSpaceResult:
    result = StateSpaceResult(root=root)
    result.add_state(root)

    initial_budget = root.get("resource_budget")
    visited_signatures = {root.signature()}

    counter = itertools.count()  # tie-breaker for heap comparisons
    open_heap = []
    f0 = _g_cost(root, initial_budget) + _h_cost(root)
    heapq.heappush(open_heap, (f0, next(counter), root))

    best_leaf = root

    while open_heap and len(result.all_states) < config.max_states:
        f_current, _, current = heapq.heappop(open_heap)

        if current.risk is not None and (best_leaf.risk is None or current.risk < best_leaf.risk):
            best_leaf = current

        if current.depth >= config.max_depth:
            continue

        children = expand_state(current, context, config)
        for child in children:
            sig = child.signature()
            if sig in visited_signatures:
                continue
            if config.risk_threshold is not None and child.risk is not None:
                if child.risk > config.risk_threshold:
                    continue
            visited_signatures.add(sig)
            result.add_state(child, parent=current)

            f_child = _g_cost(child, initial_budget) + _h_cost(child)
            heapq.heappush(open_heap, (f_child, next(counter), child))

            if len(result.all_states) >= config.max_states:
                break

    result.apply_dominance_pruning(config)
    result.meta_best_leaf_id = best_leaf.state_id  # type: ignore[attr-defined]
    return result


def optimal_path(result: StateSpaceResult) -> List[State]:
    """Return the root->leaf path A* judged best (lowest risk reached)."""
    best_leaf_id = getattr(result, "meta_best_leaf_id", None)
    if best_leaf_id is None:
        # fall back: pick the lowest-risk leaf found
        leaves = result.leaves() or result.all_states
        best = min(leaves, key=lambda s: (s.risk if s.risk is not None else 1.0))
    else:
        best = result.by_id[best_leaf_id]
    return result.path_to_root(best)
