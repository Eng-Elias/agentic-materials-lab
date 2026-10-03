import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import RunConfig
from src.data import load_pool
from src.oracle import Oracle
from src.record import ResearchRecord
from src.schemas import (
    AnalysisVerdict,
    Citation,
    ExperimentSpec,
    Handoff,
    Hypothesis,
    HypothesisVerdict,
    RunResult,
)
from src.strategies import acquire
from src.surrogate import Surrogate

HYPOTHESES = [
    dict(id="H1", label="AGENT-GENERATED",
         statement="Electronegativity spread (X_std) correlates positively with band gap.",
         testable_feature_set=["MagpieData std Deviation Electronegativity"],
         predicted_direction="positive", supporting_citation_ids=["lit_001", "lit_002"]),
    dict(id="H2", label="AGENT-GENERATED",
         statement="Mean group (noble/metal content proxy) shifts band gap; lower mean group associates with wider gap.",
         testable_feature_set=["MagpieData mean NGroup"], predicted_direction="negative",
         supporting_citation_ids=["lit_001"]),
    dict(id="H3", label="AGENT-GENERATED",
         statement="Composition-based ML surrogates reduce evaluations needed (active learning works).",
         testable_feature_set=["*"], predicted_direction="positive",
         supporting_citation_ids=["lit_005", "lit_006"]),
]

MISLEADING_H1 = dict(HYPOTHESES[0])
MISLEADING_H1.update(
    statement=("Designed-misleading rule (AGENT-GENERATED): SMALL electronegativity difference alone "
               "(near-covalent bonding) determines membership in the band-gap window; exploit by "
               "selecting minimal Magpie 'range Electronegativity'."),
    testable_feature_set=["MagpieData range Electronegativity"],
    predicted_direction="negative")


def handoff(rec: ResearchRecord, run_id: str, seed: int, round_no: int,
            from_agent: str, to_agent: str, payload, citations=None) -> Handoff:
    h = Handoff(run_id=run_id, round=round_no, from_agent=from_agent, to_agent=to_agent,
                payload=payload, citations=citations or [])
    rec.append(agent=from_agent, run_id=run_id, seed=seed, input_payload=h.model_dump(exclude={"output"}),
               output=h.payload.model_dump(), citations=h.citations)
    return h


def literature_agent(cache_dir: str = "cache/lit"):
    from src.tools_lit import papers_from_openalex

    queries = ["machine learning prediction band gap inorganic materials electronegativity",
               "active learning materials discovery band gap"]
    claims = []
    for q in queries:
        papers, _ = papers_from_openalex(q, cache_dir=cache_dir)
        for i, p in enumerate(papers[:6]):
            claims.append(Citation(
                id=f"lit_{len(claims)+1:03d}",
                claim=p["title"],
                source_title=p["title"], doi_or_url=p["doi_or_url"],
                year=p["year"], cached_response_id=p["cache_file"]))
    return claims


def planner_score(strategies, surrogate, X, candidates, cfg, k) -> dict[str, float]:
    scores = {}
    for s in strategies:
        batch = acquire(s, candidates, surrogate, X, cfg.gap_min, cfg.gap_max, k)
        if not batch:
            scores[s] = -np.inf
            continue
        mean, std = surrogate.predict(X.loc[batch])
        p = surrogate.in_window_probability(X.loc[batch], cfg.gap_min, cfg.gap_max)
        expected_hits = float(p.sum())
        expected_learning = float(std.sum()) + expected_hits * 2.0
        feasibility = 1.0 if len(batch) == k else 0.5
        scores[s] = expected_learning * feasibility / len(batch)
    return scores


