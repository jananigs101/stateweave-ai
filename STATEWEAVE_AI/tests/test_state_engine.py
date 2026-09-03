import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.state_engine import State, clamp, clamp_nonneg
from domains.disaster_response import build_initial_state


def test_state_creation_defaults():
    state = build_initial_state()
    assert state.get("population_at_risk") == 100_000
    assert state.depth == 0
    assert state.parent_id is None
    assert state.action == "INITIAL_STATE"


def test_state_signature_equal_for_identical_variables():
    s1 = State(variables={"a": 1.0, "b": 2.0})
    s2 = State(variables={"b": 2.0, "a": 1.0})
    assert s1.signature() == s2.signature()
    assert s1 == s2


def test_state_signature_differs_for_different_variables():
    s1 = State(variables={"a": 1.0})
    s2 = State(variables={"a": 2.0})
    assert s1.signature() != s2.signature()


def test_clone_produces_independent_state_with_overrides():
    s1 = State(variables={"a": 1.0, "b": 2.0})
    s2 = s1.clone(a=5.0)
    assert s2.get("a") == 5.0
    assert s2.get("b") == 2.0
    assert s1.get("a") == 1.0  # original untouched
    assert s2.state_id != s1.state_id


def test_clamp_bounds_values():
    assert clamp(1.5) == 1.0
    assert clamp(-0.5) == 0.0
    assert clamp(0.5) == 0.5


def test_clamp_nonneg():
    assert clamp_nonneg(-5) == 0.0
    assert clamp_nonneg(5) == 5.0
