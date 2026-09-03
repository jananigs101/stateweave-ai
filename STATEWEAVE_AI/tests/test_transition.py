import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.transition_engine import Environment, transition
from domains.disaster_response import build_action_registry, build_initial_state


def test_deploy_rescue_units_reduces_population_at_risk():
    root = build_initial_state()
    registry = build_action_registry()
    action = registry.get("deploy_rescue_units")
    env = Environment(severity=0.0, stochastic=False)

    child = transition(root, [action], env)

    assert child.get("population_at_risk") < root.get("population_at_risk")
    assert child.get("rescue_units") > root.get("rescue_units")
    assert child.parent_id == root.state_id
    assert child.depth == root.depth + 1


def test_close_roads_reduces_availability_and_corridor_increases_it():
    root = build_initial_state()
    registry = build_action_registry()
    env = Environment(severity=0.0, stochastic=False)

    closed = transition(root, [registry.get("close_dangerous_roads")], env)
    assert closed.get("road_availability") < root.get("road_availability")

    corridor = transition(root, [registry.get("emergency_corridor")], env)
    assert corridor.get("road_availability") > root.get("road_availability")


def test_environment_drift_increases_rainfall_over_time():
    root = build_initial_state()
    env = Environment(severity=0.8, stochastic=False)
    drifted = env.drift(root)
    assert drifted.get("rainfall") > root.get("rainfall")
    assert drifted.get("time_remaining") == root.get("time_remaining") - 1


def test_combo_actions_apply_sequentially():
    root = build_initial_state()
    registry = build_action_registry()
    env = Environment(severity=0.0, stochastic=False)

    combo = [registry.get("deploy_rescue_units"), registry.get("open_shelters")]
    child = transition(root, combo, env)

    assert child.get("rescue_units") > root.get("rescue_units")
    assert child.get("shelters") > root.get("shelters")
    assert "Deploy Rescue Units" in child.action
    assert "Open Emergency Shelters" in child.action