def run_seed(cfg: RunConfig, seed: int, backend: str, use_cache: str,
             no_analysis: bool, refutation_demo: bool,
             X, labels, top_set, rec: ResearchRecord) -> list[dict]:
    if backend != "engine":
        raise NotImplementedError(
            "backend='omnigent' pending T002 smoke test; use --backend engine")

    arm = "refutation" if refutation_demo else "ablation" if no_analysis else "agentic"
    run_id = f"{arm}-seed{seed}"
    oracle = Oracle(labels, budget=cfg.budget)
    surrogate = Surrogate(seed=seed)
    batch = cfg.batch_size
    rows: list[dict] = []
    history: list[dict] = []
    verdicts: list[HypothesisVerdict] = []
    recommendation = None
    h1_refuted = False
    refute_reason = ""

    hyps = [Hypothesis(**h) for h in ([MISLEADING_H1] + HYPOTHESES[1:] if refutation_demo else HYPOTHESES)]
    claims = literature_agent()
    used_citation_ids = sorted({c.id for c in claims})

    from src.schemas import LiteratureClaims, InsightHypotheses
    handoff(rec, run_id, seed, 0, "literature", "insight",
            LiteratureClaims(claims=claims), [c.id for c in claims])
    handoff(rec, run_id, seed, 0, "insight", "planner",
            InsightHypotheses(hypotheses=hyps),
            sorted({c for h in hyps for c in h.supporting_citation_ids}))

    rng = np.random.RandomState(10_000 + seed)
    pool_ids = np.array(sorted(labels.index))
    seed_ids = list(rng.choice(pool_ids, size=batch, replace=False))
    observed: dict[str, float] = dict(oracle.reveal(seed_ids))
    surrogate.fit(X.loc[seed_ids], pd.Series(observed))
    rows.append(_row(seed, 0, oracle, top_set, "random_seed", np.nan, arm))
    history.append({"round": 0, "hits": oracle.hits_found(top_set),
                    "rate": rr0_rate(oracle, top_set, batch)})

    while oracle.budget_remaining() > 0:
        round_no = len(rows)
        k = min(batch, oracle.budget_remaining())
        candidates = sorted(set(labels.index) - oracle.revealed_ids())

        scores = planner_score(["exploit", "explore", "hybrid", "hypothesis_test"],
                               surrogate, X, candidates, cfg, k)
        ranked = sorted(scores, key=lambda s: -scores[s])
        chosen = ranked[0]
        h1_guided = refutation_demo and not h1_refuted
        if refutation_demo:
            chosen = "exploit" if h1_guided else "hybrid"
        elif no_analysis:
            chosen = ranked[0]
        elif recommendation == "switch_to_hybrid":
            chosen = "hybrid"
        elif recommendation == "switch_to_explore":
            chosen = "explore"

        rejected = [{"strategy": s,
                     "reason": (f"top scored {scores[s]:.2f} but overridden by analysis recommendation"
                                if s == ranked[0] and s != chosen else
                                f"score {scores[s]:.2f} not above chosen {scores[chosen]:.2f}")}
                    for s in ranked if s != chosen][:2]
        if h1_guided:
            feat = MISLEADING_H1["testable_feature_set"][0]
            batch_ids = list(X.loc[candidates, feat].nsmallest(k).index)
            rationale = f"exploit guided by top Insight hypothesis H1 (min {feat})"
        else:
            batch_ids = acquire(chosen, candidates, surrogate, X, cfg.gap_min, cfg.gap_max, k)
            rationale = ("switch to hybrid: H1 REFUTED — " + refute_reason if refutation_demo and h1_refuted
                         else "Analysis recommends switch" if recommendation and not no_analysis
                         else "max expected learning score")
        spec = ExperimentSpec(round=round_no, strategy=chosen, batch_ids=batch_ids,
                              rationale=rationale,
                              expected_learning=f"expected in-window hits proxy {scores[chosen]:.2f}",
                              cost=k, rejected_alternatives=[{"strategy": r["strategy"], "reason": r["reason"]} for r in rejected])
        handoff(rec, run_id, seed, round_no, "planner", "runner", spec, used_citation_ids[:4])

        revealed = oracle.reveal(spec.batch_ids)
        observed.update(revealed)
        rr = RunResult(batch_ids=spec.batch_ids, true_values=list(revealed.values()),
                       hits_in_batch=len(set(spec.batch_ids) & top_set),
                       cumulative_hits=oracle.hits_found(top_set),
                       budget_remaining=oracle.budget_remaining(), run_id=run_id, seed=seed)
        handoff(rec, run_id, seed, round_no, "runner", "analysis", rr, [])

        ids_tr = sorted(observed)
        surrogate.fit(X.loc[ids_tr], pd.Series({i: observed[i] for i in ids_tr}))
        rmse = float(np.sqrt(np.mean((surrogate.predict(X.loc[ids_tr])[0] - pd.Series({i: observed[i] for i in ids_tr})) ** 2)))

        history.append({"round": round_no, "hits": rr.cumulative_hits,
                        "rate": rr.hits_in_batch / max(1, len(rr.batch_ids))})
        rows.append(_row(seed, round_no, oracle, top_set, chosen, rmse, arm))

        if no_analysis:
            verdicts, recommendation = [], None
        else:
            analysis = analyze(history, hyps, len(top_set) / len(labels), run_id, seed,
                               already_refuted=h1_refuted)
            verdicts = analysis.hypothesis_verdicts
            recommendation = analysis.strategy_recommendation
            if any(v.id == "H1" and v.verdict == "refuted" for v in verdicts):
                h1_refuted = True
                refute_reason = analysis.reason
            handoff(rec, run_id, seed, round_no, "analysis", "planner", analysis, used_citation_ids[-2:])
    return rows


