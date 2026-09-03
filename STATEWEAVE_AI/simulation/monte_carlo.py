"""
simulation/monte_carlo.py

STATEWEAVE :: Monte Carlo Simulation Layer
-----------------------------------------------
Given a chosen sequence of actions (a decision path), repeatedly
re-simulate it under a STOCHASTIC Environment to capture uncertainty
in variables like rainfall increase, road failure, resource
availability, evacuation success, rescue efficiency, and communication
failure.

Each run walks the same action sequence but samples different
environment drift + small per-action execution noise, producing a
distribution of final risk outcomes rather than one deterministic
number.
"""

from __future__ import annotations

import random
import statistics
from dataclasses import dataclass, field
from typing import List

from core.action_engine import Action
from core.consequence_engine import ConsequenceEngine
from core.risk_engine import RiskEngine, risk_category
from core.state_engine import State
from core.transition_engine import Environment, transition


@dataclass
class MonteCarloResult:
    final_risks: List[float] = field(default_factory=list)
    final_populations: List[float] = field(default_factory=list)

    @property
    def best_case(self) -> float:
        return min(self.final_risks) if self.final_risks else 0.0

    @property
    def worst_case(self) -> float:
        return max(self.final_risks) if self.final_risks else 0.0

    @property
    def average(self) -> float:
        return statistics.mean(self.final_risks) if self.final_risks else 0.0

    @property
    def std_dev(self) -> float:
        return statistics.pstdev(self.final_risks) if len(self.final_risks) > 1 else 0.0

    @property
    def expected_risk(self) -> float:
        return self.average

    def probability_high_risk(self, threshold: float = 0.75) -> float:
        if not self.final_risks:
            return 0.0
        count = sum(1 for r in self.final_risks if r >= threshold)
        return count / len(self.final_risks)

    def summary(self) -> dict:
        return {
            "runs": len(self.final_risks),
            "best_case_risk": self.best_case,
            "worst_case_risk": self.worst_case,
            "average_risk": self.average,
            "std_dev_risk": self.std_dev,
            "expected_risk": self.expected_risk,
            "expected_category": risk_category(self.expected_risk),
            "probability_high_risk": self.probability_high_risk(),
            "average_population_at_risk": (
                statistics.mean(self.final_populations) if self.final_populations else 0.0
            ),
        }


def run_monte_carlo(
    root: State,
    action_path: List[Action],
    num_simulations: int = 200,
    severity: float = 0.5,
    seed: int = None,
) -> MonteCarloResult:
    """Re-run `action_path` from `root` `num_simulations` times under a
    stochastic environment, collecting the distribution of final risk.
    """
    risk_engine = RiskEngine()
    consequence_engine = ConsequenceEngine()
    master_rng = random.Random(seed)

    result = MonteCarloResult()

    for _ in range(max(1, num_simulations)):
        run_seed = master_rng.randint(0, 2**31 - 1)
        env = Environment(severity=severity, stochastic=True, rng=random.Random(run_seed))

        state = root
        for action in action_path:
            # small execution-effectiveness noise: with some probability
            # the action underperforms (e.g. evacuation partially fails,
            # rescue units delayed) -- modeled as a partial-strength combo
            effectiveness = env.rng.uniform(0.75, 1.05)
            noisy_action = _scale_action(action, effectiveness)
            state = transition(state, [noisy_action], env)
            consequence_engine.analyze(state, state)  # self-consistent tagging

        breakdown = risk_engine.evaluate(state)
        result.final_risks.append(breakdown.total)
        result.final_populations.append(state.get("population_at_risk"))

    return result


def _scale_action(action: Action, effectiveness: float) -> Action:
    """Return a shallow copy of `action` whose numeric 'amount' param is
    scaled by `effectiveness`, simulating partial success/failure without
    mutating the shared registry action.
    """
    from dataclasses import replace

    params = dict(action.params)
    if "amount" in params and isinstance(params["amount"], (int, float)):
        params["amount"] = params["amount"] * effectiveness
    return replace(action, params=params)
