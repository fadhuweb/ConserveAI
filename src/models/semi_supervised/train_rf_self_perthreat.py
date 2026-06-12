"""Per-threat self-training Random Forests.

Unlike the shared multi-label RF (where the strong fire/drought labels dominate
the shared tree splits and vegetation collapses to its base rate), this trains
ONE specialist RandomForest per threat, each with its OWN self-training loop and
its OWN pseudo-labels. Vegetation can then learn the NDVI signal it was missing.

Algorithm (per threat, up to N_ITER rounds):
  1. Fit a supervised RF on that threat's labeled rows.
  2. Predict on the unlabeled pool (train rows with ndvi_missing==1).
  3. Add rows where max(p, 1-p) > CONF_THRESHOLD with a pseudo-label; retrain.
  4. Repeat until no new confident pseudo-labels.

Probabilities are Platt-calibrated per threat on the validation split. The three
fitted RFs are packaged in a PerThreatRF so the inference pipeline is unchanged.

Outputs:
  results/models/rf_self_perthreat/model.pkl
  results/models/rf_self_perthreat/test_metrics.json
"""

import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # src/models (evaluate, model_utils)
sys.path.insert(0, str(ROOT))                                  # repo root (src.models.per_threat_model)

from evaluate import evaluate_model
from model_utils import (
    DATA_PATH, FEATURE_COLS, LABEL_COLS, MODELS_DIR, SEED,
    build_eval_dicts, ensure_dirs, load_splits, prep_arrays,
)
from src.models.per_threat_model import PerThreatRF, IsotonicCalibrator

OUT_DIR        = MODELS_DIR / "rf_self_perthreat"
CONF_THRESHOLD = 0.9
N_ITER         = 5


def _params() -> dict:
    hp = MODELS_DIR / "rf_supervised" / "hyperparameters.json"
    if hp.exists():
        with open(hp) as f:
            p = json.load(f)
    else:
        p = {"n_estimators": 200, "max_depth": None, "min_samples_leaf": 5}
    p["max_depth"] = p.get("max_depth")   # JSON null -> None
    return p


def _fit(X, y, params) -> RandomForestClassifier:
    rf = RandomForestClassifier(**params, class_weight="balanced", n_jobs=-1, random_state=SEED)
    rf.fit(X, y.astype(int))
    return rf


def self_train_one(name, X_train, y_train, X_pool, params) -> RandomForestClassifier:
    valid  = ~np.isnan(y_train)
    X_lab  = X_train[valid]
    y_lab  = y_train[valid].astype(int)
    pool   = X_pool.copy()
    rf     = _fit(X_lab, y_lab, params)
    added  = 0

    for _ in range(N_ITER):
        if len(pool) == 0:
            break
        p    = rf.predict_proba(pool)[:, 1]
        conf = np.maximum(p, 1 - p)
        mask = conf > CONF_THRESHOLD
        if mask.sum() == 0:
            break
        pseudo = (p[mask] > 0.5).astype(int)
        X_lab  = np.vstack([X_lab, pool[mask]])
        y_lab  = np.concatenate([y_lab, pseudo])
        pool   = pool[~mask]
        added += int(mask.sum())
        rf     = _fit(X_lab, y_lab, params)

    print(f"  [{name:24s}] +{added} pseudo-labels | final train n={len(X_lab)}")
    return rf


def load_pool(imputer) -> np.ndarray:
    df = pd.read_csv(DATA_PATH)
    ul = df[(df["split"] == "train") & (df["ndvi_missing"] == 1)]
    if len(ul) == 0:
        return np.empty((0, len(FEATURE_COLS)), dtype=np.float32)
    return imputer.transform(ul[FEATURE_COLS]).astype(np.float32)


def run():
    ensure_dirs()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    params = _params()
    print(f"RF params: {params}")

    train_df, val_df, test_df = load_splits()
    X_train, Y_train, imputer = prep_arrays(train_df)
    X_val,   Y_val,   _       = prep_arrays(val_df,  imputer)
    X_test,  Y_test,  _       = prep_arrays(test_df, imputer)
    X_pool                    = load_pool(imputer)
    print(f"train={len(X_train)} val={len(X_val)} test={len(X_test)} pool={len(X_pool)}\n")

    print("=== Per-threat self-training ===")
    estimators = [self_train_one(LABEL_COLS[i], X_train, Y_train[:, i], X_pool, params)
                  for i in range(len(LABEL_COLS))]
    model = PerThreatRF(estimators)

    val_raw  = np.column_stack([est.predict_proba(X_val)[:, 1]  for est in estimators])
    test_raw = np.column_stack([est.predict_proba(X_test)[:, 1] for est in estimators])

    # Isotonic calibration per threat — preserves spread (Platt squashes moderate-AUC veg).
    calibrators = [IsotonicCalibrator().fit(val_raw[:, i], Y_val[:, i]) for i in range(len(LABEL_COLS))]
    test_probs = np.column_stack([
        calibrators[i].predict_proba(test_raw[:, i:i + 1])[:, 1] for i in range(len(LABEL_COLS))
    ])

    yt, yp = build_eval_dicts(test_probs, Y_test)
    test_metrics = evaluate_model(yt, yp)

    with open(OUT_DIR / "model.pkl", "wb") as f:
        pickle.dump({"model": model, "imputer": imputer, "calibrators": calibrators}, f)
    with open(OUT_DIR / "test_metrics.json", "w") as f:
        json.dump(test_metrics, f, indent=2, default=str)

    print("\n=== TEST RESULTS (per-threat self-trained) ===")
    for i, label in enumerate(LABEL_COLS):
        m  = test_metrics[label]
        sp = test_probs[:, i]
        print(f"  {label:24s} F2={m['f2']:.3f}  AUC={m['roc_auc']:.3f}  "
              f"recall={m['recall']:.3f}  prec={m['precision']:.3f}  | "
              f"pred std={sp.std():.3f} med={np.median(sp):.2f}")
    print(f"  mean-F2 = {np.mean([test_metrics[l]['f2'] for l in LABEL_COLS]):.3f}")
    print(f"\nsaved -> {OUT_DIR / 'model.pkl'}")


if __name__ == "__main__":
    run()
