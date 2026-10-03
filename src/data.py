from pathlib import Path

import numpy as np
import pandas as pd

BAND_GAP_CANDIDATES = ["optb88vdw_bandgap", "mbj_bandgap", "band_gap", "gap"]
ID_CANDIDATES = ["jid", "id"]
EHULL_COL = "ehull"

RAW_CACHE = "dft_3d.pkl"


def _resolve_existing(df: pd.DataFrame, candidates: list[str], what: str) -> str:
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(f"No {what} column found; available columns: {df.columns.tolist()}")


def load_raw(dataset: str = "dft_3d", cache_dir: str | Path = "cache") -> pd.DataFrame:
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / RAW_CACHE
    if cached.exists():
        return pd.read_pickle(cached)
    from jarvis.db.figshare import data

    df = pd.DataFrame(data(dataset))
    df.to_pickle(cached)
    return df


def featurize_magpie(df: pd.DataFrame) -> pd.DataFrame:
    from matminer.featurizers.composition import ElementProperty

    work = df.copy()
    featurizer = ElementProperty.from_preset("magpie")
    work = featurizer.featurize_dataframe(work, "composition", ignore_errors=True)
    feature_cols = [c for c in work.columns if c not in df.columns or c == "composition"]
    X = work[feature_cols].drop(columns=["composition"], errors="ignore")
    return X.apply(pd.to_numeric, errors="coerce")


def featurize_fallback(df: pd.DataFrame) -> pd.DataFrame:

    rows = {}
    for jid, comp in df["composition"].items():
        props: dict[str, float] = {}
        w = np.asarray([comp.get_atomic_fraction(el) for el in comp.elements], dtype=float)
        vals = {p: np.asarray([getattr(el, p) or np.nan for el in comp.elements], dtype=float)
                for p in ("X", "Z", "group")}
        for stat_name, fn in {
            "mean": np.mean,
            "std": np.std,
            "min": np.min,
            "max": np.max,
        }.items():
            for pname, arr in vals.items():
                props[f"{pname}_{stat_name}"] = float(
                    np.average(arr, weights=w) if stat_name == "mean" else fn(arr)
                )
        props["X_range"] = float(np.max(vals["X"]) - np.min(vals["X"]))
        rows[jid] = props
    return pd.DataFrame.from_dict(rows, orient="index")


def featurize(df: pd.DataFrame, prefer: str = "magpie") -> pd.DataFrame:
    if prefer == "magpie":
        try:
            X = featurize_magpie(df)
            return X
        except Exception as e:
            print(f"Magpie featurization failed ({e}); using fallback element-property stats")
    return featurize_fallback(df)


def prepare_pool(
    raw_df: pd.DataFrame,
    pool: int = 15000,
    seed: int = 0,
    gap_min: float = 1.0,
    gap_max: float = 2.0,
    ehull_max: float | None = None,
    prefer: str = "magpie",
) -> tuple[pd.DataFrame, pd.Series, set[str], str]:
    gap_col = _resolve_existing(raw_df, BAND_GAP_CANDIDATES, "band gap")
    id_col = next((c for c in ID_CANDIDATES if c in raw_df.columns), None)

    df = raw_df.dropna(subset=[gap_col]).copy()
    df[gap_col] = pd.to_numeric(df[gap_col], errors="coerce")
    df = df.dropna(subset=[gap_col])
    if len(df) > pool:
        df = df.sample(n=pool, random_state=seed)
    df["_id"] = df[id_col].astype(str) if id_col else df.index.astype(str)

    from pymatgen.core import Composition

    df["composition"] = df["formula"].apply(Composition)

    X = featurize(df, prefer=prefer)
    X.index = df["_id"].values

    labels = df.set_index("_id")[gap_col].astype(float)

    in_window = (df[gap_col] >= gap_min) & (df[gap_col] <= gap_max)
    if ehull_max is not None and ehull_max >= 0 and EHULL_COL in df.columns:
        eh = pd.to_numeric(df[EHULL_COL], errors="coerce")
        in_window &= (eh < ehull_max).fillna(False)
    top_set = set(df.loc[in_window, "_id"])

    print(f"pool_size={len(df)} top_set_size={len(top_set)} top_set_fraction={len(top_set)/len(df):.4f}")
    return X.dropna(axis=1, how="all").fillna(0.0), labels, top_set, gap_col


def load_pool(
    pool: int = 15000,
    seed: int = 0,
    gap_min: float = 1.0,
    gap_max: float = 2.0,
    ehull_max: float | None = None,
    cache_dir: str | Path = "cache",
    prefer: str = "magpie",
) -> tuple[pd.DataFrame, pd.Series, set[str]]:
    cache_dir = Path(cache_dir)
    feat_cache = cache_dir / f"features_pool{pool}_seed{seed}.pkl"
    if feat_cache.exists():
        bundle = pd.read_pickle(feat_cache)
        if bundle["params"] == (gap_min, gap_max, ehull_max):
            return bundle["X"], bundle["labels"], bundle["top_set"]
    raw = load_raw(cache_dir=cache_dir)
    X, labels, top_set, gap_col = prepare_pool(raw, pool, seed, gap_min, gap_max, ehull_max, prefer)
    pd.to_pickle(
        {"X": X, "labels": labels, "top_set": top_set,
         "params": (gap_min, gap_max, ehull_max), "gap_column": gap_col},
        feat_cache,
    )
    return X, labels, top_set


if __name__ == "__main__":
    X, labels, top_set = load_pool()
    print(f"features={X.shape} labels={len(labels)} top_set={len(top_set)}")
