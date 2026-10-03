"""Tool surface for Omnigent agents.

Run-time state (oracle, surrogate, run context) is injected by
experiments/run_agentic.py via init_session(). Each public function checks
the caller's grant through src/permissions.require() — the YAML workflow
mirrors these grants per agent, and this module enforces them in-process as
defense in depth (constitution Principle V).
"""

from typing import Any

from src import permissions

_CXT: dict[str, Any] = {}


def init_session(cfg=None, X=None, labels=None, top_set=None, oracle=None, surrogate=None,
                 record=None, agent_caller: str = "scientist"):
    _CXT.update(cfg=cfg, X=X, labels=labels, top_set=top_set, oracle=oracle,
                surrogate=surrogate, record=record, agent_caller=agent_caller)


def get(key: str):
    if key not in _CXT or _CXT[key] is None:
        raise RuntimeError(f"session not initialized for '{key}'")
    return _CXT[key]


# --- literature ---
def search_lit(query: str, per_page: int = 5) -> list[dict]:
    permissions.require("literature", "search_lit")
    from src.tools_lit import search

    papers, cache_id = search(query, per_page=per_page)
    for i, p in enumerate(papers):
        p["lit_id"] = f"lit_{i+1:03d}"
    return papers


def read_lit() -> dict:
    permissions.require("insight", "read_lit")
    from pathlib import Path

    return {"citations_doc": Path("docs/CITATIONS.md").read_text()}


def read_stats(agent: str = "analysis") -> dict:
    permissions.require(agent, "read_stats")
    cfg, labels, top_set = get("cfg"), get("labels"), get("top_set")
    return {
        "pool_size": int(len(labels)),
        "top_set_size": int(len(top_set)),
        "top_set_fraction": len(top_set) / len(labels),
        "budget_total": cfg.budget if cfg else None,
    }


# --- planner ---
def query_surrogate(candidate_ids: list[str]) -> dict:
    permissions.require("planner", "query_surrogate")
    X, surrogate, cfg = get("X"), get("surrogate"), get("cfg")
    subset = [c for c in candidate_ids if c in X.index]
    mean, std = surrogate.predict(X.loc[subset])
    p_win = surrogate.in_window_probability(X.loc[subset], cfg.gap_min, cfg.gap_max)
    return {i: {"mean": float(mean[i]), "std": float(std[i]), "p_in_window": float(p_win[i])}
            for i in subset}


def read_budget() -> dict:
    permissions.require("planner", "read_budget")
    oracle = get("oracle")
    return {"budget_remaining": oracle.budget_remaining(), "revealed": oracle.count_revealed()}


# --- runner ---
def oracle_reveal(ids: list[str]) -> dict:
    permissions.require("runner", "oracle_reveal")
    return get("oracle").reveal(ids)


def train_surrogate(revealed: dict[str, float]) -> dict:
    permissions.require("runner", "train_surrogate")
    import pandas as pd

    X, surrogate = get("X"), get("surrogate")
    ids = [i for i in revealed if i in X.index]
    surrogate.fit(X.loc[ids], pd.Series({i: revealed[i] for i in ids}))
    return {"trained_on": len(ids)}


# --- analysis ---
def read_results() -> dict:
    permissions.require("analysis", "read_results")
    return dict(get("run_history"))


# --- record ---
def append_record(agent: str, run_id: str, seed: int, output: dict, citations: list[str] | None = None) -> dict:
    permissions.require("record", "append_record")
    return get("record").append(agent=agent, run_id=run_id, seed=seed, input_payload=output, output=output, citations=citations)


# --- safety ---
def request_approval(action: str, justification: str) -> dict:
    permissions.require("safety", "request_approval")
    return {"pending": {"action": action, "justification": justification}}


def recommend_for_validation(shortlist: list[dict], approval: dict) -> dict:
    permissions.require("safety", "recommend_for_validation")
    if not approval.get("approved"):
        raise permissions.PermissionDenied("recommend_for_validation without approved decision")
    from pathlib import Path
    import json

    Path("results").mkdir(exist_ok=True)
    out = {"shortlist": shortlist, "approval": approval}
    Path("results/shortlist.json").write_text(json.dumps(out, indent=2, default=str))
    return out
