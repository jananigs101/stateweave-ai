"""
core/consequence_engine.py

STATEWEAVE CORE :: Cascading Consequence Engine
-----------------------------------------------
This is one of STATEWEAVE's signature components. Instead of collapsing
an action straight to a single result, it walks a transparent, rule-based
chain of Immediate -> Secondary -> Tertiary -> System-Level effects,
comparing the parent and child state's variables to infer *which*
cascades actually fired for this specific transition.

The engine is rule-based (not generative/black-box): every possible
cascade is declared explicitly below as a CascadeRule with a trigger
condition and a chain of textual effect stages. This keeps the system
auditable, which matters for a decision-support tool.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

from core.state_engine import State


@dataclass
class CascadeRule:
    name: str
    trigger: Callable[[State, State], bool]   # (parent, child) -> bool
    chain: List[str]                          # ordered effect stages
    polarity: str                              # "positive" or "negative"


def _delta(parent: State, child: State, key: str) -> float:
    return child.get(key) - parent.get(key)


# ----------------------------------------------------------------------
# Declarative cascade rules
# ----------------------------------------------------------------------

def _rule_road_closure_cascade(parent: State, child: State) -> bool:
    return _delta(parent, child, "road_availability") < -0.05


def _rule_corridor_cascade(parent: State, child: State) -> bool:
    return _delta(parent, child, "road_availability") > 0.05


def _rule_rescue_deployment_cascade(parent: State, child: State) -> bool:
    return _delta(parent, child, "rescue_units") > 0


def _rule_shelter_cascade(parent: State, child: State) -> bool:
    return _delta(parent, child, "shelters") > 0


def _rule_hospital_pressure_cascade(parent: State, child: State) -> bool:
    population = child.get("population_at_risk")
    capacity = max(child.get("hospital_capacity"), 1.0)
    return (population * 0.02) / capacity > 0.6


def _rule_communication_cascade(parent: State, child: State) -> bool:
    return _delta(parent, child, "communication") > 0.05


def _rule_environmental_worsening_cascade(parent: State, child: State) -> bool:
    return _delta(parent, child, "rainfall") > 5


CASCADE_RULES: List[CascadeRule] = [
    CascadeRule(
        name="road_closure",
        trigger=_rule_road_closure_cascade,
        chain=[
            "Close Road",
            "Traffic Redistribution to Remaining Routes",
            "Ambulance / Rescue Transit Delay",
            "Hospital Arrival Delay",
            "Emergency Capacity Pressure",
            "Overall Risk Increase",
        ],
        polarity="negative",
    ),
    CascadeRule(
        name="emergency_corridor",
        trigger=_rule_corridor_cascade,
        chain=[
            "Emergency Corridor Established",
            "Transit Delay Decreases",
            "Ambulance / Rescue Arrival Time Decreases",
            "Emergency Response Efficiency Increases",
            "Overall Risk Decrease",
        ],
        polarity="positive",
    ),
    CascadeRule(
        name="rescue_deployment",
        trigger=_rule_rescue_deployment_cascade,
        chain=[
            "Rescue Units Deployed",
            "Extraction Capacity Increases",
            "Population at Risk Decreases",
            "Overall Risk Decrease",
        ],
        polarity="positive",
    ),
    CascadeRule(
        name="shelter_expansion",
        trigger=_rule_shelter_cascade,
        chain=[
            "Shelters Opened",
            "Displaced Population Housed",
            "Exposure to Elements Decreases",
            "Population at Risk Decreases",
        ],
        polarity="positive",
    ),
    CascadeRule(
        name="hospital_pressure",
        trigger=_rule_hospital_pressure_cascade,
        chain=[
            "Expected Casualties Approach Hospital Capacity",
            "Hospital Overload Risk Rises",
            "Treatment Delay Risk Rises",
            "Overall Risk Increase",
        ],
        polarity="negative",
    ),
    CascadeRule(
        name="communication_restoration",
        trigger=_rule_communication_cascade,
        chain=[
            "Emergency Communication Established",
            "Coordination Between Units Improves",
            "Response Efficiency Increases",
            "Overall Risk Decrease",
        ],
        polarity="positive",
    ),
    CascadeRule(
        name="environmental_worsening",
        trigger=_rule_environmental_worsening_cascade,
        chain=[
            "Rainfall Intensifies",
            "Flooding Risk Rises",
            "Infrastructure Degrades Faster",
            "Overall Risk Increase",
        ],
        polarity="negative",
    ),
]


@dataclass
class ConsequenceReport:
    fired_rules: List[CascadeRule]

    def positive_chains(self) -> List[List[str]]:
        return [r.chain for r in self.fired_rules if r.polarity == "positive"]

    def negative_chains(self) -> List[List[str]]:
        return [r.chain for r in self.fired_rules if r.polarity == "negative"]

    def to_dict(self) -> dict:
        return {
            "positive": self.positive_chains(),
            "negative": self.negative_chains(),
            "rule_names": [r.name for r in self.fired_rules],
        }


class ConsequenceEngine:
    """Detects which declared cascade rules fired for a parent->child
    transition, and records them onto the child state's metadata.
    """

    def __init__(self, rules: List[CascadeRule] = None):
        self.rules = rules if rules is not None else CASCADE_RULES

    def analyze(self, parent: State, child: State) -> ConsequenceReport:
        fired = [rule for rule in self.rules if rule.trigger(parent, child)]
        report = ConsequenceReport(fired_rules=fired)
        child.meta["consequences"] = report.to_dict()
        return report
