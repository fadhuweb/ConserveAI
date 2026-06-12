"""Per-threat model container.

Holds one fitted classifier per threat (fire, drought, vegetation) and exposes
the same multi-output ``predict_proba`` interface as the old shared multi-label
RandomForest — i.e. it returns a list of (n, 2) probability arrays, one per
threat. This makes it a drop-in replacement in the inference pipeline
(``np.column_stack([p[:, 1] for p in model.predict_proba(X)])``), with NO change
to the daily-forecast or backfill jobs.

Kept dependency-free (numpy only) so it imports cleanly when the pickled
production model is loaded by the backend.
"""

import numpy as np
from sklearn.isotonic import IsotonicRegression


class PerThreatRF:
    def __init__(self, estimators):
        # estimators: fitted classifiers ordered [fire, drought, vegetation]
        self.estimators = list(estimators)

    def predict_proba(self, X):
        return [est.predict_proba(X) for est in self.estimators]

    def predict(self, X):
        return np.column_stack([est.predict(X) for est in self.estimators])


class IsotonicCalibrator:
    """Non-parametric probability calibrator that preserves spread (unlike Platt,
    which compresses moderate-AUC threats toward the base rate). Exposes the same
    ``predict_proba(col)[:, 1]`` interface the inference pipeline expects."""

    def __init__(self):
        self.iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)

    def fit(self, raw_col, y):
        raw = np.asarray(raw_col).ravel()
        y = np.asarray(y).ravel()
        valid = ~np.isnan(y)
        self.iso.fit(raw[valid], y[valid].astype(float))
        return self

    def predict_proba(self, X):
        col = np.asarray(X).ravel()
        c = np.clip(self.iso.predict(col), 0.0, 1.0)
        return np.column_stack([1.0 - c, c])
