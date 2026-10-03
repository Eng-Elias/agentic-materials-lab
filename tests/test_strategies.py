import numpy as np
import pandas as pd
import pytest

from src.strategies import exploit, explore, hybrid_ucb, hypothesis_test, acquire

IDS = [f"c{i}" for i in range(20)]
MEAN = pd.Series(np.linspace(0.0, 3.0, 20), index=IDS)
STD = pd.Series(np.linspace(0.3, 0.3, 20), index=IDS)
STD[IDS[5]] = 1.5
STD[IDS[6]] = 2.0


class StubSurrogate:
    def __init__(self, mean, std):
        self.mean = mean
        self.std = std

    def predict(self, X):
        return self.mean.loc[X.index], self.std.loc[X.index]


@pytest.fixture
def X():
    return pd.DataFrame(np.ones((20, 3)), index=IDS)


def test_exploit_picks_closest_to_window():
    picks = exploit(MEAN, STD, 1.0, 2.0, k=3)
    centered = ["c9", "c10", "c11"]
    assert set(picks) == set(centered)
    in_window = MEAN[(MEAN >= 1.0) & (MEAN <= 2.0)].index.tolist()
    assert set(picks).issubset(set(in_window))


def test_exploit_empty_when_nothing_in_window_and_prefers_upside():
    mean_low = pd.Series([0.0] * 4 + [0.5], index=[f"x{i}" for i in range(5)])
    picks = exploit(mean_low, pd.Series([0.2] * 5, index=mean_low.index), 1.0, 2.0, k=1)
    assert picks == ["x4"]


def test_explore_picks_highest_uncertainty():
    picks = explore(MEAN, STD, k=2)
    assert picks == [IDS[6], IDS[5]]


def test_hybrid_mixes_value_and_uncertainty():
    picks = hybrid_ucb(MEAN, STD, 1.0, 2.0, k=4, beta=2.0)
    assert IDS[6] in picks
    assert len(picks) == 4
    assert len(set(picks)) == 4


def test_hypothesis_test_prefers_edge_of_knowledge():
    mean = pd.Series([0.0] * 20, index=IDS)
    std = pd.Series([0.5] * 20, index=IDS)
    mean[IDS[6]] = 1.0
    std[IDS[6]] = 1.5
    std[IDS[0]] = 2.0
    picks = hypothesis_test(mean, std, 1.0, 2.0, k=2)
    assert picks[0] == IDS[6]
    assert set(picks) == {IDS[6], IDS[0]}
    pure_uncertainty = explore(mean, std, k=2)
    assert pure_uncertainty[0] == IDS[0]
    assert picks != pure_uncertainty


def test_k_zero_returns_nothing(X):
    assert exploit(MEAN, STD, 1.0, 2.0, 0) == []
    assert explore(MEAN, STD, 0) == []
    assert acquire("explore", IDS, StubSurrogate(MEAN, STD), X, 1.0, 2.0, 0) == []


def test_acquire_filters_candidates_to_known_ids(X):
    surrogate = StubSurrogate(MEAN, STD)
    picks = acquire("exploit", IDS + ["ghost", "ghost2"], surrogate, X, 1.0, 2.0, 3)
    assert "ghost" not in picks and "ghost2" not in picks
    assert len(picks) == 3


def test_acquire_unknown_strategy_raises(X):
    with pytest.raises(ValueError):
        acquire("nope", IDS, StubSurrogate(MEAN, STD), X, 1.0, 2.0, 3)


def test_picks_never_exceed_k_or_duplicate(X):
    surrogate = StubSurrogate(MEAN, STD)
    for name in ("exploit", "explore", "hybrid", "hypothesis_test"):
        picks = acquire(name, IDS, surrogate, X, 1.0, 2.0, 7)
        assert len(picks) == 7 and len(set(picks)) == 7
        assert set(picks).issubset(set(IDS))
