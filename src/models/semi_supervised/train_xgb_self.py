"""Self-training XGBoost for multi-threat semi-supervised forecasting.

Same algorithm as RF self-training but using three separate XGBClassifiers
(one per threat), consistent with the supervised XGBoost architecture.

Algorithm (up to N_ITER rounds):
  1. Start from the supervised XGB best hyperparameters
     (loaded from results/models/xgb_supervised/hyperparameters.json).
  2. Predict probabilities on the unlabeled pool.
  3. For each sample where max(p_i, 1-p_i) > CONF_THRESHOLD for every
     threat i, assign pseudo-labels and move to the labeled set.
  4. Retrain all three XGBClassifiers on labeled + pseudo-labeled set.
  5. Repeat until pool is exhausted or no new pseudo-labels are added.

Unlabeled pool: training-period rows with ndvi_missing==1 (NDVI sensor gaps).

Outputs:
  results/models/xgb_self/model.pkl
  results/models/xgb_self/test_metrics.json
  results/xgb_self_results.json
"""

import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate import evaluate_model
from model_utils import (
    DATA_PATH,
    FEATURE_COLS,
    LABEL_COLS,
    MODELS_DIR,
    RESULTS_DIR,
    SEED,
    apply_platt,
    build_eval_dicts,
    ensure_dirs,
    fit_platt_scalers,
    load_splits,
    mean_f2,
    per_park_metrics,
    prep_arrays,
)

XGB_SELF_DIR   = MODELS_DIR / "xgb_self"
CONF_THRESHOLD = 0.9
N_ITER         = 5


def _load_best_params() -> dict:
    hp_path = MODELS_DIR / "xgb_supervised" / "hyperparameters.json"
    if hp_path.exists():
        with open(hp_path) as f:
            return json.load(f)
    return {"n_estimators": 300, "max_depth": 6, "learning_rate": 0.1}


def load_unlabeled(imputer) -> np.ndarray:
    df = pd.read_csv(DATA_PATH)
    ul = df[(df["split"] == "train") & (df["ndvi_missing"] == 1)].copy()
    if len(ul) == 0:
        print("  [unlabeled] No ndvi_missing==1 rows in train split — pool is empty.")
        return np.empty((0, len(FEATURE_COLS)), dtype=np.float32)
    X_ul = imputer.transform(ul[FEATURE_COLS]).astype(np.float32)
    print(f"  [unlabeled] Pool: {len(X_ul)} rows (ndvi_missing==1, split==train)")
    return X_ul


def compute_spw(Y: np.ndarray) -> list[float]:
    weights = []
    for i in range(Y.shape[1]):
        col   = Y[:, i]
        valid = col[~np.isnan(col)]
        n_pos = float(valid.sum())
        n_neg = float(len(valid) - n_pos)
        weights.append(n_neg / n_pos if n_pos > 0 else 1.0)
    return weights


def fit_xgb(X: np.ndarray, Y: np.ndarray, params: dict) -> list[XGBClassifier]:
    spw    = compute_spw(Y)
    models = []
    for i in range(Y.shape[1]):
        col   = Y[:, i]
        valid = ~np.isnan(col)
        xgb   = XGBClassifier(
            **params,
            scale_pos_weight=spw[i],
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="logloss",
            verbosity=0,
            use_label_encoder=False,
            random_state=SEED,
            n_jobs=-1,
        )
        xgb.fit(X[valid], col[valid].astype(int))
        models.append(xgb)
    return models


def get_probs(models: list, X: np.ndarray) -> np.ndarray:
    return np.column_stack([m.predict_proba(X)[:, 1] for m in models])


def run():
    ensure_dirs()
    XGB_SELF_DIR.mkdir(parents=True, exist_ok=True)

    params = _load_best_params()
    print(f"XGB params: {params}")

    train_df, val_df, test_df = load_splits()
    X_train, Y_train, imputer = prep_arrays(train_df)
    X_val,   Y_val,   _       = prep_arrays(val_df,  imputer)
    X_test,  Y_test,  _       = prep_arrays(test_df, imputer)

    X_ul = load_unlabeled(imputer)

    print("\n=== XGBoost Self-Training ===")
    models = fit_xgb(X_train, Y_train, params)

    X_lab = X_train.copy()
    Y_lab = Y_train.copy()
    added_total = 0

    for it in range(1, N_ITER + 1):
        if len(X_ul) == 0:
            print(f"  Iter {it}: unlabeled pool exhausted.")
            break

        probs_ul = get_probs(models, X_ul)
        conf     = np.maximum(probs_ul, 1 - probs_ul)
        mask     = np.all(conf > CONF_THRESHOLD, axis=1)
        n_added  = int(mask.sum())

        if n_added == 0:
            print(f"  Iter {it}: no confident pseudo-labels (pool={len(X_ul)}). Stopping.")
            break

        pseudo_Y = (probs_ul[mask] > 0.5).astype(float)
        X_lab    = np.vstack([X_lab, X_ul[mask]])
        Y_lab    = np.vstack([Y_lab, pseudo_Y])
        X_ul     = X_ul[~mask]
        added_total += n_added

        print(f"  Iter {it}: +{n_added} pseudo-labels | pool={len(X_ul)} | labeled={len(X_lab)}")
        models = fit_xgb(X_lab, Y_lab, params)

    print(f"\n  Total pseudo-labels added: {added_total}")

    val_probs_raw  = get_probs(models, X_val)
    scalers        = fit_platt_scalers(val_probs_raw, Y_val)
    val_probs      = apply_platt(val_probs_raw, scalers)

    test_probs_raw = get_probs(models, X_test)
    test_probs     = apply_platt(test_probs_raw, scalers)

    yt_d, yp_d   = build_eval_dicts(test_probs, Y_test)
    test_metrics  = evaluate_model(yt_d, yp_d)

    yt_v, yp_v   = build_eval_dicts(val_probs, Y_val)
    val_metrics   = evaluate_model(yt_v, yp_v, include_bootstrap=False, include_lead_time=False)

    results = {
        "model":          "xgb_self",
        "n_iter":         N_ITER,
        "conf_threshold": CONF_THRESHOLD,
        "added_total":    added_total,
        "val_mean_f2":    mean_f2(val_probs, Y_val),
        "test_mean_f2":   float(np.mean([test_metrics[l]["f2"] for l in LABEL_COLS])),
        "val_metrics":    val_metrics,
        "test_metrics":   test_metrics,
        "per_park_test":  per_park_metrics(test_df, test_probs, evaluate_model),
    }

    with open(RESULTS_DIR / "xgb_self_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    with open(XGB_SELF_DIR / "test_metrics.json", "w") as f:
        json.dump(test_metrics, f, indent=2, default=str)
    with open(XGB_SELF_DIR / "model.pkl", "wb") as f:
        pickle.dump({"models": models, "imputer": imputer, "calibrators": scalers}, f)

    print("\nXGB Self-Training Test Results:")
    for label in LABEL_COLS:
        m  = test_metrics[label]
        ci = m["bootstrap_f2"]
        print(f"  {label}: F2={m['f2']:.4f} "
              f"(95% CI [{ci['ci_lower']:.4f}, {ci['ci_upper']:.4f}])  "
              f"beats={m['beats_baseline']}")
    print(f"\nTest mean-F2: {results['test_mean_f2']:.4f}")
    print("Saved to results/models/xgb_self/")


if __name__ == "__main__":
    run()