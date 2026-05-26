"""Shared data loading, preprocessing, and calibration utilities."""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import fbeta_score

from evaluate import THREAT_LABELS

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "data" / "processed" / "featured_dataset.csv"
RESULTS_DIR = ROOT / "results"
MODELS_DIR = RESULTS_DIR / "models"

FEATURE_COLS = [
    # climate
    "rain_7d", "rain_30d", "rain_60d", "rain_deficit_30d",
    "temp_max_7d", "temp_max_30d", "hot_days_30d",
    # satellite
    "ndvi", "ndvi_30d_lag", "ndvi_change_30d", "ndvi_90d_avg", "ndvi_deviation",
    # fire history
    "fire_30d", "fire_90d", "days_since_fire",
    # context
    "doy_sin", "doy_cos", "dry_season", "park_id", "ecosystem_id",
]

LABEL_COLS = THREAT_LABELS
SEED = 42


def load_splits(path: Path = DATA_PATH) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(path)
    df = df[df["ndvi_missing"] == 0].copy()
    train = df[df["split"] == "train"].copy()
    val = df[df["split"] == "val"].copy()
    test = df[df["split"] == "test"].copy()
    return train, val, test


def prep_arrays(df: pd.DataFrame, imputer: SimpleImputer | None = None):
    X = df[FEATURE_COLS].copy()
    if imputer is None:
        imputer = SimpleImputer(strategy="median")
        X_arr = imputer.fit_transform(X)
    else:
        X_arr = imputer.transform(X)
    Y = df[LABEL_COLS].values.astype(float)
    return X_arr, Y, imputer


def _fit_temperature(val_probs: np.ndarray, val_labels: np.ndarray) -> float:
    """Find temperature T that minimises NLL on validation probabilities.

    Temperature scaling divides logits by T before the sigmoid.  T is always
    positive so it can only stretch or compress probabilities — it cannot
    invert the signal, unlike Platt scaling with a negative coefficient.
    """
    p = np.clip(val_probs, 1e-7, 1 - 1e-7)
    logits = np.log(p / (1 - p))
    y = val_labels.astype(float)

    def nll(T):
        p_scaled = np.clip(1 / (1 + np.exp(-logits / T)), 1e-7, 1 - 1e-7)
        return -float(np.mean(y * np.log(p_scaled) + (1 - y) * np.log(1 - p_scaled)))

    result = minimize_scalar(nll, bounds=(0.1, 10.0), method="bounded")
    return float(result.x)


def _apply_temperature(probs: np.ndarray, T: float) -> np.ndarray:
    p = np.clip(probs, 1e-7, 1 - 1e-7)
    logits = np.log(p / (1 - p))
    return (1 / (1 + np.exp(-logits / T))).astype(np.float32)


def fit_platt_scalers(val_probs: np.ndarray, val_labels: np.ndarray) -> list:
    """Fit one LogisticRegression calibrator per threat on validation probabilities.

    If the fitted coefficient is negative (signal inversion due to val/train
    distribution mismatch), falls back to temperature scaling, which can only
    stretch or compress probabilities and cannot invert them.
    """
    scalers = []
    for i in range(val_labels.shape[1]):
        lr = LogisticRegression(C=1e5, max_iter=500, solver="lbfgs")
        yt = val_labels[:, i]
        valid = ~np.isnan(yt)
        lr.fit(val_probs[valid, i].reshape(-1, 1), yt[valid].astype(int))
        if lr.coef_[0][0] <= 0:
            T = _fit_temperature(val_probs[valid, i], yt[valid])
            print(f"  [calibration] threat {i}: negative Platt coef ({lr.coef_[0][0]:.4f}), "
                  f"falling back to temperature scaling (T={T:.4f})")
            lr._passthrough = True
            lr._temperature = T
        else:
            lr._passthrough = False
            lr._temperature = None
        scalers.append(lr)
    return scalers


def apply_platt(raw_probs: np.ndarray, scalers: list) -> np.ndarray:
    cal = raw_probs.copy()
    for i, lr in enumerate(scalers):
        if getattr(lr, "_passthrough", False):
            T = getattr(lr, "_temperature", None)
            cal[:, i] = _apply_temperature(raw_probs[:, i], T) if T is not None else raw_probs[:, i]
        else:
            cal[:, i] = lr.predict_proba(raw_probs[:, i].reshape(-1, 1))[:, 1]
    return cal


def mean_f2(probs: np.ndarray, labels: np.ndarray) -> float:
    scores = []
    for i in range(labels.shape[1]):
        yt = labels[:, i].astype(int)
        yp = (probs[:, i] >= 0.5).astype(int)
        scores.append(fbeta_score(yt, yp, beta=2, zero_division=0))
    return float(np.mean(scores))


def build_eval_dicts(probs: np.ndarray, labels: np.ndarray) -> tuple[dict, dict]:
    y_true_dict = {col: labels[:, i] for i, col in enumerate(LABEL_COLS)}
    y_prob_dict = {col: probs[:, i] for i, col in enumerate(LABEL_COLS)}
    return y_true_dict, y_prob_dict


def per_park_metrics(df: pd.DataFrame, probs: np.ndarray, evaluate_fn) -> dict:
    results = {}
    parks = df["park"].values
    labels = df[LABEL_COLS].values.astype(float)
    for park in np.unique(parks):
        mask = parks == park
        yt_d, yp_d = build_eval_dicts(probs[mask], labels[mask])
        results[park] = evaluate_fn(yt_d, yp_d, include_bootstrap=False, include_lead_time=False)
    return results


def ensure_dirs():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)