"""
algorithms/dfs.py

Depth-First state-space exploration.

Follows one action path as deep as possible (up to max_depth) before
backtracking, useful for exploring long-horizon consequences of a
committed strategy rather than surveying all near-term options.
"""

from __future__ import annotations

from typing import List

from core.state_engine import State
from core.state_space import SearchConfig, SearchContext, StateSpaceResult, expand_state


def run_dfs(root: State, context: SearchContext, config: SearchConfig) -> StateSpaceResult:
    result = StateSpaceResult(root=root)
    result.add_state(root)

    visited_signatures = {root.signature()}
    stack: List[State] = [root]

    while stack and len(result.all_states) < config.max_states:
        current = stack.pop()
        if current.depth >= config.max_depth:
            continue

        children = expand_state(current, context, config)
        # push in reverse so the first-generated child is explored first
        for child in reversed(children):
            sig = child.signature()
            if sig in visited_signatures:
                continue
            if config.risk_threshold is not None and child.risk is not None:
                if child.risk > config.risk_threshold:
                    continue
            visited_signatures.add(sig)
            result.add_state(child, parent=current)
            stack.append(child)
            if len(result.all_states) >= config.max_states:
                break

    result.apply_dominance_pruning(config)
    return result
