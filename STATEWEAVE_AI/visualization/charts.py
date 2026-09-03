"""
visualization/charts.py

Reusable Plotly chart builders for the Streamlit dashboard:
  - decision score comparison bar chart
  - risk comparison bar chart
  - Monte Carlo outcome distribution histogram
  - resource utilization bar chart
  - population protection comparison chart
  - risk evolution over search depth (line chart)
"""

from __future__ import annotations

from typing import List

import plotly.graph_objects as go

from core.decision_engine import DecisionCandidate
from core.state_space import StateSpaceResult
from simulation.monte_carlo import MonteCarloResult


def decision_score_chart(candidates: List[DecisionCandidate]) -> go.Figure:
    labels = [f"#{i+1}: {' + '.join(c.action_sequence) or 'No Action'}" for i, c in enumerate(candidates)]
    scores = [c.decision_score for c in candidates]
    fig = go.Figure(go.Bar(x=scores, y=labels, orientation="h", marker_color="#3498db"))
    fig.update_layout(
        title="Decision Score Comparison",
        xaxis_title="Decision Score",
        height=max(300, 40 * len(candidates)),
        margin=dict(l=10, r=10, t=40, b=10),
        yaxis=dict(autorange="reversed"),
    )
    return fig


def risk_comparison_chart(candidates: List[DecisionCandidate]) -> go.Figure:
    labels = [f"#{i+1}" for i in range(len(candidates))]
    risks = [c.state.risk for c in candidates]
    colors = ["#e74c3c" if r >= 0.75 else "#e67e22" if r >= 0.55 else "#f1c40f" if r >= 0.30 else "#2ecc71" for r in risks]
    fig = go.Figure(go.Bar(x=labels, y=risks, marker_color=colors))
    fig.update_layout(
        title="Risk Comparison Across Candidate Decisions",
        xaxis_title="Candidate Decision",
        yaxis_title="Risk Score (0-1)",
        yaxis_range=[0, 1],
        height=350,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def monte_carlo_distribution_chart(mc: MonteCarloResult) -> go.Figure:
    fig = go.Figure(go.Histogram(x=mc.final_risks, nbinsx=25, marker_color="#9b59b6"))
    fig.add_vline(x=mc.average, line_dash="dash", line_color="#2c3e50", annotation_text="Average")
    fig.update_layout(
        title="Monte Carlo Outcome Distribution (Final Risk)",
        xaxis_title="Final Risk Score",
        yaxis_title="Number of Simulation Runs",
        height=350,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def resource_utilization_chart(candidates: List[DecisionCandidate]) -> go.Figure:
    labels = [f"#{i+1}" for i in range(len(candidates))]
    costs = [c.resource_cost for c in candidates]
    fig = go.Figure(go.Bar(x=labels, y=costs, marker_color="#1abc9c"))
    fig.update_layout(
        title="Resource Cost by Candidate Decision",
        xaxis_title="Candidate Decision",
        yaxis_title="Resource Units Spent",
        height=350,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def population_protection_chart(candidates: List[DecisionCandidate]) -> go.Figure:
    labels = [f"#{i+1}" for i in range(len(candidates))]
    protected = [c.population_protected for c in candidates]
    fig = go.Figure(go.Bar(x=labels, y=protected, marker_color="#2980b9"))
    fig.update_layout(
        title="Population Protected by Candidate Decision",
        xaxis_title="Candidate Decision",
        yaxis_title="People Protected",
        height=350,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def risk_evolution_chart(space_result: StateSpaceResult) -> go.Figure:
    by_depth: dict = {}
    for state in space_result.all_states:
        by_depth.setdefault(state.depth, []).append(state.risk if state.risk is not None else 0.0)

    depths = sorted(by_depth.keys())
    avg_risk = [sum(by_depth[d]) / len(by_depth[d]) for d in depths]
    min_risk = [min(by_depth[d]) for d in depths]
    max_risk = [max(by_depth[d]) for d in depths]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=depths, y=max_risk, name="Max Risk", line=dict(color="#e74c3c", dash="dot")))
    fig.add_trace(go.Scatter(x=depths, y=avg_risk, name="Average Risk", line=dict(color="#f39c12")))
    fig.add_trace(go.Scatter(x=depths, y=min_risk, name="Min Risk", line=dict(color="#2ecc71", dash="dot")))
    fig.update_layout(
        title="Risk Evolution Across Search Depth",
        xaxis_title="Search Depth",
        yaxis_title="Risk Score (0-1)",
        yaxis_range=[0, 1],
        height=350,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig
