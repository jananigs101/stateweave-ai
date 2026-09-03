"""
simulation/scenario_engine.py

STATEWEAVE :: Scenario Orchestration Layer
-----------------------------------------------
Ties the whole pipeline together for a single "run":

    Current State
        -> State Space Generator (BFS/DFS/A*)
        -> Decision Engine (ranking + explanation)
        -> best decision path
        -> Monte Carlo simulation of that path

This is the module the Streamlit app calls after the user configures
a scenario and clicks "Generate State Space" / "Run Simulation".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Literal, Optional

from algorithms.astar import optimal_path, run_astar
from algorithms.bfs import run_bfs
from algorithms.dfs import run_dfs
from core.action_engine import ActionRegistry
from core.decision_engine import DecisionCandidate, DecisionEngine
from core.risk_engine import RiskEngine
from core.state_engine import State
from core.state_space import SearchConfig, SearchContext, StateSpaceResult
from core.transition_engine import Environment
from simulation.monte_carlo import MonteCarloResult, run_monte_carlo


SearchAlgorithm = Literal["bfs", "dfs", "astar"]


@dataclass
class ScenarioRunResult:
    root: State
    algorithm: SearchAlgorithm
    space_result: StateSpaceResult
    ranked_decisions: List[DecisionCandidate]
    best_decision: Optional[DecisionCandidate]
    astar_path: Optional[List[State]] = None
    monte_carlo: Optional[MonteCarloResult] = None


def run_scenario(
    root: State,
    action_registry: ActionRegistry,
    algorithm: SearchAlgorithm = "bfs",
    max_depth: int = 3,
    max_states: int = 300,
    max_combo_size: int = 2,
    risk_threshold: Optional[float] = None,
    environment_severity: float = 0.5,
    monte_carlo_runs: int = 0,
) -> ScenarioRunResult:
    """Run the full STATEWEAVE pipeline for one scenario configuration."""

    risk_engine = RiskEngine()
    risk_engine.evaluate(root)  # score the root itself so deltas are meaningful

    environment = Environment(severity=environment_severity, stochastic=False)
    context = SearchContext(action_registry=action_registry, environment=environment, risk_engine=risk_engine)
    config = SearchConfig(
        max_depth=max_depth,
        max_states=max_states,
        max_combo_size=max_combo_size,
        risk_threshold=risk_threshold,
    )

    astar_path = None
    if algorithm == "bfs":
        space_result = run_bfs(root, context, config)
    elif algorithm == "dfs":
        space_result = run_dfs(root, context, config)
    elif algorithm == "astar":
        space_result = run_astar(root, context, config)
        astar_path = optimal_path(space_result)
    else:
        raise ValueError(f"Unknown algorithm: {algorithm}")

    decision_engine = DecisionEngine()
    ranked = decision_engine.rank(space_result, top_n=10)
    best = ranked[0] if ranked else None

    monte_carlo_result = None
    if monte_carlo_runs and best is not None:
        action_path = _actions_for_path(best.path, action_registry)
        if action_path:
            monte_carlo_result = run_monte_carlo(
                root,
                action_path,
                num_simulations=monte_carlo_runs,
                severity=environment_severity,
            )

    return ScenarioRunResult(
        root=root,
        algorithm=algorithm,
        space_result=space_result,
        ranked_decisions=ranked,
        best_decision=best,
        astar_path=astar_path,
        monte_carlo=monte_carlo_result,
    )


def _actions_for_path(path: List[State], action_registry: ActionRegistry):
    """Reconstruct the ordered list of Action objects taken along a
    root->leaf path, for replay inside the Monte Carlo engine.
    """
    actions = []
    for node in path[1:]:
        for name in node.meta.get("applied_actions", []):
            try:
                actions.append(action_registry.get(name))
            except KeyError:
                continue
    return actions


def run_monte_carlo_for_candidate(
    root: State,
    candidate: DecisionCandidate,
    action_registry: ActionRegistry,
    num_simulations: int = 200,
    severity: float = 0.5,
) -> MonteCarloResult:
    action_path = _actions_for_path(candidate.path, action_registry)
    return run_monte_carlo(root, action_path, num_simulations=num_simulations, severity=severity)
