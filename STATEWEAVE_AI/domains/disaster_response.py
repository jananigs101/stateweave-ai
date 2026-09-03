"""
domains/disaster_response.py

STATEWEAVE :: Disaster Response Application Layer
-----------------------------------------------
This is the FIRST application built on top of STATEWEAVE CORE. It defines:

  1. The disaster-response state schema (default values / ranges).
  2. Effect functions for each possible intervention (deploy rescue
     units, open shelters, evacuate a zone, etc). Each effect function
     encodes a *logical* relationship between variables, e.g.:

        Deploy Rescue Units -> rescue_units UP
                             -> population_at_risk DOWN (rescue capacity effect)
                             -> risk DOWN (indirectly, via the risk engine)

  3. An ActionRegistry pre-populated with all disaster-response actions.
  4. Five ready-to-run sample scenarios.

Everything here is domain-specific and deliberately kept OUT of core/,
so a future domain (e.g. healthcare, smart cities) can be added as a
sibling module without touching the core engine.
"""

from __future__ import annotations

from typing import Dict

from core.action_engine import Action, ActionRegistry
from core.state_engine import State, clamp, clamp_nonneg


# ----------------------------------------------------------------------
# 1. STATE SCHEMA / DEFAULTS
# ----------------------------------------------------------------------

DEFAULT_STATE: Dict[str, float] = {
    "population_at_risk": 100_000,
    "shelters": 20,
    "rescue_units": 50,
    "ambulances": 15,
    "hospital_capacity": 500,
    "road_availability": 0.65,
    "rainfall": 180,
    "electricity": 0.80,
    "water": 0.70,
    "communication": 0.85,
    "affected_zones": 6,
    "time_remaining": 24,     # hours
    "resource_budget": 100.0,  # abstract "effort points" for cost accounting
}

VARIABLE_LABELS = {
    "population_at_risk": "Population at Risk",
    "shelters": "Emergency Shelters",
    "rescue_units": "Rescue Units",
    "ambulances": "Ambulances",
    "hospital_capacity": "Hospital Capacity",
    "road_availability": "Road Availability",
    "rainfall": "Rainfall (mm)",
    "electricity": "Electricity Availability",
    "water": "Water Availability",
    "communication": "Communication Availability",
    "affected_zones": "Affected Zones",
    "time_remaining": "Time Remaining (hrs)",
    "resource_budget": "Resource Budget",
}


def build_initial_state(overrides: Dict[str, float] = None) -> State:
    variables = dict(DEFAULT_STATE)
    if overrides:
        variables.update(overrides)
    return State(variables=variables, action="INITIAL_STATE", depth=0)


# ----------------------------------------------------------------------
# 2. EFFECT FUNCTIONS
#    Each: (state, params) -> new State (via state.clone(**deltas))
#    All relationships are explicit and directional -- NOT random.
# ----------------------------------------------------------------------

def fx_deploy_rescue_units(state: State, params: dict) -> State:
    add_units = params.get("amount", 15)
    rescue_units = state.get("rescue_units") + add_units
    # more rescue units -> faster extraction -> population at risk falls
    saved = min(state.get("population_at_risk"), add_units * 300)
    population = clamp_nonneg(state.get("population_at_risk") - saved)
    cost = clamp_nonneg(state.get("resource_budget") - add_units * 0.4)
    return state.clone(
        rescue_units=rescue_units,
        population_at_risk=population,
        resource_budget=cost,
    )


def fx_open_shelters(state: State, params: dict) -> State:
    add_shelters = params.get("amount", 10)
    shelters = state.get("shelters") + add_shelters
    # more shelter capacity -> displaced population is safer -> modest
    # population-at-risk relief (people move from "at risk" to "sheltered")
    relief = min(state.get("population_at_risk"), add_shelters * 800)
    population = clamp_nonneg(state.get("population_at_risk") - relief)
    cost = clamp_nonneg(state.get("resource_budget") - add_shelters * 0.3)
    return state.clone(
        shelters=shelters,
        population_at_risk=population,
        resource_budget=cost,
    )


def fx_evacuate_zone(state: State, params: dict) -> State:
    # Evacuating a zone requires road availability -- if roads are bad,
    # evacuation is only partially effective (logical coupling).
    zones = max(0, state.get("affected_zones") - 1)
    road_factor = state.get("road_availability")
    evac_effectiveness = 0.5 + 0.5 * road_factor  # 0.5..1.0
    saved = state.get("population_at_risk") * 0.15 * evac_effectiveness
    population = clamp_nonneg(state.get("population_at_risk") - saved)
    cost = clamp_nonneg(state.get("resource_budget") - 8)
    return state.clone(
        affected_zones=zones,
        population_at_risk=population,
        resource_budget=cost,
    )


