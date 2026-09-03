"""
core/risk_engine.py

STATEWEAVE CORE :: Risk Analysis Layer
-----------------------------------------------
Computes a transparent, explainable risk score in [0, 1] for a given
State, from named, weighted factors. Every factor and its contribution
is retained so the UI / report can show "why the risk is what it is",
satisfying the explainability requirement.

Risk factors (weights configurable, default sums to 1.0):
    population_exposure      - how much of the population is at risk,
                                relative to a reference scale
    resource_shortage        - shortfall of rescue/shelter/ambulance/
                                hospital capacity vs population needs
    infrastructure_failure   - inverse of road/electricity/water
    hospital_overload        - population vs hospital_capacity ratio
    road_inaccessibility     - inverse of road_availability
    communication_failure    - inverse of communication
    environmental_severity   - normalized rainfall intensity
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from core.state_engine import State, clamp


DEFAULT_WEIGHTS: Dict[str, float] = {
    "population_exposure": 0.22,
    "resource_shortage": 0.18,
    "infrastructure_failure": 0.15,
    "hospital_overload": 0.15,
    "road_inaccessibility": 0.12,
    "communication_failure": 0.08,
    "environmental_severity": 0.10,
}

# Reference scales used to normalize raw quantities into [0, 1].
REFERENCE_POPULATION = 250_000
REFERENCE_RAINFALL = 300.0  # mm, treated as "extreme" ceiling


RISK_CATEGORY_THRESHOLDS = [
    (0.30, "LOW"),
    (0.55, "MODERATE"),
    (0.75, "HIGH"),
    (1.01, "CRITICAL"),
]


def risk_category(score: float) -> str:
    for threshold, label in RISK_CATEGORY_THRESHOLDS:
        if score < threshold:
            return label
    return "CRITICAL"


@dataclass
class RiskBreakdown:
    total: float
    category: str
    factors: Dict[str, float] = field(default_factory=dict)          # raw 0..1 sub-scores
    contributions: Dict[str, float] = field(default_factory=dict)    # weighted contributions
    weights: Dict[str, float] = field(default_factory=dict)

    def top_contributors(self, n: int = 3) -> List[Tuple[str, float]]:
        return sorted(self.contributions.items(), key=lambda kv: kv[1], reverse=True)[:n]

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "category": self.category,
            "factors": self.factors,
            "contributions": self.contributions,
            "weights": self.weights,
        }


class RiskEngine:
    """Transparent, weighted, multi-factor risk scoring."""

    def __init__(self, weights: Dict[str, float] = None):
        self.weights = dict(weights) if weights else dict(DEFAULT_WEIGHTS)

    # ------------------------------------------------------------------
    # Individual factor calculations (each returns a value in [0, 1])
    # ------------------------------------------------------------------
    @staticmethod
    def _population_exposure(state: State) -> float:
        return clamp(state.get("population_at_risk") / REFERENCE_POPULATION)

    @staticmethod
    def _resource_shortage(state: State) -> float:
        population = max(state.get("population_at_risk"), 1.0)
        # "need" scales with population; compare to what's actually available
        rescue_ratio = state.get("rescue_units") / (population / 2000.0 + 1e-6)
        shelter_ratio = state.get("shelters") / (population / 5000.0 + 1e-6)
        ambulance_ratio = state.get("ambulances") / (population / 8000.0 + 1e-6)

        # ratio >= 1 means "adequately resourced" -> shortage 0
        rescue_shortage = clamp(1.0 - rescue_ratio)
        shelter_shortage = clamp(1.0 - shelter_ratio)
        ambulance_shortage = clamp(1.0 - ambulance_ratio)

        return clamp((rescue_shortage + shelter_shortage + ambulance_shortage) / 3.0)

    @staticmethod
    def _infrastructure_failure(state: State) -> float:
        road = state.get("road_availability")
        elec = state.get("electricity")
        water = state.get("water")
        avg_health = (road + elec + water) / 3.0
        return clamp(1.0 - avg_health)

    @staticmethod
    def _hospital_overload(state: State) -> float:
        population = state.get("population_at_risk")
        capacity = max(state.get("hospital_capacity"), 1.0)
        # assume ~2% of at-risk population may need hospital care
        expected_need = population * 0.02
        overload_ratio = expected_need / capacity
        return clamp(overload_ratio)

    @staticmethod
    def _road_inaccessibility(state: State) -> float:
        return clamp(1.0 - state.get("road_availability"))

    @staticmethod
    def _communication_failure(state: State) -> float:
        return clamp(1.0 - state.get("communication"))

    @staticmethod
    def _environmental_severity(state: State) -> float:
        return clamp(state.get("rainfall") / REFERENCE_RAINFALL)

    # ------------------------------------------------------------------
    def evaluate(self, state: State) -> RiskBreakdown:
        factors = {
            "population_exposure": self._population_exposure(state),
            "resource_shortage": self._resource_shortage(state),
            "infrastructure_failure": self._infrastructure_failure(state),
            "hospital_overload": self._hospital_overload(state),
            "road_inaccessibility": self._road_inaccessibility(state),
            "communication_failure": self._communication_failure(state),
            "environmental_severity": self._environmental_severity(state),
        }

        contributions = {
            key: factors[key] * self.weights.get(key, 0.0) for key in factors
        }
        total = clamp(sum(contributions.values()))
        category = risk_category(total)

        breakdown = RiskBreakdown(
            total=total,
            category=category,
            factors=factors,
            contributions=contributions,
            weights=dict(self.weights),
        )

        # cache on the state itself so downstream engines don't recompute
        state.risk = total
        state.meta["risk_breakdown"] = breakdown.to_dict()
        return breakdown

    def explain(self, breakdown: RiskBreakdown, n: int = 3) -> List[str]:
        """Human-readable bullet points explaining the dominant risk drivers."""
        labels = {
            "population_exposure": "High population exposure",
            "resource_shortage": "Insufficient rescue/shelter/ambulance resources",
            "infrastructure_failure": "Degraded road/electricity/water infrastructure",
            "hospital_overload": "Hospital capacity under pressure",
            "road_inaccessibility": "Limited road accessibility",
            "communication_failure": "Communication network degraded",
            "environmental_severity": "Severe environmental conditions (rainfall)",
        }
        top = breakdown.top_contributors(n)
        return [f"{labels.get(k, k)} (contributes {v:.1%} of total risk)" for k, v in top if v > 0.001]
