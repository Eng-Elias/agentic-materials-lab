from typing import Literal, Optional, Union

from pydantic import BaseModel, Field, model_validator

AGENTS = ("literature", "insight", "planner", "runner", "analysis", "record", "safety", "scientist")
STRATEGY = Literal["exploit", "explore", "hybrid", "hypothesis_test"]


class Citation(BaseModel):
    model_config = {"extra": "forbid"}
    id: str
    claim: str = Field(min_length=1)
    source_title: str = Field(min_length=1)
    doi_or_url: str = Field(min_length=1)
    year: int
    cached_response_id: str


class LiteratureClaims(BaseModel):
    model_config = {"extra": "forbid"}
    claims: list[Citation] = Field(min_length=1)


class Hypothesis(BaseModel):
    model_config = {"extra": "forbid"}
    id: str
    label: Literal["AGENT-GENERATED"]
    statement: str = Field(min_length=1)
    testable_feature_set: list[str] = Field(min_length=1)
    predicted_direction: Literal["positive", "negative"]
    supporting_citation_ids: list[str] = Field(min_length=1)


class InsightHypotheses(BaseModel):
    model_config = {"extra": "forbid"}
    hypotheses: list[Hypothesis] = Field(min_length=1)


class RejectedAlternative(BaseModel):
    model_config = {"extra": "forbid"}
    strategy: STRATEGY
    reason: str = Field(min_length=1)


class ExperimentSpec(BaseModel):
    model_config = {"extra": "forbid"}
    round: int = Field(ge=1)
    strategy: STRATEGY
    batch_ids: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1)
    expected_learning: str = Field(min_length=1)
    cost: int = Field(ge=1)
    rejected_alternatives: list[RejectedAlternative] = Field(min_length=1)

    @model_validator(mode="after")
    def cost_matches_batch(self):
        if self.cost != len(self.batch_ids):
            raise ValueError(f"cost ({self.cost}) must equal len(batch_ids) ({len(self.batch_ids)})")
        return self


class RunResult(BaseModel):
    model_config = {"extra": "forbid"}
    batch_ids: list[str]
    true_values: list[float]
    hits_in_batch: int = Field(ge=0)
    cumulative_hits: int = Field(ge=0)
    budget_remaining: int = Field(ge=0)
    run_id: str
    seed: int


class HypothesisVerdict(BaseModel):
    model_config = {"extra": "forbid"}
    id: str
    verdict: Literal["supported", "refuted", "inconclusive"]
    evidence: Optional[str] = None

    @model_validator(mode="after")
    def evidence_required_unless_inconclusive(self):
        if self.verdict != "inconclusive" and not (self.evidence or "").strip():
            raise ValueError("evidence is required when verdict is not inconclusive")
        return self


class AnalysisVerdict(BaseModel):
    model_config = {"extra": "forbid"}
    hypothesis_verdicts: list[HypothesisVerdict]
    strategy_recommendation: Optional[
        Literal["switch_to_explore", "switch_to_hybrid", "switch_to_exploit", "continue"]
    ] = None
    reason: Optional[str] = None

    @model_validator(mode="after")
    def refutation_requires_recommendation(self):
        if any(v.verdict == "refuted" for v in self.hypothesis_verdicts):
            if not self.strategy_recommendation:
                raise ValueError("a refuted verdict requires strategy_recommendation")
            if not (self.reason or "").strip():
                raise ValueError("a refuted verdict requires a reason")
        return self


class ApprovalRequest(BaseModel):
    model_config = {"extra": "forbid"}
    action: Literal["recommend_for_validation", "budget_increase", "report_uncited_claim"]
    justification: str = Field(min_length=1)


class ApprovalDecision(BaseModel):
    model_config = {"extra": "forbid"}
    action: Literal["recommend_for_validation", "budget_increase", "report_uncited_claim"]
    approved: bool
    approver: str = Field(min_length=1)


class Handoff(BaseModel):
    model_config = {"extra": "forbid"}
    run_id: str = Field(min_length=1)
    round: int = Field(ge=0)
    from_agent: Literal[*AGENTS]
    to_agent: Literal[*AGENTS]
    payload: Union[
        LiteratureClaims,
        InsightHypotheses,
        ExperimentSpec,
        RunResult,
        AnalysisVerdict,
        ApprovalRequest,
        ApprovalDecision,
    ]
    citations: list[str] = []
    uncertainty: Optional[Literal["low", "medium", "high"]] = None
