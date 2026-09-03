import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from algorithms.bfs import run_bfs
from core.decision_engine import DecisionEngine
from core.risk_engine import RiskEngine, risk_category
from core.state_space import SearchConfig, SearchContext
from core.transition_engine import Environment
from domains.disaster_response import build_action_registry, build_initial_state
from simulation.monte_carlo import run_monte_carlo


def test_risk_score_in_valid_range():
    root = build_initial_state()
    engine = RiskEngine()
    breakdown = engine.evaluate(root)
    assert 0.0 <= breakdown.total <= 1.0
    assert breakdown.category in {"LOW", "MODERATE", "HIGH", "CRITICAL"}


def test_risk_category_thresholds():
    assert risk_category(0.1) == "LOW"
    assert risk_category(0.4) == "MODERATE"
    assert risk_category(0.6) == "HIGH"
    assert risk_category(0.9) == "CRITICAL"


def test_higher_population_at_risk_increases_risk():
    engine = RiskEngine()
    low = build_initial_state({"population_at_risk": 10_000})
    high = build_initial_state({"population_at_risk": 200_000})
    low_score = engine.evaluate(low).total
    high_score = engine.evaluate(high).total
    assert high_score > low_score


def test_decision_ranking_orders_by_score_descending():
    registry = build_action_registry()
    env = Environment(severity=0.4, stochastic=False)
    risk_engine = RiskEngine()
    root = build_initial_state()
    risk_engine.evaluate(root)

    context = SearchContext(action_registry=registry, environment=env, risk_engine=risk_engine)
    config = SearchConfig(max_depth=2, max_states=100, max_combo_size=1)
    space_result = run_bfs(root, context, config)

    decision_engine = DecisionEngine()
    ranked = decision_engine.rank(space_result, top_n=10)

    assert len(ranked) > 0
    scores = [c.decision_score for c in ranked]
    assert scores == sorted(scores, reverse=True)


def test_monte_carlo_produces_bounded_distribution():
    registry = build_action_registry()
    root = build_initial_state()
    RiskEngine().evaluate(root)
    actions = [registry.get("deploy_rescue_units"), registry.get("open_shelters")]

    result = run_monte_carlo(root, actions, num_simulations=25, severity=0.5, seed=42)

    assert len(result.final_risks) == 25
    assert all(0.0 <= r <= 1.0 for r in result.final_risks)
    assert result.best_case <= result.average <= result.worst_case
