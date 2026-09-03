"""
reports/report_generator.py

Generates a professional Markdown scenario analysis report from a
ScenarioRunResult, suitable for download from the dashboard's Report page.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from core.decision_engine import DecisionCandidate
from core.risk_engine import RiskEngine
from domains.disaster_response import VARIABLE_LABELS
from simulation.scenario_engine import ScenarioRunResult


def _fmt_state_table(state) -> str:
    lines = ["| Variable | Value |", "|---|---|"]
    for key, value in state.variables.items():
        label = VARIABLE_LABELS.get(key, key.replace("_", " ").title())
        if isinstance(value, float):
            lines.append(f"| {label} | {value:,.2f} |")
        else:
            lines.append(f"| {label} | {value} |")
    return "\n".join(lines)


def generate_report(result: ScenarioRunResult, scenario_name: str = "Custom Scenario") -> str:
    root = result.root
    best: Optional[DecisionCandidate] = result.best_decision
    risk_engine = RiskEngine()
    breakdown = risk_engine.evaluate(root)
    root_explanation = risk_engine.explain(breakdown)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    md = []
    md.append(f"# STATEWEAVE AI — Scenario Analysis Report")
    md.append(f"**Scenario:** {scenario_name}  ")
    md.append(f"**Generated:** {generated_at}  ")
    md.append(f"**Search Algorithm:** {result.algorithm.upper()}  ")
    md.append("")
    md.append("## 1. Current State Summary")
    md.append(_fmt_state_table(root))
    md.append("")
    md.append(f"**Initial Risk Score:** {root.risk:.3f} ({breakdown.category})")
    md.append("")
    md.append("**Primary Risk Drivers:**")
    for line in root_explanation:
        md.append(f"- {line}")
    md.append("")

    md.append("## 2. State Space Exploration")
    md.append(f"- Total states generated: **{len(result.space_result.all_states)}**")
    md.append(f"- Non-dominated candidate states: **{len(result.space_result.non_dominated_states())}**")
    md.append(f"- Maximum depth explored: **{max((s.depth for s in result.space_result.all_states), default=0)}**")
    md.append("")

    md.append("## 3. Ranked Decisions")
    if result.ranked_decisions:
        md.append("| Rank | Actions | Decision Score | Risk Reduction | Population Protected | Resource Cost |")
        md.append("|---|---|---|---|---|---|")
        for i, c in enumerate(result.ranked_decisions, start=1):
            actions = " + ".join(c.action_sequence) if c.action_sequence else "-"
            md.append(
                f"| {i} | {actions} | {c.decision_score:.1f} | {c.risk_reduction:.1%} | "
                f"{c.population_protected:,.0f} | {c.resource_cost:.1f} |"
            )
    else:
        md.append("_No viable decisions were found for this configuration._")
    md.append("")

    if best is not None:
        md.append("## 4. Recommended Decision")
        md.append(f"**{' + '.join(best.action_sequence) if best.action_sequence else 'No Action'}**")
        md.append("")
        md.append(f"- Decision Score: **{best.decision_score:.1f}**")
        md.append(f"- Resulting Risk: **{best.state.risk:.3f}** "
                   f"({best.state.meta.get('risk_breakdown', {}).get('category')})")
        md.append(f"- Risk Reduction: **{best.risk_reduction:.1%}**")
        md.append(f"- Population Protected: **{best.population_protected:,.0f}**")
        md.append(f"- Resource Cost: **{best.resource_cost:.1f} units**")
        md.append("")
        md.append("### Why This Decision Was Recommended")
        from core.decision_engine import DecisionEngine
        for line in DecisionEngine().explain(best):
            md.append(f"- {line}")
        md.append("")

    if result.monte_carlo is not None:
        summary = result.monte_carlo.summary()
        md.append("## 5. Monte Carlo Uncertainty Analysis")
        md.append(f"- Simulation runs: **{summary['runs']}**")
        md.append(f"- Best-case risk: **{summary['best_case_risk']:.3f}**")
        md.append(f"- Worst-case risk: **{summary['worst_case_risk']:.3f}**")
        md.append(f"- Average (expected) risk: **{summary['average_risk']:.3f}** "
                   f"({summary['expected_category']})")
        md.append(f"- Standard deviation: **{summary['std_dev_risk']:.3f}**")
        md.append(f"- Probability of high-risk outcome (>= 0.75): **{summary['probability_high_risk']:.1%}**")
        md.append("")

    md.append("## 6. Limitations")
    md.append(
        "- Effects are modeled with domain-expert-inspired heuristic relationships, "
        "not calibrated against real historical disaster data.\n"
        "- The state space is pruned (max depth / max states / dominance pruning) for "
        "performance, so exhaustive optimality is not guaranteed beyond the explored frontier.\n"
        "- Monte Carlo uncertainty only perturbs the environment and action effectiveness; "
        "it does not model correlated, compounding rare events."
    )
    md.append("")
    md.append("---")
    md.append("*Generated by STATEWEAVE AI — Future-State Decision Intelligence Engine*")

    return "\n".join(md)