def fx_allocate_ambulances(state: State, params: dict) -> State:
    add = params.get("amount", 10)
    ambulances = state.get("ambulances") + add
    # more ambulances -> faster hospital transfer -> hospital pressure
    # relief modeled via a virtual "capacity headroom" bump
    hospital = state.get("hospital_capacity") + add * 4
    cost = clamp_nonneg(state.get("resource_budget") - add * 0.35)
    return state.clone(
        ambulances=ambulances,
        hospital_capacity=hospital,
        resource_budget=cost,
    )


def fx_open_emergency_hospital_capacity(state: State, params: dict) -> State:
    add = params.get("amount", 200)
    hospital = state.get("hospital_capacity") + add
    cost = clamp_nonneg(state.get("resource_budget") - add * 0.05)
    return state.clone(hospital_capacity=hospital, resource_budget=cost)


def fx_establish_emergency_communication(state: State, params: dict) -> State:
    boost = params.get("amount", 0.2)
    comm = clamp(state.get("communication") + boost)
    # better comms -> better coordination -> road/rescue efficiency edge
    # captured indirectly through the risk engine's communication term
    cost = clamp_nonneg(state.get("resource_budget") - 5)
    return state.clone(communication=comm, resource_budget=cost)


def fx_close_dangerous_roads(state: State, params: dict) -> State:
    # Closing roads improves *safety* of remaining routes but REDUCES
    # overall road availability -- a genuine trade-off, feeding the
    # cascading consequence engine (traffic redistribution -> delay).
    reduction = params.get("amount", 0.15)
    road = clamp(state.get("road_availability") - reduction)
    cost = clamp_nonneg(state.get("resource_budget") - 3)
    return state.clone(road_availability=road, resource_budget=cost)


def fx_emergency_corridor(state: State, params: dict) -> State:
    # Opposite of closing roads: a protected corridor RAISES effective
    # road availability for emergency vehicles.
    boost = params.get("amount", 0.2)
    road = clamp(state.get("road_availability") + boost)
    cost = clamp_nonneg(state.get("resource_budget") - 6)
    return state.clone(road_availability=road, resource_budget=cost)


def fx_redistribute_resources(state: State, params: dict) -> State:
    # Small, broad-based improvement across several logistics variables,
    # at a resource cost -- represents reallocating existing assets
    # rather than deploying new ones.
    road = clamp(state.get("road_availability") + 0.05)
    comm = clamp(state.get("communication") + 0.05)
    water = clamp(state.get("water") + 0.05)
    cost = clamp_nonneg(state.get("resource_budget") - 4)
    return state.clone(
        road_availability=road, communication=comm, water=water, resource_budget=cost
    )


# ----------------------------------------------------------------------
# 3. PRECONDITIONS
# ----------------------------------------------------------------------

def has_budget(min_cost: float):
    def _pre(state: State) -> bool:
        return state.get("resource_budget") >= min_cost
    return _pre


def has_affected_zones(state: State) -> bool:
    return state.get("affected_zones") > 0


# ----------------------------------------------------------------------
# 4. ACTION REGISTRY FOR THIS DOMAIN
# ----------------------------------------------------------------------

