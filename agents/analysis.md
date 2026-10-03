# Agent Spec: Analysis Agent

- **Decision owned**: What did we learn, and does it contradict any hypothesis?
- **Tools allowed**: `read_results` (run history + hit rates), baseline curve stats, feature-importance read. No oracle, no planning.
- **Input**: latest `RunResult`, hypotheses, random baseline curve, arm stats.
- **Output schema**: `AnalysisVerdict`: `{hypothesis_verdicts: [{id, supported|refuted|inconclusive, evidence REQUIRED unless inconclusive}], strategy_recommendation ∈ switch_to_explore|switch_to_hybrid|switch_to_exploit|continue|null (REQUIRED when any verdict=refuted), reason (REQUIRED when any verdict=refuted)}`.
- **Rules**:
  - A hypothesis is refuted when the guided arm's hit rate is at or below the random baseline for 2 consecutive rounds; evidence must quote both rates.
  - If a result is surprising (exploit plateau, RMSE spikes), reopen the earlier assumption and say so explicitly.
  - Verdicts carry uncertainty; never overclaim from one round.
