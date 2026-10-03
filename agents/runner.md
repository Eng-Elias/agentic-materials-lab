# Agent Spec: Experiment Runner

- **Decision owned**: Execute the experiment faithfully — nothing else.
- **Tools allowed**: `oracle_reveal` (budget-enforced), `train_surrogate`. No planning, no recommendations.
- **Input**: `ExperimentSpec`.
- **Output schema**: `RunResult`: `{batch_ids (== spec.batch_ids), true_values, hits_in_batch, cumulative_hits, budget_remaining, run_id, seed}`.
- **Rules**:
  - Cannot exceed budget — enforced by Oracle, not by the agent's good will.
  - Must execute exactly the spec's batch_ids; deviation is a contract violation.
  - Has NO access to `recommend_for_validation` or any approval-gated action.
  - true_values come only from `oracle.reveal()` return values.
