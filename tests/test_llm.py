import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "experiments"))

from src.llm import complete, provider_from_env  # noqa: E402
from run_agentic import _parse_hypotheses, HYPOTHESES  # noqa: E402


def test_cache_roundtrip(tmp_path):
    calls = []
    def backend(agent, prompt):
        calls.append(prompt)
        return "out:" + prompt[:4]
    r1 = complete("a", "m", "prompt-1", 0, cache_dir=tmp_path, backend=backend)
    r2 = complete("a", "m", "prompt-1", 0, cache_dir=tmp_path, backend=backend)
    assert not r1["cache_hit"] and r2["cache_hit"] and len(calls) == 1
    entry = json.loads((tmp_path / f"{r1['key']}.json").read_text())
    assert entry["model"] == "m" and entry["seed"] == 0


def test_cache_key_separates_seed_and_agent(tmp_path):
    b = lambda a, p: "x"
    k1 = complete("a", "m", "p", 0, cache_dir=tmp_path, backend=b)["key"]
    k2 = complete("a", "m", "p", 1, cache_dir=tmp_path, backend=b)["key"]
    k3 = complete("b", "m", "p", 0, cache_dir=tmp_path, backend=b)["key"]
    assert len({k1, k2, k3}) == 3


def test_miss_without_backend_raises(tmp_path):
    with pytest.raises(RuntimeError):
        complete("a", "m", "p", 0, cache_dir=tmp_path, backend=None)


def test_provider_default_is_engine(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    provider, model, backend = provider_from_env()
    assert provider == "engine" and model == "deterministic-engine-v1" and backend is None


def test_provider_openai_requires_key_and_model(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        provider_from_env()
    monkeypatch.setenv("LLM_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    provider, model, backend = provider_from_env()
    assert provider == "openai" and model == "gpt-4o-mini" and callable(backend)


def test_parse_hypotheses_fallback():
    hyps = _parse_hypotheses("not json at all", HYPOTHESES)
    assert [h.id for h in hyps] == ["H1", "H2", "H3"]


def test_parse_hypotheses_forces_label():
    out = json.dumps([{"id": "HX", "label": "HUMAN", "statement": "s",
                       "testable_feature_set": ["f"], "predicted_direction": "positive",
                       "supporting_citation_ids": ["lit_001"]}])
    hyps = _parse_hypotheses(out, HYPOTHESES)
    assert hyps[0].label == "AGENT-GENERATED" and hyps[0].id == "HX"
