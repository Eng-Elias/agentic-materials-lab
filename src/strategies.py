import pandas as pd

STRATEGIES = ("exploit", "explore", "hybrid", "hypothesis_test")


def _top(series: pd.Series, k: int) -> list[str]:
    if k <= 0:
        return []
    ordered = series.sort_values(ascending=False, kind="mergesort")
    return [str(i) for i in ordered.head(min(k, len(ordered))).index]


def exploit(mean: pd.Series, std: pd.Series, gap_min: float, gap_max: float, k: int) -> list[str]:
    from scipy.stats import norm

    p_win = norm.cdf((gap_max - mean) / std.clip(lower=1e-3)) - norm.cdf((gap_min - mean) / std.clip(lower=1e-3))
    return _top(pd.Series(p_win, index=mean.index), k)


def explore(mean: pd.Series, std: pd.Series, k: int) -> list[str]:
    return _top(std, k)


def hybrid_ucb(
    mean: pd.Series, std: pd.Series, gap_min: float, gap_max: float, k: int, beta: float = 2.0
) -> list[str]:
    from scipy.stats import norm

    s = std.clip(lower=1e-3)
    p_win = pd.Series(
        norm.cdf((gap_max - mean) / s) - norm.cdf((gap_min - mean) / s), index=mean.index
    )
    score = p_win + beta * std / std.max()
    return _top(score, k)


def hypothesis_test(mean: pd.Series, std: pd.Series, gap_min: float, gap_max: float, k: int) -> list[str]:
    from scipy.stats import norm

    s = std.clip(lower=1e-3)
    p_win = pd.Series(
        norm.cdf((gap_max - mean) / s) - norm.cdf((gap_min - mean) / s), index=mean.index
    ).clip(0.0, 1.0)
    score = p_win * (1.0 - p_win) * std
    return _top(score, k)


def acquire(
    strategy: str,
    candidates: list[str],
    surrogate,
    X: pd.DataFrame,
    gap_min: float,
    gap_max: float,
    k: int,
) -> list[str]:
    unseen = [c for c in candidates if c in X.index]
    if not unseen or k <= 0:
        return []
    mean, std = surrogate.predict(X.loc[unseen])
    if strategy == "exploit":
        return exploit(mean, std, gap_min, gap_max, k)
    if strategy == "explore":
        return explore(mean, std, k)
    if strategy == "hybrid":
        return hybrid_ucb(mean, std, gap_min, gap_max, k)
    if strategy == "hypothesis_test":
        return hypothesis_test(mean, std, gap_min, gap_max, k)
    raise ValueError(f"unknown strategy: {strategy}")
