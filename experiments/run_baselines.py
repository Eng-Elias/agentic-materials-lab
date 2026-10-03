import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import RunConfig
from src.data import load_pool
from src.oracle import Oracle

ARMS = ["random", "greedy", "uncertainty"]


def run_random(labels: pd.Series, top_set: set[str], cfg: RunConfig, seed: int) -> list[dict]:
    oracle = Oracle(labels, budget=cfg.budget)
    rng = np.random.RandomState(seed)
    batch = cfg.budget // cfg.rounds
    pool_ids = np.array(sorted(labels.index))
    rows = []
    while oracle.budget_remaining() > 0:
        k = min(batch, oracle.budget_remaining())
        unrevealed = pool_ids[~np.isin(pool_ids, list(oracle.revealed_ids()))]
        pick = rng.choice(unrevealed, size=k, replace=False)
        oracle.reveal(list(pick))
        round_no = len(rows) + 1
        rows.append({
            "arm": "random",
            "seed": seed,
            "round": round_no,
            "evaluations": oracle.count_revealed(),
            "cumulative_hits": oracle.hits_found(top_set),
            "rmse": "",
        })
    return rows


def plot_random(df: pd.DataFrame, top_fraction: float, out_path: Path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    grouped = df.groupby("evaluations")["cumulative_hits"]
    mean = grouped.mean()
    std = grouped.std().fillna(0.0)

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.fill_between(mean.index, mean - std, mean + std, alpha=0.25, label="±1 std")
    ax.plot(mean.index, mean, marker="o", label="random mean")
    ax.set_xlabel("Evaluations spent")
    ax.set_ylabel("Cumulative hits (top-set materials found)")
    ax.set_title(f"Random baseline over {df['seed'].nunique()} seeds "
                 f"(top-set fraction {top_fraction:.2%})")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser(description="Non-agentic baseline arms")
    p.add_argument("--seeds", type=int, default=10)
    p.add_argument("--budget", type=int, default=300)
    p.add_argument("--rounds", type=int, default=6)
    p.add_argument("--pool", type=int, default=15000)
    p.add_argument("--gap-min", dest="gap_min", type=float, default=1.0)
    p.add_argument("--gap-max", dest="gap_max", type=float, default=2.0)
    p.add_argument("--ehull-max", dest="ehull_max", type=float, default=-1.0)
    p.add_argument("--arms", type=str, default="random")
    p.add_argument("--quick", action="store_true")
    p.add_argument("--out", type=str, default="results")
    args, _ = p.parse_known_args()

    cfg = RunConfig(
        seeds=2 if args.quick else args.seeds,
        budget=100 if args.quick else args.budget,
        rounds=2 if args.quick else args.rounds,
        pool=2000 if args.quick else args.pool,
        gap_min=args.gap_min,
        gap_max=args.gap_max,
        ehull_max=None if args.ehull_max < 0 else args.ehull_max,
        out_dir=args.out,
    )
    if cfg.budget % cfg.rounds != 0:
        raise SystemExit("budget must be divisible by rounds")

    X, labels, top_set = load_pool(
        pool=cfg.pool, seed=0, gap_min=cfg.gap_min, gap_max=cfg.gap_max,
        ehull_max=cfg.ehull_max, cache_dir="cache",
    )
    del X

    out_dir = Path(cfg.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    arms = [a.strip() for a in args.arms.split(",")]
    for arm in arms:
        if arm != "random":
            raise SystemExit(f"arm '{arm}' not implemented yet (slice 3.3 adds greedy/uncertainty)")
        rows = []
        for seed in range(cfg.seeds):
            rows.extend(run_random(labels, top_set, cfg, seed))
        df = pd.DataFrame(rows, columns=["arm", "seed", "round", "evaluations", "cumulative_hits", "rmse"])
        csv_path = out_dir / f"baseline_{arm}.csv"
        df.to_csv(csv_path, index=False)
        plot_random(df, len(top_set) / len(labels), out_dir / f"baseline_{arm}.png")

        final = df[df.evaluations == df.evaluations.max()]
        hit_rate = final["cumulative_hits"].mean() / max(1, df.evaluations.max())
        print(f"arm={arm} seeds={cfg.seeds} budget={df.evaluations.max()}"
              f" top_set_fraction={len(top_set)/len(labels):.4f} random_hit_rate={hit_rate:.4f}")
        print(f"wrote {csv_path} and {out_dir}/baseline_{arm}.png")


if __name__ == "__main__":
    main()
