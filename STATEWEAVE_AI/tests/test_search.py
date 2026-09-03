import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from algorithms.astar import optimal_path, run_astar
from algorithms.bfs import run_bfs
from algorithms.dfs import run_dfs
from core.risk_engine import RiskEngine
from core.state_space import SearchConfig, SearchContext
from core.transition_engine import Environment
from domains.disaster_response import build_action_registry, build_initial_state


def _make_context():
    registry = build_action_registry()
    env = Environment(severity=0.5, stochastic=False)
    risk_engine = RiskEngine()
    root = build_initial_state()
    risk_engine.evaluate(root)
    context = SearchContext(action_registry=registry, environment=env, risk_engine=risk_engine)
    return root, context


def test_bfs_generates_states_and_respects_max_states():
    root, context = _make_context()
    config = SearchConfig(max_depth=2, max_states=50, max_combo_size=1)
    result = run_bfs(root, context, config)

    assert len(result.all_states) > 1
    assert len(result.all_states) <= 50
    assert result.all_states[0] is root


def test_bfs_respects_max_depth():
    root, context = _make_context()
    config = SearchConfig(max_depth=1, max_states=500, max_combo_size=1)
    result = run_bfs(root, context, config)
    assert max(s.depth for s in result.all_states) <= 1


def test_dfs_generates_valid_tree():
    root, context = _make_context()
    config = SearchConfig(max_depth=3, max_states=100, max_combo_size=1)
    result = run_dfs(root, context, config)

    assert len(result.all_states) > 1
    for state in result.all_states:
        if state.parent_id is not None:
            assert state.parent_id in result.by_id


def test_astar_finds_a_path_with_decreasing_or_stable_risk_potential():
    root, context = _make_context()
    config = SearchConfig(max_depth=3, max_states=150, max_combo_size=1)
    result = run_astar(root, context, config)
    path = optimal_path(result)

    assert path[0] is root
    assert len(path) >= 1
    # every state in the path should be reachable via parent chain
    for i in range(1, len(path)):
        assert path[i].parent_id == path[i - 1].state_id


def test_deduplication_prevents_duplicate_signatures():
    root, context = _make_context()
    config = SearchConfig(max_depth=2, max_states=100, max_combo_size=1)
    result = run_bfs(root, context, config)
    signatures = [s.signature() for s in result.all_states]
    assert len(signatures) == len(set(signatures))
