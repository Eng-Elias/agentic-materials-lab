# Agent Spec: Experiment Planner

- **Decision owned**: Which experiment to run next, given the budget.
- **Tools allowed**: `query_surrogate` (predictions + uncertainty), `read_budget`. No oracle access.
- **Input**: current hypotheses, budget remaining, surrogate state, prior `RunResult`s, `AnalysisVerdict`s.
- **Output schema**: `ExperimentSpec`: `{round (≥1), strategy ∈ exploit|explore|hybrid|hypothesis_test, batch_ids (min 1), rationale, expected_learning, cost == len(batch_ids), rejected_alternatives (≥1 item {strategy, reason})}`.
- **Rules**:
  - MUST evaluate at least 2 candidate strategies each round on expected learning, feasibility, and cost; the rejected one(s) are recorded with reasons.
  - Batch cost must equal len(batch_ids) and fit remaining budget; over-budget specs are schema/permission errors.
  - Must honor the latest Analysis verdict: a `switch_to_*` recommendation changes the chosen strategy next round unless explicitly argued otherwise (logged).
  - Deterministic scoring inputs are provided by the surrounding harness (`experiments/run_agentic.py`); the agent decides and justifies, the harness verifies.
