"""
visualization/state_graph.py

Builds an interactive Plotly figure of the generated state-space tree/graph,
using NetworkX for layout. Node color encodes risk level; node size encodes
population at risk; hover text shows the full state summary.
"""

from __future__ import annotations

from typing import Optional

import networkx as nx
import plotly.graph_objects as go

from core.state_space import StateSpaceResult

RISK_COLORS = {
    "LOW": "#2ecc71",
    "MODERATE": "#f1c40f",
    "HIGH": "#e67e22",
    "CRITICAL": "#e74c3c",
}


def _build_networkx_graph(result: StateSpaceResult) -> nx.DiGraph:
    graph = nx.DiGraph()
    for state in result.all_states:
        graph.add_node(state.state_id, state=state)
    for parent_id, children in result.children_of.items():
        for child_id in children:
            graph.add_edge(parent_id, child_id)
    return graph


def build_state_space_figure(result: StateSpaceResult, highlight_path: Optional[list] = None) -> go.Figure:
    graph = _build_networkx_graph(result)

    if len(graph.nodes) == 0:
        return go.Figure()

    try:
        pos = nx.nx_agraph.graphviz_layout(graph, prog="dot")
    except Exception:
        pos = _layered_layout(result)

    highlight_ids = {s.state_id for s in highlight_path} if highlight_path else set()

    edge_x, edge_y = [], []
    for u, v in graph.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(width=1, color="#b0b0b0"),
        hoverinfo="none",
    )

    node_x, node_y, node_color, node_size, node_text, node_line = [], [], [], [], [], []
    for node_id in graph.nodes():
        state = graph.nodes[node_id]["state"]
        x, y = pos[node_id]
        node_x.append(x)
        node_y.append(y)

        category = state.meta.get("risk_breakdown", {}).get("category", "MODERATE")
        node_color.append(RISK_COLORS.get(category, "#95a5a6"))

        pop = state.get("population_at_risk")
        node_size.append(12 + min(pop / 5000.0, 30))

        node_line.append(3 if node_id in highlight_ids else 0.5)

        node_text.append(
            f"State #{state.state_id}<br>"
            f"Action: {state.action}<br>"
            f"Depth: {state.depth}<br>"
            f"Risk: {state.risk:.2f} ({category})<br>"
            f"Population at Risk: {pop:,.0f}<br>"
            f"Resource Budget: {state.get('resource_budget'):.1f}"
        )

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode="markers",
        marker=dict(
            color=node_color, size=node_size,
            line=dict(width=node_line, color="#2c3e50"),
        ),
        text=node_text, hoverinfo="text",
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        showlegend=False,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor="white",
        height=560,
    )
    return fig


def _layered_layout(result: StateSpaceResult) -> dict:
    """Fallback layout (no graphviz dependency needed): places states in
    horizontal layers by depth, spread evenly within each layer.
    """
    by_depth: dict = {}
    for state in result.all_states:
        by_depth.setdefault(state.depth, []).append(state)

    pos = {}
    for depth, states in by_depth.items():
        n = len(states)
        for i, state in enumerate(states):
            x = (i - (n - 1) / 2.0) * 2.0
            y = -depth * 2.0
            pos[state.state_id] = (x, y)
    return pos
