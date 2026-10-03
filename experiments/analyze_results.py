"""Aggregate arm CSVs -> curves.png + summary.csv. Numbers exactly as measured."""
import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ARM_FILES = {
    "random": "baseline_random.csv",
    "greedy": "baseline_greedy.csv",
    "uncertainty": "baseline_uncertainty.csv",
    "agentic": "agentic.csv",
    "ablation": "ablation.csv",
}
COLORS = {"random": "#888888", "greedy": "#d62728", "uncertainty": "#ff7f0e",
          "agentic": "#1f77b4", "ablation": "#2ca02c"}


def load_arms(results_dir: Path) -> dict[str, pd.DataFrame]:
    arms = {}
    for arm, fname in ARM_FILES.items():
        path = results_dir / fname
        if path.exists():
            df = pd.read_csv(path)
            df["arm"] = arm  # normalize (baseline csvs already carry arm)
            arms[arm] = df
        else:
            print(f"warning: {path} missing — arm '{arm}' skipped")
    return arms


def evals_to_hits(df: pd.DataFrame, milestone: int) -> pd.Series:
    """Per-seed first evaluations value at which cumulative_hits >= milestone;
    NaN if never reached."""
    out = {}
    for seed, g in df.groupby("seed"):
        g = g.sort_values("evaluations")
        hit = g.loc[g.cumulative_hits >= milestone, "evaluations"]
        out[seed] = float(hit.iloc[0]) if len(hit) else np.nan
    return pd.Series(out)


def main():
    p = argparse.ArgumentParser(description="Aggregate results across arms")
    p.add_argument("--results", type=str, default="results")
    p.add_argument("--pool", type=int, default=15000)
    p.add_argument("--gap-min", dest="gap_min", type=float, default=1.0)
    p.add_argument("--gap-max", dest="gap_max", type=float, default=2.0)
    p.add_argument("--ehull-max", dest="ehull_max", type=float, default=-1.0)
    p.add_argument("--top-set-size", type=int, default=0,
                   help="skip load_pool; else computed via src.data.load_pool")
    p.add_argument("--cache", type=str, default="cache")
    args = p.parse_args()

    if args.top_set_size:
        top_set_size = args.top_set_size
    else:
        from src.data import load_pool
        _, _, top_set = load_pool(pool=args.pool, seed=0, gap_min=args.gap_min,
                                  gap_max=args.gap_max,
                                  ehull_max=None if args.ehull_max < 0 else args.ehull_max,
                                  cache_dir=args.cache)
        top_set_size = len(top_set)

    results_dir = Path(args.results)
    arms = load_arms(results_dir)
    if not arms:
        raise SystemExit("no arm CSVs found")

    # (1) hits vs evaluations, mean +/- std shading
    fig, ax = plt.subplots(figsize=(8, 5))
    for arm, df in arms.items():
        grp = df.groupby("evaluations").cumulative_hits
        mean, std = grp.mean(), grp.std().fillna(0.0)
        ax.plot(mean.index, mean.values, label=arm, color=COLORS[arm], lw=2)
        ax.fill_between(mean.index, mean - std, mean + std,
                        color=COLORS[arm], alpha=0.15)
    ax.axhline(top_set_size * 0.5, ls="--", c="k", lw=1, alpha=0.5,
               label="50% of top set")
    ax.set_xlabel("evaluations")
    ax.set_ylabel("cumulative hits (in-window)")
    ax.set_title("Discovery efficiency: hits vs evaluations (mean +/- std, 10 seeds)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(results_dir / "curves.png", dpi=150)
    print(f"wrote {results_dir/'curves.png'}")

    # (2) evaluations to reach milestones, per arm (mean+-std across seeds)
    milestones = sorted({1, 5, 10, 25, 50, int(np.ceil(top_set_size * 0.5))})
    rows = []
    for arm, df in arms.items():
        final = df[df["round"] == df["round"].max()].cumulative_hits
        for m in milestones:
            s = evals_to_hits(df, m)
            reached = s.dropna()
            rows.append({
                "arm": arm, "milestone_hits": m,
                "evals_mean": round(reached.mean(), 1) if len(reached) else np.nan,
                "evals_std": round(reached.std(), 1) if len(reached) > 1 else np.nan,
                "seeds_reached": int(len(reached)), "seeds_total": int(len(s)),
                "final_hits_mean": round(final.mean(), 2),
                "final_hits_std": round(final.std(), 2),
                "note": "" if len(reached) else "never reached within budget",
            })
    summary = pd.DataFrame(rows)

    # (3) speedup at matched milestones: evals_arm / evals_agentic (>=1 means
    # agentic needed fewer evals). Computed on per-seed eval series where both
    # arms reached the milestone.
    speed_rows = []
    if "agentic" in arms:
        for m in milestones:
            ag = evals_to_hits(arms["agentic"], m)
            for arm, df in arms.items():
                if arm == "agentic":
                    continue
                other = evals_to_hits(df, m)
                both = pd.concat([other, ag], axis=1, keys=["other", "agentic"]).dropna()
                if len(both) == 0:
                    continue
                ratio = both["other"] / both["agentic"]
                speed_rows.append({
                    "milestone_hits": m, "arm_vs_agentic": arm,
                    "speedup_mean": round(ratio.mean(), 3),
                    "speedup_std": round(ratio.std(), 3) if len(ratio) > 1 else np.nan,
                    "n_seeds": int(len(ratio)),
                    "interpretation": ("agentic faster" if ratio.mean() > 1
                                       else "agentic slower" if ratio.mean() < 1
                                       else "equal"),
                })
    speedups = pd.DataFrame(speed_rows)

    # (4) summary.csv
    summary.to_csv(results_dir / "summary.csv", index=False)
    speedups.to_csv(results_dir / "speedups.csv", index=False)
    print(f"wrote {results_dir/'summary.csv'} and {results_dir/'speedups.csv'}")
    print(f"top_set_size={top_set_size}")
    print(speedups.to_string(index=False) if len(speedups) else "no matched milestones")


if __name__ == "__main__":
    main()
