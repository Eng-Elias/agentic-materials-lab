import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

STD_FLOOR = 1e-3


class Surrogate:
    def __init__(self, seed: int = 0, n_estimators: int = 200):
        self.seed = seed
        self.model = RandomForestRegressor(
            n_estimators=n_estimators, random_state=seed, n_jobs=-1
        )
        self.columns_: list[str] | None = None

    def fit(self, X: pd.DataFrame, y: pd.Series | np.ndarray):
        self.columns_ = list(X.columns)
        self.model.fit(X.to_numpy(dtype=float), np.asarray(y, dtype=float))
        return self

    def predict(self, X: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
        if self.columns_ is None:
            raise RuntimeError("Surrogate.predict called before fit")
        X = X.reindex(columns=self.columns_, fill_value=0.0)
        tree_preds = np.stack([t.predict(X.to_numpy(dtype=float)) for t in self.model.estimators_])
        mean = pd.Series(tree_preds.mean(axis=0), index=X.index)
        std = pd.Series(tree_preds.std(axis=0, ddof=1), index=X.index).clip(lower=STD_FLOOR)
        return mean, std

    def in_window_probability(self, X: pd.DataFrame, lo: float, hi: float) -> pd.Series:
        from scipy.stats import norm

        mean, std = self.predict(X)
        p = norm.cdf(np.asarray((hi - mean) / std, dtype=float)) - norm.cdf(
            np.asarray((lo - mean) / std, dtype=float))
        return pd.Series(np.asarray(p, dtype=float), index=X.index).clip(0.0, 1.0)
