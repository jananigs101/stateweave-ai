# 🌊 STATEWEAVE AI

### Future-State Decision Intelligence Engine

**Tagline:** *Explore Possible Futures. Find Better Decisions.*

---

## 1. Problem Statement

When a disaster unfolds — a flood, a cyclone, a hospital system under
strain — decision-makers must choose interventions (deploy rescue units?
evacuate a zone? open shelters?) under time pressure, with incomplete
information, and with actions that interact and cascade in non-obvious
ways. Most decision-support tools either (a) present raw dashboards
with no forward-looking analysis, or (b) act as opaque "AI recommends X"
black boxes with no explanation.

## 2. Motivation

Good crisis decisions require reasoning about **possible futures**, not
just the present: *if we do X, what happens next, and what happens after
that?* This is fundamentally a **state-space search** problem — the same
family of problem as pathfinding or game-tree search — applied to
real-world consequence modeling, risk scoring, and resource allocation.

## 3. Solution

STATEWEAVE AI treats a crisis scenario as a **state** in a structured
state space. It:

1. Represents the current situation as a typed state object.
2. Generates the realistic interventions available from that state.
3. Simulates the (deterministic, logically-grounded) effect of each
   intervention, plus passive environmental drift.
4. Searches the resulting state space (BFS / DFS / A*) with
   performance-safe pruning.
5. Detects **cascading consequences** — chains of immediate → secondary
   → tertiary → system-level effects — using a transparent rule engine.
6. Scores every reachable state's **risk** from named, weighted factors.
7. Ranks candidate decisions by an explicit, auditable **Decision Score**.
8. Quantifies uncertainty for the top decision via **Monte Carlo**
   simulation.
9. Visualizes the whole tree interactively and explains *why* the top
   recommendation was chosen, in plain language grounded in the actual
   numbers.

## 4. Key Innovation

Most "AI decision tools" jump straight from Action → Result. STATEWEAVE's
**Cascading Consequence Engine** instead exposes the full causal chain
(e.g. *Close Road → Traffic Redistribution → Ambulance Delay → Hospital
Arrival Delay → Emergency Capacity Pressure → Risk Increase*), and its
**Decision Engine** always shows its work — every recommendation is
traceable back to concrete risk-reduction, population-protection, and
resource-cost numbers, never a canned sentence.

## 5. Architecture

```text
STATEWEAVE CORE
       │
       ├── State Representation      (core/state_engine.py)
       ├── Action Generator          (core/action_engine.py)
       ├── Transition Engine         (core/transition_engine.py)
       ├── State Space Generator     (core/state_space.py)
       ├── Search Algorithms         (algorithms/bfs.py, dfs.py, astar.py)
       ├── Cascading Consequence     (core/consequence_engine.py)
       ├── Risk Engine               (core/risk_engine.py)
       ├── Decision Engine           (core/decision_engine.py)
       └── Monte Carlo Simulation    (simulation/monte_carlo.py)

APPLICATION LAYER
       └── Disaster Response         (domains/disaster_response.py)

PRESENTATION LAYER
       ├── Streamlit Dashboard       (app.py)
       ├── State-Space Visualization (visualization/state_graph.py)
       ├── Charts                   (visualization/charts.py)
       └── Report Generator          (reports/report_generator.py)
```

The core engine (`core/`, `algorithms/`, `simulation/`) is entirely
domain-independent — it only knows about generic numeric "state
variables" and "actions." Disaster response is implemented as the first
**application layer** (`domains/disaster_response.py`), so a future
domain (healthcare capacity planning, smart-city traffic response,
infrastructure resilience, etc.) can be added as a sibling module
without touching the core.

## 6. State-Space Methodology

A `State` is a structured, hashable snapshot of scenario variables
(population at risk, shelters, rescue units, road availability, ...).
From any state, the `ActionRegistry` generates the applicable single
actions *and* small combinations of actions (e.g. "Evacuate Zone" +
"Emergency Corridor"). Each action/combination is applied via the
`TransitionEngine`, producing a child state with full provenance
(parent id, action label, depth). States are deduplicated by content
signature (SHA-256 of rounded variables), so identical outcomes reached
via different paths collapse to one node.

## 7. Algorithms

| Algorithm | File | Use case |
|---|---|---|
| **BFS** | `algorithms/bfs.py` | Broad, level-by-level survey of near-term options |
| **DFS** | `algorithms/dfs.py` | Deep exploration of one committed strategy's long-horizon effects |
| **A\*** | `algorithms/astar.py` | Finds the single lowest-risk decision *path*, using `f = g (resource cost spent) + h (current risk as remaining-difficulty estimate)` |

Performance safeguards (Section 21 of the original spec) shared by all
three: state-signature deduplication, configurable max depth, a hard
max-states cap, optional risk-threshold pruning, and post-hoc
**dominance pruning** (a state is dropped from decision-ranking if a
sibling state is at least as good on risk, population protected, *and*
resource budget remaining).

## 8. Cascading Consequence Engine

`core/consequence_engine.py` declares a set of `CascadeRule`s, each with
a trigger condition (a function of parent/child state deltas) and an
ordered chain of textual effect stages, tagged `positive` or `negative`.
For every state transition, the engine checks which rules fired and
attaches the resulting chains to the child state's metadata — so the
"Consequence Analysis" dashboard page and the report can show exactly
which cascades a given decision path triggered, and why.

## 9. Monte Carlo Simulation

`simulation/monte_carlo.py` re-runs a chosen action sequence many times
under a **stochastic** `Environment` (randomized rainfall drift,
infrastructure decay, and per-action effectiveness noise), producing a
distribution of final risk outcomes: best case, worst case, average
(expected risk), standard deviation, and probability of a high-risk
outcome (≥ 0.75).