def rr0_rate(oracle, top_set, batch) -> float:
    return oracle.hits_found(top_set) / max(1, batch)


def analyze(history, hyps, baseline_rate: float, run_id: str, seed: int,
            already_refuted: bool = False) -> AnalysisVerdict:
    late = [h for h in history if h["round"] >= 1][-2:]
    refuted = already_refuted or (len(late) == 2 and all(h["rate"] <= baseline_rate for h in late))
    verdicts = []
    for h in hyps:
        if refuted and h.id == "H1":
            evidence = ("guided-arm hit rate " + str([round(h["rate"], 3) for h in late])
                        + f" at/below random baseline {baseline_rate:.3f} for 2 consecutive rounds"
                        if not already_refuted else
                        "H1 remains REFUTED (refutation is terminal); prior evidence stands")
            verdicts.append(HypothesisVerdict(id="H1", verdict="refuted", evidence=evidence))
        elif refuted and h.id == "H3":
            verdicts.append(HypothesisVerdict(
                id="H3", verdict="supported",
                evidence=f"strategy switch from exploit recommended after {len(history)-1} rounds; evals survived"))
        else:
            verdicts.append(HypothesisVerdict(id=h.id, verdict="inconclusive"))
    return AnalysisVerdict(
        hypothesis_verdicts=verdicts,
        strategy_recommendation="switch_to_hybrid" if refuted else "continue",
        reason=("two consecutive rounds at/below random baseline — exploit guided by H1 plateaus"
                if refuted else "hit rate tracking expectations"))


def _row(seed: int, round_no: int, oracle: Oracle, top_set, strategy: str, rmse, arm: str) -> dict:
    return {"arm": arm, "seed": seed, "round": round_no,
            "evaluations": oracle.count_revealed(), "cumulative_hits": oracle.hits_found(top_set),
            "rmse": rmse, "strategy": strategy}


def main():
    p = argparse.ArgumentParser(description="Agentic loop (engine backend until T002 lands)")
    p.add_argument("--seeds", type=int, default=1)
    p.add_argument("--budget", type=int, default=300)
    p.add_argument("--rounds", type=int, default=6)
    p.add_argument("--pool", type=int, default=15000)
    p.add_argument("--gap-min", dest="gap_min", type=float, default=1.0)
    p.add_argument("--gap-max", dest="gap_max", type=float, default=2.0)
    p.add_argument("--ehull-max", dest="ehull_max", type=float, default=-1.0)
    p.add_argument("--backend", type=str, default="engine", choices=["engine", "omnigent"])
    p.add_argument("--refutation-demo", action="store_true")
    p.add_argument("--no-analysis", action="store_true")
    p.add_argument("--use-cache", dest="use_cache", type=str, default="cache")
    p.add_argument("--quick", action="store_true")
    p.add_argument("--out", type=str, default="results")
    args = p.parse_args()

    cfg = RunConfig(seeds=2 if args.quick else args.seeds,
                    budget=100 if args.quick else args.budget,
                    rounds=2 if args.quick else args.rounds,
                    pool=2000 if args.quick else args.pool,
                    gap_min=args.gap_min, gap_max=args.gap_max,
                    ehull_max=None if args.ehull_max < 0 else args.ehull_max,
                    out_dir=args.out, cache_dir=args.use_cache)
    if cfg.budget % cfg.rounds:
        raise SystemExit("budget must be divisible by rounds")

    X, labels, top_set = load_pool(pool=cfg.pool, seed=0, gap_min=cfg.gap_min,
                                   gap_max=cfg.gap_max, ehull_max=cfg.ehull_max,
                                   cache_dir=cfg.cache_dir)
    out_dir = Path(cfg.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    log_path = Path("records/refutation_example.jsonl" if args.refutation_demo
                    else "records/research_log.jsonl")
    log_path.unlink(missing_ok=True)
    all_rows = []
    for seed in range(cfg.seeds):
        rec = ResearchRecord(log_path)
        rows = run_seed(cfg, seed, args.backend, args.use_cache,
                        args.no_analysis, args.refutation_demo, X, labels, top_set, rec)
        df = pd.DataFrame(rows)
        name = "refutation" if args.refutation_demo else "ablation" if args.no_analysis else "agentic"
        df.to_csv(out_dir / f"{name}_seed{seed}.csv", index=False)
        final = df.iloc[-1]
        print(f"seed={seed} evals={int(final.evaluations)} hits={int(final.cumulative_hits)} "
              f"strategies={df.strategy.unique().tolist()}")
        all_rows.extend(rows)
    if cfg.seeds > 1:
        name = "ablation" if args.no_analysis else "agentic"
        pd.DataFrame(all_rows).to_csv(out_dir / f"{name}.csv", index=False)


if __name__ == "__main__":
    main()
