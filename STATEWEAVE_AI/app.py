"""
app.py

STATEWEAVE AI — Future-State Decision Intelligence Engine
-----------------------------------------------------------
Main Streamlit entry point. Run with:

    streamlit run app.py

Pages:
  Dashboard | Scenario Builder | State Space Explorer |
  Decision Intelligence | Monte Carlo Analysis | Consequence Analysis |
  Scenario Comparison | Report
"""

from __future__ import annotations

import streamlit as st

from core.risk_engine import RiskEngine
from domains.disaster_response import (
    SAMPLE_SCENARIOS,
    VARIABLE_LABELS,
    build_action_registry,
    build_initial_state,
    get_sample_scenario,
)
from reports.report_generator import generate_report
from simulation.scenario_engine import run_monte_carlo_for_candidate, run_scenario
from visualization.charts import (
    decision_score_chart,
    monte_carlo_distribution_chart,
    population_protection_chart,
    resource_utilization_chart,
    risk_comparison_chart,
    risk_evolution_chart,
)
from visualization.dashboard import inject_global_css, risk_badge, section_header, styled_card
from visualization.state_graph import build_state_space_figure

st.set_page_config(
    page_title="STATEWEAVE AI",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_global_css()

# ----------------------------------------------------------------------
# Session state initialization
# ----------------------------------------------------------------------
if "current_state_vars" not in st.session_state:
    st.session_state.current_state_vars = dict(SAMPLE_SCENARIOS["Chennai Flood"])
if "scenario_name" not in st.session_state:
    st.session_state.scenario_name = "Chennai Flood"
if "run_result" not in st.session_state:
    st.session_state.run_result = None
if "comparison_results" not in st.session_state:
    st.session_state.comparison_results = {}
if "mc_result" not in st.session_state:
    st.session_state.mc_result = None

action_registry = build_action_registry()
risk_engine = RiskEngine()


# ----------------------------------------------------------------------
# Sidebar navigation
# ----------------------------------------------------------------------
st.sidebar.title("🌊 STATEWEAVE AI")
st.sidebar.caption("Explore Possible Futures. Find Better Decisions.")
st.sidebar.markdown("---")

PAGES = [
    "Dashboard",
    "Scenario Builder",
    "State Space Explorer",
    "Decision Intelligence",
    "Monte Carlo Analysis",
    "Consequence Analysis",
    "Scenario Comparison",
    "Report",
]
page = st.sidebar.radio("Navigate", PAGES, label_visibility="collapsed")

st.sidebar.markdown("---")
st.sidebar.subheader("Sample Scenarios")
for name in SAMPLE_SCENARIOS:
    if st.sidebar.button(f"📌 {name}", key=f"sample_{name}", use_container_width=True):
        st.session_state.current_state_vars = dict(SAMPLE_SCENARIOS[name])
        st.session_state.scenario_name = name
        st.session_state.run_result = None
        st.session_state.mc_result = None
        st.rerun()

if st.sidebar.button("🔄 Reset to Defaults", use_container_width=True):
    st.session_state.current_state_vars = dict(SAMPLE_SCENARIOS["Chennai Flood"])
    st.session_state.scenario_name = "Chennai Flood"
    st.session_state.run_result = None
    st.session_state.mc_result = None
    st.rerun()


def get_root_state():
    return build_initial_state(st.session_state.current_state_vars)


# ========================================================================
# PAGE: DASHBOARD
# ========================================================================
if page == "Dashboard":
    section_header("Dashboard", f"Current scenario: {st.session_state.scenario_name}")

    root = get_root_state()
    breakdown = risk_engine.evaluate(root)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Current Risk", f"{breakdown.total:.2f}")
        st.markdown(risk_badge(breakdown.category), unsafe_allow_html=True)
    with col2:
        st.metric("Population at Risk", f"{root.get('population_at_risk'):,.0f}")
    with col3:
        st.metric("Resource Budget", f"{root.get('resource_budget'):.0f}")
    with col4:
        st.metric("Affected Zones", f"{int(root.get('affected_zones'))}")

    st.markdown("###")
    result = st.session_state.run_result

    col5, col6, col7 = st.columns(3)
    with col5:
        st.metric("States Generated", len(result.space_result.all_states) if result else 0)
    with col6:
        if result and result.best_decision:
            st.metric("Best Decision Score", f"{result.best_decision.decision_score:.1f}")
        else:
            st.metric("Best Decision Score", "—")
    with col7:
        if result and result.best_decision:
            st.metric("Expected Risk Reduction", f"{result.best_decision.risk_reduction:.1%}")
        else:
            st.metric("Expected Risk Reduction", "—")

    st.markdown("###")
    if result and result.best_decision:
        best = result.best_decision
        styled_card(
            "🏆 Recommended Decision",
            f"<b>{' + '.join(best.action_sequence) or 'No Action'}</b><br>"
            f"Decision Score: {best.decision_score:.1f} &nbsp;|&nbsp; "
            f"Risk Reduction: {best.risk_reduction:.1%} &nbsp;|&nbsp; "
            f"Population Protected: {best.population_protected:,.0f}",
            accent="#2ecc71",
        )
    else:
        st.info("Go to **Scenario Builder** and click **Generate State Space** to populate the dashboard.")

    st.markdown("#### Primary Risk Drivers")
    for line in risk_engine.explain(breakdown):
        st.markdown(f"- {line}")


# ========================================================================
# PAGE: SCENARIO BUILDER
# ========================================================================
elif page == "Scenario Builder":
    section_header("Scenario Builder", "Configure the current state and generate the future state space.")

    v = st.session_state.current_state_vars
    with st.form("scenario_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            v["population_at_risk"] = st.number_input(
                "Population at Risk", 0, 2_000_000, int(v["population_at_risk"]), step=1000,
                help="Number of people currently in danger zones.")
            v["shelters"] = st.number_input("Shelters", 0, 500, int(v["shelters"]))
            v["rescue_units"] = st.number_input("Rescue Units", 0, 500, int(v["rescue_units"]))
            v["ambulances"] = st.number_input("Ambulances", 0, 500, int(v["ambulances"]))
        with c2:
            v["hospital_capacity"] = st.number_input("Hospital Capacity", 0, 10000, int(v["hospital_capacity"]))
            v["road_availability"] = st.slider("Road Availability", 0.0, 1.0, float(v["road_availability"]))
            v["rainfall"] = st.number_input("Rainfall (mm)", 0, 1000, int(v["rainfall"]))
            v["electricity"] = st.slider("Electricity Availability", 0.0, 1.0, float(v["electricity"]))
        with c3:
            v["water"] = st.slider("Water Availability", 0.0, 1.0, float(v["water"]))
            v["communication"] = st.slider("Communication Availability", 0.0, 1.0, float(v["communication"]))
            v["affected_zones"] = st.number_input("Affected Zones", 0, 100, int(v["affected_zones"]))
            v["time_remaining"] = st.number_input("Time Remaining (hrs)", 0, 200, int(v["time_remaining"]))
        v["resource_budget"] = st.slider("Resource Budget", 10.0, 500.0, float(v["resource_budget"]))

        st.markdown("#### Search Configuration")
        c4, c5, c6, c7 = st.columns(4)
        with c4:
            algorithm = st.selectbox("Algorithm", ["bfs", "dfs", "astar"], help="BFS: broad near-term survey. DFS: deep single-path exploration. A*: optimal risk-minimizing path.")
        with c5:
            depth = st.slider("Simulation Depth", 1, 5, 3)
        with c6:
            max_states = st.slider("Max States", 50, 1000, 300, step=50)
        with c7:
            combo_size = st.selectbox("Max Combo Size", [1, 2], index=1, help="Allow combining up to N actions per step.")

        run_mc = st.checkbox("Also run Monte Carlo simulation on the best decision", value=True)
        mc_runs = st.slider("Monte Carlo Runs", 50, 1000, 200, step=50) if run_mc else 0

        submitted = st.form_submit_button("🚀 Generate State Space", use_container_width=True)

    if submitted:
        st.session_state.current_state_vars = v
        with st.spinner("Generating future state space..."):
            root = build_initial_state(v)
            result = run_scenario(
                root, action_registry,
                algorithm=algorithm, max_depth=depth, max_states=max_states,
                max_combo_size=combo_size, monte_carlo_runs=mc_runs,
            )
        st.session_state.run_result = result
        st.session_state.mc_result = result.monte_carlo
        st.success(f"Generated {len(result.space_result.all_states)} states. See **State Space Explorer** and **Decision Intelligence**.")


# ========================================================================
# PAGE: STATE SPACE EXPLORER
# ========================================================================
elif page == "State Space Explorer":
    section_header("State Space Explorer", "Interactive visualization of the generated future-state tree/graph.")

    result = st.session_state.run_result
    if result is None:
        st.warning("No state space generated yet. Go to **Scenario Builder** first.")
    else:
        highlight = result.astar_path if result.astar_path else (result.best_decision.path if result.best_decision else None)
        fig = build_state_space_figure(result.space_result, highlight_path=highlight)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Node color = risk category (green→red). Node size = population at risk. Highlighted border = best/optimal path.")

        st.markdown("#### Risk Evolution Over Search Depth")
        st.plotly_chart(risk_evolution_chart(result.space_result), use_container_width=True)

        with st.expander("View raw state table"):
            rows = [s.to_dict() for s in result.space_result.all_states]
            st.dataframe(rows, use_container_width=True)


# ========================================================================
# PAGE: DECISION INTELLIGENCE
# ========================================================================
elif page == "Decision Intelligence":
    section_header("Decision Intelligence", "Ranked candidate decisions with transparent explanations.")

    result = st.session_state.run_result
    if result is None:
        st.warning("No state space generated yet. Go to **Scenario Builder** first.")
    else:
        candidates = result.ranked_decisions
        if not candidates:
            st.info("No viable candidate decisions were found for this configuration.")
        else:
            st.plotly_chart(decision_score_chart(candidates), use_container_width=True)

            from core.decision_engine import DecisionEngine
            engine = DecisionEngine()

            for i, c in enumerate(candidates, start=1):
                title = f"#{i}  {' + '.join(c.action_sequence) or 'No Action'}  —  Score {c.decision_score:.1f}"
                with st.expander(title, expanded=(i == 1)):
                    cc1, cc2, cc3, cc4 = st.columns(4)
                    cc1.metric("Risk Reduction", f"{c.risk_reduction:.1%}")
                    cc2.metric("Population Protected", f"{c.population_protected:,.0f}")
                    cc3.metric("Resource Cost", f"{c.resource_cost:.1f}")
                    cc4.metric("Resulting Risk", f"{c.state.risk:.2f}")

                    st.markdown("**Why this decision was recommended:**")
                    for line in engine.explain(c):
                        st.markdown(f"✓ {line}")

                    if i == 1 and st.button("Run Monte Carlo on this decision", key=f"mc_btn_{i}"):
                        root = get_root_state()
                        risk_engine.evaluate(root)
                        with st.spinner("Running Monte Carlo simulation..."):
                            mc = run_monte_carlo_for_candidate(root, c, action_registry, num_simulations=200)
                        st.session_state.mc_result = mc
                        st.success("Monte Carlo complete — see the Monte Carlo Analysis page.")


# ========================================================================
# PAGE: MONTE CARLO ANALYSIS
# ========================================================================
elif page == "Monte Carlo Analysis":
    section_header("Monte Carlo Analysis", "Outcome distributions under uncertainty for the best decision path.")

    mc = st.session_state.mc_result
    if mc is None:
        st.warning("No Monte Carlo results yet. Enable it in **Scenario Builder**, or run it from **Decision Intelligence**.")
    else:
        summary = mc.summary()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Best Case Risk", f"{summary['best_case_risk']:.2f}")
        c2.metric("Worst Case Risk", f"{summary['worst_case_risk']:.2f}")
        c3.metric("Average (Expected) Risk", f"{summary['average_risk']:.2f}")
        c4.metric("P(High Risk ≥0.75)", f"{summary['probability_high_risk']:.1%}")

        st.plotly_chart(monte_carlo_distribution_chart(mc), use_container_width=True)
        st.markdown(
            f"Across **{summary['runs']}** simulated futures, the expected risk category is "
            f"**{summary['expected_category']}**, with a standard deviation of "
            f"**{summary['std_dev_risk']:.3f}**, and an average of "
            f"**{summary['average_population_at_risk']:,.0f}** people remaining at risk."
        )


# ========================================================================
# PAGE: CONSEQUENCE ANALYSIS
# ========================================================================
elif page == "Consequence Analysis":
    section_header("Consequence Analysis", "Cascading effect chains triggered by the recommended decision.")

    result = st.session_state.run_result
    if result is None or result.best_decision is None:
        st.warning("No state space generated yet. Go to **Scenario Builder** first.")
    else:
        path = result.best_decision.path
        for node in path[1:]:
            st.markdown(f"### Step: {node.action}")
            cons = node.meta.get("consequences", {})
            positive = cons.get("positive", [])
            negative = cons.get("negative", [])

            if positive:
                st.markdown("**✅ Positive Cascades**")
                for chain in positive:
                    st.markdown(" → ".join(chain))
            if negative:
                st.markdown("**⚠️ Negative Cascades**")
                for chain in negative:
                    st.markdown(" → ".join(chain))
            if not positive and not negative:
                st.caption("No cascade rules triggered at this step.")
            st.markdown("---")


# ========================================================================
# PAGE: SCENARIO COMPARISON
# ========================================================================
elif page == "Scenario Comparison":
    section_header("Scenario Comparison", "Compare the best decision across multiple sample scenarios.")

    selected = st.multiselect("Select scenarios to compare", list(SAMPLE_SCENARIOS.keys()),
                               default=list(SAMPLE_SCENARIOS.keys())[:3])
    depth = st.slider("Depth for comparison run", 1, 5, 3)

    if st.button("▶ Run Comparison", use_container_width=True):
        results = {}
        with st.spinner("Running scenarios..."):
            for name in selected:
                root = get_sample_scenario(name)
                res = run_scenario(root, action_registry, algorithm="bfs", max_depth=depth, max_states=250)
                results[name] = res
        st.session_state.comparison_results = results

    results = st.session_state.comparison_results
    if results:
        cols = st.columns(len(results))
        best_name, best_score = None, -1e9
        for (name, res), col in zip(results.items(), cols):
            with col:
                st.markdown(f"#### {name}")
                if res.best_decision:
                    st.metric("Risk", f"{res.best_decision.state.risk:.2f}")
                    st.metric("Population Protected", f"{res.best_decision.population_protected:,.0f}")
                    st.metric("Decision Score", f"{res.best_decision.decision_score:.1f}")
                    if res.best_decision.decision_score > best_score:
                        best_score = res.best_decision.decision_score
                        best_name = name
                else:
                    st.info("No viable decision found.")
        if best_name:
            st.success(f"🏆 Best strategy overall: **{best_name}** (Decision Score: {best_score:.1f})")


# ========================================================================
# PAGE: REPORT
# ========================================================================
elif page == "Report":
    section_header("Scenario Report", "Generate a professional Markdown report of the current analysis.")

    result = st.session_state.run_result
    if result is None:
        st.warning("No state space generated yet. Go to **Scenario Builder** first.")
    else:
        report_md = generate_report(result, scenario_name=st.session_state.scenario_name)
        st.download_button(
            "⬇ Download Report (Markdown)",
            data=report_md,
            file_name=f"stateweave_report_{st.session_state.scenario_name.replace(' ', '_')}.md",
            mime="text/markdown",
            use_container_width=True,
        )
        st.markdown(report_md)
