# Data Model: Agentic Materials Discovery Lab

Entities derive from `spec.md` → Key Entities and map 1:1 to Pydantic models in
`src/schemas.py` (validation rules enforce the constitution). The candidate pool and labels
are plain NumPy/pandas structures, not Pydantic, for speed; they never cross agent boundaries
except by id.

## Candidate Pool (internal, non-serialized across agents)

- **MaterialPool**: in-memory structure with:
  - `ids: list[str]` — stable JARVIS ids (`jid`)
  - `features: np.ndarray (n, d)` — Magpie (or fallback) feature matrix; **never contains the
    target column or ehull raw values from the label perspective** (label filtration handled
    in data.py before featurization)
  - `top_set: set[str]` — derived from hidden labels at setup; used ONLY by evaluation
    analysis code, never passed to any agent or surrogate
- Validation: feature matrix has no column named/numerically identical to the label column
  (asserted by the oracle leak test).

## Oracle (internal, privilege boundary)

- **Oracle**: owns `labels: dict[str, float]` privately, plus `budget: int`,
  `revealed: set[str]`.
- State transitions: `unrevealed → revealed` (via `reveal(ids)` only); `revealed` ids rejected
  on re-reveal; attempt beyond budget raises `BudgetExceededError`.
- Invariants (test-enforced): none of `labels` contents reachable via public attrs/methods;
  `reveal` returns only requested ids; budget never goes negative.

## Citation

| Field | Type | Rule |
|---|---|---|
| id | str (lit_NNN) | unique |
| claim | str | verbatim claim text |
| source_title | str | required |
| doi_or_url | HttpUrl/str | MUST resolve to the real cached API response |
| year | int | from response |
| cached_response_id | str | lookup key into cache/lit |

## Hypothesis

| Field | Type | Rule |
|---|---|---|
| id | str (H1, H3...) | unique per run |
| label | Literal["AGENT-GENERATED"] | missing/default → validation error |
| statement | str | — |
| testable_feature_set | list[str] | must be subsets of available features |
| predicted_direction | Literal["positive", "negative"] | — |
| supporting_citation_ids | list[str] | ≥1, must exist in current run's citations |

Verdicts are NOT a Hypothesis field — they live in `AnalysisVerdict.hypothesis_verdicts`
(per-run evidence, not hypothesis identity).

## ExperimentSpec (Planner → Runner)

| Field | Type | Rule |
|---|---|---|
| round | int ≥ 1 | — |
| strategy | Literal["exploit", "explore", "hybrid", "hypothesis_test"] | — |
| batch_ids | list[str] | length ≤ min(batch_size, budget_remaining); all unrevealed |
| rationale | str | non-empty |
| expected_learning | str | non-empty |
| cost | int | == len(batch_ids), ≤ budget_remaining |
| rejected_alternatives | list[{strategy, reason}] | ≥1 item (Planner MUST score ≥2 strategies) |

## RunResult (Runner → Analysis)

| Field | Type | Rule |
|---|---|---|
| batch_ids | list[str] | matches ExperimentSpec.batch_ids |
| true_values | list[float] | from oracle reveal only |
| hits_in_batch | int | count of batch ids in top_set |
| cumulative_hits | int | monotone non-decreasing across rounds of a run |
| budget_remaining | int | ≥ 0; == prior − len(batch_ids) |
| run_id | str | — |
| seed | int | — |

## AnalysisVerdict (Analysis → Planner)

| Field | Type | Rule |
|---|---|---|
| hypothesis_verdicts | list[{id, verdict, evidence}] | evidence non-empty when verdict ≠ inconclusive |
| strategy_recommendation | Optional[Literal["switch_to_explore", "switch_to_hybrid", "switch_to_exploit", "continue"]] | required when any verdict == "refuted" |
| reason | str | required when recommendation ≠ null |

## Handoff (envelope for every inter-agent message)

| Field | Type | Rule |
|---|---|---|
| run_id | str | — |
| round | int | — |
| from_agent | str — Literal of the 7 agent names | — |
| to_agent | str — Literal of the 7 agent names | must be a legal target per workflow edges |
| payload | one of the above payload models (discriminated union) | schema-validated |
| citations | list[str] | every claim in payload must be backed here |
| uncertainty | Optional[Literal["low", "medium", "high"]] | — |

## ResearchRecord (append-only log lines)

| Field | Type | Rule |
|---|---|---|
| timestamp | ISO-8601 str | — |
| agent | str | — |
| run_id / seed | str / int | both required |
| input_hash | str | sha256 of canonical input JSON |
| output | dict | the validated payload |
| citations | list[str] | — |

## relationships

Literature → Citation → Hypothesis (Insight) → ExperimentSpec (Planner) → RunResult (Runner)
→ AnalysisVerdict (Analysis) → next ExperimentSpec; all wrapped by Handoff and mirrored to
ResearchRecord; Safety observes Handoffs and emits approval-gated `ApprovalDecision`
{action, approved: bool, approver: str} for the three consequential action types.
