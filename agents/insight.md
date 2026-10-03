# Agent Spec: Insight Agent

- **Decision owned**: Which hypotheses are worth testing?
- **Tools allowed**: `read_stats` (dataset summary stats ONLY), `read_lit` (Literature output). No oracle, no label access.
- **Input**: `LiteratureClaims`, available feature names, top-set fraction.
- **Output schema**: `InsightHypotheses`: exactly 3 hypotheses, each `{id, label: AGENT-GENERATED, statement, testable_feature_set (⊆ available features), predicted_direction ∈ positive|negative, supporting_citation_ids (≥1)}`.
- **Rules**:
  - All hypotheses are machine-speculation and MUST be labeled AGENT-GENERATED — unlabeled output fails schema validation and is discarded.
  - Each hypothesis must cite at least one literature claim; unsupported priors are not allowed.
  - Hypotheses must be falsifiable against the surrogate's feature set.