## 10. Risk Model

`core/risk_engine.py` computes risk as a transparent weighted sum of
seven named factors (population exposure, resource shortage,
infrastructure failure, hospital overload, road inaccessibility,
communication failure, environmental severity), each normalized to
`[0, 1]`. The engine exposes each factor's raw score *and* its weighted
contribution, so `risk_engine.explain()` can report the top risk
drivers in plain language, not just a single opaque number.

## 11. Explainable Decision Engine

`core/decision_engine.py` scores every non-dominated reachable state
against the root using an explicit formula:

```text
Decision Score =
    + w1 * Risk Reduction
    + w2 * Population Protection (relative)
    + w3 * Resource Efficiency (normalized)
    + w4 * Response Efficiency (normalized)
    - w5 * Resource Cost (relative)
    - w6 * Negative Consequence Penalty
```

All weights live in `DEFAULT_SCORE_WEIGHTS` and are trivially tunable.
`DecisionEngine.explain()` turns a candidate's actual computed numbers
into plain-language bullet points — there is no pre-written
recommendation text anywhere in the system.

## 12. Screenshots

*(Add screenshots of the Dashboard, State Space Explorer, and Decision
Intelligence pages here after running the app locally.)*

- `docs/screenshot-dashboard.png`
- `docs/screenshot-state-space.png`
- `docs/screenshot-decisions.png`

## 13. Tech Stack

- Python 3.10+
- Streamlit — interactive dashboard
- NumPy / Pandas — numeric & tabular handling
- NetworkX — graph structure/layout for the state-space tree
- Plotly — interactive charts and graph rendering
- Scikit-learn — available for future statistical extensions
- Pytest — unit testing

No cloud services, databases, Docker, or paid APIs are required — the
entire system runs locally.

## 14. Installation

```bash
python -m venv venv
source venv/bin/activate   # venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## 15. Running

```bash
streamlit run app.py
```

Then open the local URL Streamlit prints (typically `http://localhost:8501`).

## 16. Example Scenario

1. In the sidebar, click **📌 Chennai Flood**.
2. Go to **Scenario Builder**, review the pre-filled parameters, choose
   `algorithm = bfs`, `depth = 3`, and click **Generate State Space**.
3. Visit **State Space Explorer** to see the interactive future-state
   graph.
4. Visit **Decision Intelligence** to see the ranked, explained
   recommendations (e.g. *Evacuate High-Risk Zone + Open Emergency
   Shelters*).
5. Visit **Monte Carlo Analysis** to see the uncertainty distribution
   for the top decision.
6. Visit **Report** to download a full Markdown scenario report.

## 17. Limitations

- Effect relationships are hand-authored, domain-expert-inspired
  heuristics, not calibrated against real historical disaster datasets.
- The explored state space is pruned for performance (max depth / max
  states / dominance pruning), so exhaustive global optimality is not
  guaranteed — A* finds the best path *within the explored frontier*.
- Monte Carlo uncertainty perturbs environment drift and per-action
  effectiveness independently; it does not model correlated,
  compounding rare/systemic events (e.g. simultaneous multi-hazard
  cascades).
- The decision score's weights are a reasonable, transparent default,
  not a normatively "correct" ethical valuation of lives vs. resources
  — they are meant to be reviewed and tuned by domain experts.

## 18. Future Research Directions

- Calibrate transition and risk functions against real disaster-response
  datasets (e.g. historical flood response logs).
- Learn action-effect parameters from data instead of hand-authoring them,
  while keeping the causal *structure* transparent (hybrid
  learned-parameter / rule-based-structure approach).
- Extend the domain-independent core with additional application layers:
  healthcare capacity planning, smart-city traffic incident response,
  infrastructure resilience planning.
- Multi-agent extensions where multiple decision-makers (e.g. different
  agencies) have partially conflicting objectives.
- Replace the current best-first A* heuristic with a learned value
  function while preserving explainability guarantees.

## 19. Academic / Research Significance

STATEWEAVE AI is a concrete, runnable illustration of applying classical
AI state-space search (BFS/DFS/A*), multi-factor risk modeling, Monte
Carlo simulation under uncertainty, and explainable multi-criteria
decision analysis to a socially significant domain (disaster response),
while keeping every computation auditable — a design stance directly
relevant to research on trustworthy, explainable decision-support
systems for high-stakes domains.

## 20. Project Structure

```text
STATEWEAVE_AI/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── core/
│   ├── state_engine.py
│   ├── action_engine.py
│   ├── transition_engine.py
│   ├── state_space.py
│   ├── consequence_engine.py
│   ├── risk_engine.py
│   └── decision_engine.py
├── algorithms/
│   ├── bfs.py
│   ├── dfs.py
│   └── astar.py
├── simulation/
│   ├── monte_carlo.py
│   └── scenario_engine.py
├── domains/
│   └── disaster_response.py
├── visualization/
│   ├── state_graph.py
│   ├── charts.py
│   └── dashboard.py
├── reports/
│   └── report_generator.py
├── data/
│   └── scenarios.json
└── tests/
    ├── test_state_engine.py
    ├── test_transition.py
    ├── test_search.py
    └── test_risk.py
```

## 21. Testing

```bash
pytest tests/ -v
```

20 unit tests cover state creation/hashing, action effects and
transitions, BFS/DFS/A* search correctness (depth limits, max-states
limits, deduplication), risk scoring, decision ranking, and Monte Carlo
output bounds.

## 22. License

MIT License — free to use, modify, and extend for academic or personal
projects. See `LICENSE` (add one matching your institution's / your own
preference if distributing publicly).
