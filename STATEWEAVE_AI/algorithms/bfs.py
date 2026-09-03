"""
algorithms/bfs.py

Breadth-First state-space exploration.

Explores the state space level by level (all depth-1 states, then all
depth-2 states, ...) so it's well suited for "what are ALL the near-term
options and their immediate consequences" style exploration.

Includes the shared pruning/deduplication machinery so BFS, DFS and A*
all respect the same performance guarantees (see core/state_space.py's
SearchConfig for max_states / risk_threshold / dominance pruning).
"""

from __future__ import annotations

from collections import deque
from typing import List

from core.state_engine import State
from core.state_space import SearchConfig, SearchContext, StateSpaceResult, expand_state


def run_bfs(root: State, context: SearchContext, config: SearchConfig) -> StateSpaceResult:
    result = StateSpaceResult(root=root)
    result.add_state(root)

    frontier = deque([root])
    visited_signatures = {root.signature()}

    while frontier and len(result.all_states) < config.max_states:
        current = frontier.popleft()
        if current.depth >= config.max_depth:
            continue

        children = expand_state(current, context, config)
        for child in children:
            sig = child.signature()
            if sig in visited_signatures:
                continue
            if config.risk_threshold is not None and child.risk is not None:
                if child.risk > config.risk_threshold:
                    continue  # risk-threshold pruning
            visited_signatures.add(sig)
            result.add_state(child, parent=current)
            frontier.append(child)
            if len(result.all_states) >= config.max_states:
                break

    result.apply_dominance_pruning(config)
    return result
