import json

import pytest
from pydantic import ValidationError

from src.record import ResearchRecord, input_hash
from src.schemas import (
    AnalysisVerdict,
    Citation,
    ExperimentSpec,
    Handoff,
    Hypothesis,
    HypothesisVerdict,
    LiteratureClaims,
    RunResult,
)

GOOD_CITATION = {
    "id": "lit_001",
    "claim": "Electronegativity difference correlates with band gap.",
    "source_title": "Machine-learning prediction of band gaps",
    "doi_or_url": "https://doi.org/10.0000/example",
    "year": 2021,
    "cached_response_id": "openalex:W123456",
}

GOOD_HYPOTHESIS = {
    "id": "H1",
    "label": "AGENT-GENERATED",
    "statement": "Electronegativity difference correlates positively with band gap.",
    "testable_feature_set": ["X_mean", "X_std"],
    "predicted_direction": "positive",
    "supporting_citation_ids": ["lit_001"],
}

GOOD_SPEC = {
    "round": 2,
    "strategy": "hybrid",
    "batch_ids": ["JVASP-1", "JVASP-2"],
    "rationale": "highest expected in-window information per unit cost",
    "expected_learning": "reduce RMSE near window edge",
    "cost": 2,
    "rejected_alternatives": [
        {"strategy": "exploit", "reason": "last round's hit rate dropped below random"}
    ],
}

GOOD_RUN = {
    "batch_ids": ["JVASP-1", "JVASP-2"],
    "true_values": [1.45, 1.62],
    "hits_in_batch": 2,
    "cumulative_hits": 7,
    "budget_remaining": 100,
    "run_id": "2026-10-04-r02",
    "seed": 3,
}


def test_citation_valid():
    Citation(**GOOD_CITATION)


def test_citation_rejects_empty_claim():
    with pytest.raises(ValidationError):
        Citation(**{**GOOD_CITATION, "claim": ""})


def test_hypothesis_valid():
    Hypothesis(**GOOD_HYPOTHESIS)


def test_hypothesis_without_label_rejected():
    bad = {k: v for k, v in GOOD_HYPOTHESIS.items() if k != "label"}
    with pytest.raises(ValidationError):
        Hypothesis(**bad)


def test_hypothesis_wrong_label_rejected():
    with pytest.raises(ValidationError):
        Hypothesis(**{**GOOD_HYPOTHESIS, "label": "AUTHOR-STATED"})


def test_hypothesis_requires_citations():
    with pytest.raises(ValidationError):
        Hypothesis(**{**GOOD_HYPOTHESIS, "supporting_citation_ids": []})


def test_experiment_spec_valid():
    ExperimentSpec(**GOOD_SPEC)


def test_experiment_spec_rejects_no_rejected_alternatives():
    with pytest.raises(ValidationError):
        ExperimentSpec(**{**GOOD_SPEC, "rejected_alternatives": []})


def test_experiment_spec_cost_must_match_batch():
    with pytest.raises(ValidationError):
        ExperimentSpec(**{**GOOD_SPEC, "cost": 5})


def test_experiment_spec_unknown_strategy_rejected():
    with pytest.raises(ValidationError):
        ExperimentSpec(**{**GOOD_SPEC, "strategy": "yolo"})


def test_run_result_valid():
    RunResult(**GOOD_RUN)


def test_analysis_verdict_refuted_needs_evidence_and_recommendation():
    refuted_no_evidence = {"id": "H1", "verdict": "refuted"}
    with pytest.raises(ValidationError):
        HypothesisVerdict(**refuted_no_evidence)
    with pytest.raises(ValidationError):
        AnalysisVerdict(hypothesis_verdicts=[{"id": "H1", "verdict": "refuted", "evidence": "rate=0.02"}])
    ok = AnalysisVerdict(
        hypothesis_verdicts=[{"id": "H1", "verdict": "refuted", "evidence": "hit rate 0.02 < random"}],
        strategy_recommendation="switch_to_hybrid",
        reason="two consecutive rounds below random",
    )
    assert ok.strategy_recommendation == "switch_to_hybrid"


def test_inconclusive_needs_no_evidence():
    HypothesisVerdict(id="H2", verdict="inconclusive")


def test_handoff_example_from_plan_validates():
    handoff = {
        "run_id": "2026-10-03-r03",
        "round": 3,
        "from": "analysis_agent",
        "to": "planner",
        "payload": {
            "hypothesis_verdicts": [{"id": "H1", "verdict": "refuted", "evidence": "..."}],
            "strategy_recommendation": "switch_to_explore",
            "reason": "Greedy hit rate fell below random in last 2 rounds",
        },
        "citations": ["lit_004"],
        "uncertainty": "medium",
    }
    adapted = {k: v for k, v in handoff.items() if k not in ("from", "to")}
    adapted["from_agent"] = handoff["from"].replace("_agent", "")
    adapted["to_agent"] = handoff["to"].replace("_agent", "")
    h = Handoff.model_validate(adapted)
    assert h.payload.strategy_recommendation == "switch_to_explore"


def test_malformed_handoffs_rejected():
    base = {
        "run_id": "r1",
        "round": 1,
        "from_agent": "planner",
        "to_agent": "runner",
        "payload": GOOD_SPEC,
        "citations": [],
    }
    with pytest.raises(ValidationError):
        Handoff.model_validate({**base, "from_agent": "ghost"})
    with pytest.raises(ValidationError):
        Handoff.model_validate({**base, "payload": {"whatever": True}})
    with pytest.raises(ValidationError):
        Handoff.model_validate({**base, "round": -1})
    with pytest.raises(ValidationError):
        Handoff.model_validate({**base, "surprise_field": 1})


def test_record_appends_and_hashes(tmp_path):
    rec = ResearchRecord(tmp_path / "log.jsonl")
    e1 = rec.append(agent="planner", run_id="r1", seed=0, input_payload={"a": 1},
                    output=GOOD_SPEC, citations=["lit_001"])
    e2 = rec.append(agent="runner", run_id="r1", seed=0, input_payload={"a": 1},
                    output=GOOD_RUN, citations=[])
    lines = rec.read_all()
    assert len(lines) == 2
    for key in ("timestamp", "agent", "run_id", "seed", "input_hash", "output", "citations"):
        assert key in e1 and key in lines[0]
    assert e1["input_hash"] == e2["input_hash"] == input_hash({"a": 1})


def test_record_hash_is_canonical():
    assert input_hash({"b": 2, "a": 1}) == input_hash({"a": 1, "b": 2})
