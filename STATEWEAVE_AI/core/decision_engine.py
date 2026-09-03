"""
core/decision_engine.py

STATEWEAVE CORE :: Decision Intelligence Layer
-----------------------------------------------
Turns a generated state space into a RANKED list of candidate decisions
(root -> non-root state paths), each with:

  * Risk reduction        (root.risk - state.risk)
  * Population protected  (root.population_at_risk - state.population_at_risk)
  * Resource efficiency   (population protected per unit resource spent)
  * Response efficiency   (risk reduction per unit resource spent)
  * Resource cost         (resource spent along the path)
  * Negative consequences (count of negative cascade chains triggered
                            along the path)
  * Decision Score        transparent weighted formula (Section 10)

The top-ranked decision also gets a generated natural-language
explanation built directly from these numbers -- not canned text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from core.state_engine import State
from core.state_space import StateSpaceResult


DEFAULT_SCORE_WEIGHTS = {
    "risk_reduction": 40.0,
    "population_protection": 30.0,
    "resource_efficiency": 15.0,
    "response_efficiency": 15.0,
    "resource_cost_penalty": 20.0,
    "negative_consequence_penalty": 8.0,
}


@dataclass
class DecisionCandidate:
    state: State
    path: List[State]
    risk_reduction: float
    population_protected: float
    resource_cost: float
    resource_efficiency: float
    response_efficiency: float
    negative_consequences: int
    positive_consequences: int
    decision_score: float
    action_sequence: List[str]

    def to_dict(self) -> dict:
        return {
            "state_id": self.state.state_id,
            "action_sequence": self.action_sequence,
            "risk": self.state.risk,
            "risk_category": self.state.meta.get("risk_breakdown", {}).get("category"),
            "risk_reduction": self.risk_reduction,
            "population_protected": self.population_protected,
            "resource_cost": self.resource_cost,
            "resource_efficiency": self.resource_efficiency,
            "response_efficiency": self.response_efficiency,
            "negative_consequences": self.negative_consequences,
            "positive_consequences": self.positive_consequences,
            "decision_score": self.decision_score,
        }


class DecisionEngine:
    def __init__(self, weights: Dict[str, float] = None):
        self.weights = dict(weights) if weights else dict(DEFAULT_SCORE_WEIGHTS)

    def _score_state(self, root: State, state: State, path: List[State]) -> DecisionCandidate:
        risk_reduction = (root.risk or 0.0) - (state.risk or 0.0)
        population_protected = root.get("population_at_risk") - state.get("population_at_risk")
        resource_cost = root.get("resource_budget") - state.get("resource_budget")
        resource_cost = max(resource_cost, 1e-6)  # avoid divide-by-zero

        resource_efficiency = population_protected / resource_cost
        response_efficiency = (risk_reduction * 100.0) / resource_cost

        negative = 0
        positive = 0
        action_sequence: List[str] = []
        for node in path[1:]:  # skip root
            cons = node.meta.get("consequences", {})
            negative += len(cons.get("negative", []))
            positive += len(cons.get("positive", []))
            labels = node.meta.get("action_labels")
            if labels:
                action_sequence.extend(labels)

        # normalize resource_efficiency/response_efficiency into comparable
        # ranges before weighting, using simple bounded transforms
        norm_pop_eff = min(resource_efficiency / 500.0, 1.0)   # ~500 people/unit is "excellent"
        norm_resp_eff = min(max(response_efficiency, 0.0) / 10.0, 1.0)

        score = (
            self.weights["risk_reduction"] * max(risk_reduction, 0.0)
            + self.weights["population_protection"] * (population_protected / max(root.get("population_at_risk"), 1.0))
            + self.weights["resource_efficiency"] * norm_pop_eff
            + self.weights["response_efficiency"] * norm_resp_eff
            - self.weights["resource_cost_penalty"] * min(resource_cost / max(root.get("resource_budget"), 1.0), 1.0)
            - self.weights["negative_consequence_penalty"] * min(negative, 5) / 5.0
        )

        return DecisionCandidate(
            state=state,
            path=path,
            risk_reduction=risk_reduction,
            population_protected=population_protected,
            resource_cost=resource_cost,
            resource_efficiency=resource_efficiency,
            response_efficiency=response_efficiency,
            negative_consequences=negative,
            positive_consequences=positive,
            decision_score=round(score, 2),
            action_sequence=action_sequence,
        )

    def rank(self, result: StateSpaceResult, top_n: int = 10) -> List[DecisionCandidate]:
        root = result.root
        candidates = []
        for state in result.non_dominated_states():
            if state.state_id == root.state_id:
                continue
            path = result.path_to_root(state)
            candidates.append(self._score_state(root, state, path))

        candidates.sort(key=lambda c: c.decision_score, reverse=True)
        return candidates[:top_n]

    def explain(self, candidate: DecisionCandidate) -> List[str]:
        """Generate bullet-point explanation from the *actual numbers*
        of this candidate -- satisfies the "no black-box" requirement.
        """
        bullets = []
        if candidate.risk_reduction > 0:
            bullets.append(f"Reduced overall risk by {candidate.risk_reduction:.1%}")
        if candidate.population_protected > 0:
            bullets.append(f"Protected an estimated {candidate.population_protected:,.0f} additional people")
        if candidate.positive_consequences > 0:
            bullets.append(f"Triggered {candidate.positive_consequences} positive cascading effect(s)")
        if candidate.negative_consequences == 0:
            bullets.append("No negative cascading effects detected")
        else:
            bullets.append(f"Introduced {candidate.negative_consequences} negative cascading effect(s) -- trade-off to weigh")
        bullets.append(f"Resource cost: {candidate.resource_cost:.1f} units "
                        f"({candidate.resource_efficiency:.1f} people protected per unit)")
        return bullets
