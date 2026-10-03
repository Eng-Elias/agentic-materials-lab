import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import RunConfig
from src.data import load_pool
from src.oracle import Oracle
from src.strategies import acquire
from src.surrogate import Surrogate

ARMS = ["random", "greedy", "uncertainty"]
ARM_STRATEGY = {"greedy": "exploit", "uncertainty": "explore"}


def seeding_batch(labels: pd.Series, k: int, seed: int) -> list[str]:
    rng = np.random.RandomState(10_000 + seed)
    ids = np.array(sorted(labels.index))
    return list(rng.choice(ids, size=k, replace=False))


def run_arm(
    arm: str,
    X: pd.DataFrame,
    labels: pd.Series,
    top_set: set[str],
    cfg: RunConfig,
    seed: int,
) -> list[dict]:
    oracle = Oracle(labels, budget=cfg.budget)
    rng = np.random.RandomState(seed)
    batch = cfg.batch_size
    rows: list[dict] = []
    observed: dict[str, float] = {}

    seed_ids = seeding_batch(labels, batch, seed)
    observed.update(oracle.reveal(seed_ids))
    rows.append(_row(arm, seed, 1, oracle, top_set, rmse=np.nan))

    surrogate = Surrogate(seed=seed)
    while oracle.budget_remaining() > 0:
        round_no = len(rows) + 1
        k = min(batch, oracle.budget_remaining())
        if arm == "random":
            unrevealed = np.array(sorted(set(labels.index) - oracle.revealed_ids()))
            pick = list(rng.choice(unrevealed, size=k, replace=False))
            rmse = np.nan
        else:
            ids_tr = sorted(observed)
            surrogate.fit(X.loc[ids_tr], pd.Series({i: observed[i] for i in ids_tr}))
            rmse = float(np.sqrt(np.mean((surrogate.predict(X.loc[ids_tr])[0] - pd.Series({i: observed[i] for i in ids_tr})) ** 2)))
            candidates = sorted(set(labels.index) - oracle.revealed_ids())
            pick = acquire(
                ARM_STRATEGY[arm], candidates, surrogate, X,
                cfg.gap_min, cfg.gap_max, k,
            )
        observed.update(oracle.reveal(pick))
        rows.append(_row(arm, seed, round_no, oracle, top_set, rmse=rmse))
    return rows


def _row(arm: str, seed: int, round_no: int, oracle: Oracle, top_set: set[str], rmse: float) -> dict:
    return {
        "arm": arm,
        "seed": seed,
        "round": round_no,
        "evaluations": oracle.count_revealed(),
        "cumulative_hits": oracle.hits_found(top_set),
        "rmse": rmse,
    }


def evals_to_hits(df: pd.DataFrame, hits: int) -> tuple[float, float | None]:
    by_seed = []
    for _, g in df.groupby("seed"):
        hit = g[g.cumulative_hits >= hits]
        by_seed.append(float(hit.evaluations.min()) if len(hit) else np.nan)
    reached = [v for v in by_seed if not np.isnan(v)]
    if not reached:
        return np.nan, None
    std = float(np.std(reached)) if len(reached) > 1 else None
    return float(np.mean(reached)), std


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
    p.add_argument("--arms", type=str, default="random,greedy,uncertainty")
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

    out_dir = Path(cfg.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    arms = [a.strip() for a in args.arms.split(",")]
    unknown = set(arms) - set(ARMS)
    if unknown:
        raise SystemExit(f"unknown arms: {sorted(unknown)} (allowed: {ARMS})")
    for arm in arms:
        rows = []
        for seed in range(cfg.seeds):
            rows.extend(run_arm(arm, X, labels, top_set, cfg, seed))
        df = pd.DataFrame(rows, columns=["arm", "seed", "round", "evaluations", "cumulative_hits", "rmse"])
        csv_path = out_dir / f"baseline_{arm}.csv"
        df.to_csv(csv_path, index=False)
        plot_random(df, len(top_set) / len(labels), out_dir / f"baseline_{arm}.png")

        final = df[df.evaluations == df.evaluations.max()]
        hit_rate = final["cumulative_hits"].mean() / max(1, df.evaluations.max())
        milestones = {m: evals_to_hits(df, m) for m in (5, 10, 15, 20)}
        ms = " ".join(f"e@{m}={v[0]:.0f}" if not np.isnan(v[0]) else f"e@{m}=--"
                      for m, v in milestones.items())
        print(f"arm={arm} seeds={cfg.seeds} budget={df.evaluations.max()}"
              f" top_set_fraction={len(top_set)/len(labels):.4f} hit_rate={hit_rate:.4f}"
              f" mean_hits={final['cumulative_hits'].mean():.1f} {ms}")
        print(f"wrote {csv_path} and {out_dir}/baseline_{arm}.png")


if __name__ == "__main__":
    main()
