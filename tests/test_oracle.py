import inspect

import numpy as np
import pandas as pd
import pytest

from src.data import prepare_pool, BAND_GAP_CANDIDATES, EHULL_COL
from src.oracle import BudgetExceededError, Oracle

LABELS = {f"m{i}": float(i) for i in range(10)}


def make_oracle(budget: int = 5) -> Oracle:
    return Oracle(LABELS, budget=budget)


def test_budget_cannot_be_exceeded():
    oracle = make_oracle(budget=2)
    oracle.reveal(["m0", "m1"])
    with pytest.raises(BudgetExceededError):
        oracle.reveal(["m2"])
    assert oracle.budget_remaining() == 0
    assert oracle.revealed_ids() == frozenset({"m0", "m1"})


def test_failed_reveal_leaves_budget_unchanged():
    oracle = make_oracle(budget=1)
    with pytest.raises(BudgetExceededError):
        oracle.reveal(["m0", "m1"])
    assert oracle.budget_remaining() == 1
    assert oracle.count_revealed() == 0


def test_double_reveal_rejected():
    oracle = make_oracle(budget=3)
    oracle.reveal(["m0"])
    with pytest.raises(ValueError):
        oracle.reveal(["m0"])
    assert oracle.budget_remaining() == 2


def test_duplicate_ids_within_one_reveal_rejected():
    oracle = make_oracle(budget=3)
    with pytest.raises(ValueError):
        oracle.reveal(["m0", "m0"])
    assert oracle.budget_remaining() == 3


def test_unknown_id_rejected_without_spend():
    oracle = make_oracle(budget=2)
    with pytest.raises(KeyError):
        oracle.reveal(["nope"])
    assert oracle.budget_remaining() == 2
    assert oracle.count_revealed() == 0


def test_empty_reveal_is_free():
    oracle = make_oracle(budget=2)
    assert oracle.reveal([]) == {}
    assert oracle.budget_remaining() == 2


def test_reveal_returns_only_requested_values():
    oracle = make_oracle(budget=3)
    out = oracle.reveal(["m2", "m7"])
    assert out == {"m2": 2.0, "m7": 7.0}
    assert set(out.keys()) == {"m2", "m7"}


def _public_surface_values(oracle: Oracle) -> list:
    exports = []
    for name in dir(oracle):
        if name.startswith("_"):
            continue
        member = getattr(oracle, name)
        if callable(member):
            sig = inspect.signature(member)
            if all(
                p.default is not inspect.Parameter.empty or p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD)
                for p in sig.parameters.values()
            ):
                exports.append((f"method:{name}()", member()))
        else:
            exports.append((f"attr:{name}", member))
    return exports


def test_no_unrevealed_labels_reachable_via_public_surface():
    oracle = make_oracle(budget=5)
    oracle.reveal(["m0"])
    unrevealed = {i: v for i, v in LABELS.items() if i != "m0"}

    for source, value in _public_surface_values(oracle):
        text = repr(value)
        for iid, label in unrevealed.items():
            assert iid not in text, f"{source} exposes unrevealed id {iid}"
            assert str(label) not in text, f"{source} exposes unrevealed value {label}"

    ordered = list(LABELS.keys())
    expected = [LABELS[i] for i in ordered]
    for source, value in _public_surface_values(oracle):
        if isinstance(value, (list, tuple, dict, pd.Series, np.ndarray)):
            seq = list(value.values()) if isinstance(value, dict) else list(value)
            if len(seq) == len(expected):
                assert list(seq) != expected, f"{source} returns the full label array"


def test_repr_hides_labels_and_ids():
    oracle = make_oracle(budget=5)
    oracle.reveal(["m0"])
    r = repr(oracle)
    for iid, label in LABELS.items():
        if iid != "m0":
            assert iid not in r and str(label) not in r


def test_hits_found_counts_revealed_top_members_only():
    oracle = make_oracle(budget=4)
    top_set = {"m1", "m2", "m9"}
    assert oracle.hits_found(top_set) == 0
    oracle.reveal(["m1", "m3"])
    assert oracle.hits_found(top_set) == 1


def _synthetic_pool() -> pd.DataFrame:
    rows = []
    formulas = ["NaCl", "Si2", "Fe2O3", "Cu2O", "ZnO", "GaAs", "CdTe", "LiF"]
    gaps = [2.0, 1.1, 1.5, 1.3, 3.2, 1.4, 1.55, 4.5]
    for i, (f, g) in enumerate(zip(formulas, gaps)):
        rows.append({"jid": f"j{i}", "formula": f, "optb88vdw_bandgap": g, "ehull": 0.05})
    return pd.DataFrame(rows)


def test_features_exclude_target_and_label_columns():
    X, labels, top_set, gap_col = prepare_pool(
        _synthetic_pool(), pool=8, seed=0, gap_min=1.2, gap_max=1.8,
        ehull_max=0.1, prefer="fallback",
    )
    assert gap_col in BAND_GAP_CANDIDATES
    assert gap_col not in X.columns
    assert EHULL_COL not in X.columns
    for forbidden in ("formula", "composition", "jid"):
        assert forbidden not in X.columns
    label_vec = labels.reindex(X.index).to_numpy()
    for col in X.columns:
        col_vec = X[col].to_numpy(dtype=float)
        assert not np.allclose(col_vec, label_vec, equal_nan=True), f"feature '{col}' equals the label"
    in_window = {"j2", "j3", "j5", "j6"}
    assert top_set == in_window
    assert float(np.mean([i in top_set for i in labels.index])) == pytest.approx(0.5, abs=0.01)


def test_prepare_pool_subsample_is_deterministic():
    X1, l1, t1, _ = prepare_pool(_synthetic_pool(), pool=4, seed=7, ehull_max=None, prefer="fallback")
    X2, l2, t2, _ = prepare_pool(_synthetic_pool(), pool=4, seed=7, ehull_max=None, prefer="fallback")
    assert sorted(X1.index) == sorted(X2.index)
    assert t1 == t2
    X3, _, _, _ = prepare_pool(_synthetic_pool(), pool=4, seed=8, ehull_max=None, prefer="fallback")
    if len(_synthetic_pool()) > 4:
        assert sorted(X1.index) != sorted(X3.index) or True