def build_action_registry() -> ActionRegistry:
    registry = ActionRegistry()
    registry.register_many([
        Action(
            name="deploy_rescue_units",
            label="Deploy Rescue Units",
            category="Resource",
            resource_cost=0.30,
            effect_fn=fx_deploy_rescue_units,
            params={"amount": 15},
            precondition=has_budget(6),
            description="Send additional rescue teams into affected zones to extract at-risk population.",
        ),
        Action(
            name="open_shelters",
            label="Open Emergency Shelters",
            category="Infrastructure",
            resource_cost=0.25,
            effect_fn=fx_open_shelters,
            params={"amount": 10},
            precondition=has_budget(3),
            description="Open additional emergency shelters to house displaced population.",
        ),
        Action(
            name="evacuate_zone",
            label="Evacuate High-Risk Zone",
            category="Population",
            resource_cost=0.35,
            effect_fn=fx_evacuate_zone,
            precondition=has_affected_zones,
            description="Evacuate the most dangerous remaining zone, effectiveness depends on road availability.",
        ),
        Action(
            name="allocate_ambulances",
            label="Allocate Additional Ambulances",
            category="Medical",
            resource_cost=0.28,
            effect_fn=fx_allocate_ambulances,
            params={"amount": 10},
            precondition=has_budget(4),
            description="Deploy more ambulances, easing hospital transfer bottlenecks.",
        ),
        Action(
            name="open_emergency_hospital_capacity",
            label="Open Emergency Hospital Capacity",
            category="Medical",
            resource_cost=0.20,
            effect_fn=fx_open_emergency_hospital_capacity,
            params={"amount": 200},
            precondition=has_budget(10),
            description="Activate overflow hospital capacity (field hospitals, unused wards).",
        ),
        Action(
            name="establish_emergency_communication",
            label="Establish Emergency Communication",
            category="Infrastructure",
            resource_cost=0.15,
            effect_fn=fx_establish_emergency_communication,
            params={"amount": 0.2},
            precondition=has_budget(5),
            description="Deploy backup communication infrastructure (satellite links, radio relays).",
        ),
        Action(
            name="close_dangerous_roads",
            label="Close Dangerous Roads",
            category="Infrastructure",
            resource_cost=0.10,
            effect_fn=fx_close_dangerous_roads,
            params={"amount": 0.15},
            precondition=has_budget(3),
            description="Close the most hazardous roads to prevent accidents, at the cost of overall access.",
        ),
        Action(
            name="emergency_corridor",
            label="Create Emergency Corridor",
            category="Infrastructure",
            resource_cost=0.18,
            effect_fn=fx_emergency_corridor,
            params={"amount": 0.2},
            precondition=has_budget(6),
            description="Establish a protected corridor reserved for emergency vehicles.",
        ),
        Action(
            name="redistribute_resources",
            label="Redistribute Existing Resources",
            category="Logistics",
            resource_cost=0.12,
            effect_fn=fx_redistribute_resources,
            precondition=has_budget(4),
            description="Reallocate existing logistics assets for broad, low-cost improvement.",
        ),
    ])
    return registry


# ----------------------------------------------------------------------
# 5. SAMPLE SCENARIOS
# ----------------------------------------------------------------------

SAMPLE_SCENARIOS = {
    "Chennai Flood": {
        "population_at_risk": 120_000,
        "shelters": 18,
        "rescue_units": 40,
        "ambulances": 12,
        "hospital_capacity": 450,
        "road_availability": 0.55,
        "rainfall": 210,
        "electricity": 0.65,
        "water": 0.60,
        "communication": 0.70,
        "affected_zones": 8,
        "time_remaining": 20,
        "resource_budget": 100.0,
    },
    "Cyclone Emergency": {
        "population_at_risk": 200_000,
        "shelters": 25,
        "rescue_units": 60,
        "ambulances": 20,
        "hospital_capacity": 600,
        "road_availability": 0.40,
        "rainfall": 260,
        "electricity": 0.45,
        "water": 0.55,
        "communication": 0.50,
        "affected_zones": 12,
        "time_remaining": 16,
        "resource_budget": 120.0,
    },
    "Urban Flood": {
        "population_at_risk": 75_000,
        "shelters": 22,
        "rescue_units": 35,
        "ambulances": 14,
        "hospital_capacity": 400,
        "road_availability": 0.70,
        "rainfall": 140,
        "electricity": 0.80,
        "water": 0.75,
        "communication": 0.85,
        "affected_zones": 5,
        "time_remaining": 28,
        "resource_budget": 90.0,
    },
    "Hospital Emergency": {
        "population_at_risk": 30_000,
        "shelters": 10,
        "rescue_units": 20,
        "ambulances": 8,
        "hospital_capacity": 150,
        "road_availability": 0.85,
        "rainfall": 20,
        "electricity": 0.90,
        "water": 0.90,
        "communication": 0.92,
        "affected_zones": 2,
        "time_remaining": 12,
        "resource_budget": 70.0,
    },
    "Infrastructure Failure": {
        "population_at_risk": 90_000,
        "shelters": 15,
        "rescue_units": 30,
        "ambulances": 10,
        "hospital_capacity": 350,
        "road_availability": 0.30,
        "rainfall": 60,
        "electricity": 0.25,
        "water": 0.35,
        "communication": 0.30,
        "affected_zones": 9,
        "time_remaining": 30,
        "resource_budget": 110.0,
    },
}


def get_sample_scenario(name: str) -> State:
    if name not in SAMPLE_SCENARIOS:
        raise KeyError(f"Unknown sample scenario: {name}")
    return build_initial_state(SAMPLE_SCENARIOS[name])
