"""Train supervised XGBoost classifiers for multi-threat forecasting.

Three separate binary XGBClassifiers, one per threat, with scale_pos_weight
tuned per threat.

Outputs:
  results/models/xgb_supervised/model.pkl
  results/models/xgb_supervised/hyperparameters.json
  results/models/xgb_supervised/test_metrics.json
"""

import json
import pickle
import sys
from itertools import product
from pathlib import Path

import numpy as np
from xgboost import XGBClassifier

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate import evaluate_model
from model_utils import (
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

XGB_MODEL_DIR = MODELS_DIR / "xgb_supervised"

XGB_PARAM_GRID = {
    "n_estimators": [200, 300],
    "max_depth": [4, 6],
    "learning_rate": [0.05, 0.1],
}


def compute_scale_pos_weight(Y_train: np.ndarray) -> list[float]:
    weights = []
    for i in range(Y_train.shape[1]):
        n_pos = Y_train[:, i].sum()
        n_neg = len(Y_train) - n_pos
        weights.append(float(n_neg / n_pos) if n_pos > 0 else 1.0)
    return weights


def predict_proba_xgb(models: list, X: np.ndarray) -> np.ndarray:
    return np.column_stack([m.predict_proba(X)[:, 1] for m in models])


def train_xgboost(X_train, Y_train, X_val, Y_val):
    spw = compute_scale_pos_weight(Y_train)
    print(f"  scale_pos_weight per threat: {[f'{w:.2f}' for w in spw]}")

    best_score = -1.0
    best_params = {}
    best_models = None

    keys = list(XGB_PARAM_GRID.keys())
    vals = list(XGB_PARAM_GRID.values())

    for combo in product(*vals):
        params = dict(zip(keys, combo))
        models = []
        val_probs_list = []

        for i in range(Y_train.shape[1]):
            xgb = XGBClassifier(
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
            xgb.fit(X_train, Y_train[:, i].astype(int))
            val_probs_list.append(xgb.predict_proba(X_val)[:, 1])
            models.append(xgb)

        val_probs_arr = np.column_stack(val_probs_list)
        score = mean_f2(val_probs_arr, Y_val)
        print(f"  XGB {params} -> val mean-F2={score:.4f}")

        if score > best_score:
            best_score = score
            best_params = params
            best_models = models

    print(f"Best XGB params: {best_params}, val mean-F2={best_score:.4f}")
    return best_models, best_params


def run():
    ensure_dirs()
    XGB_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading data...")
    train_df, val_df, test_df = load_splits()
    print(f"  train={len(train_df)} val={len(val_df)} test={len(test_df)}")

    X_train, Y_train, imputer = prep_arrays(train_df)
    X_val, Y_val, _ = prep_arrays(val_df, imputer)
    X_test, Y_test, _ = prep_arrays(test_df, imputer)

    print("\n=== XGBoost ===")
    xgb_models, best_params = train_xgboost(X_train, Y_train, X_val, Y_val)

    val_probs_raw = predict_proba_xgb(xgb_models, X_val)
    scalers = fit_platt_scalers(val_probs_raw, Y_val)
    val_probs = apply_platt(val_probs_raw, scalers)

    test_probs_raw = predict_proba_xgb(xgb_models, X_test)
    test_probs = apply_platt(test_probs_raw, scalers)

    yt_d, yp_d = build_eval_dicts(test_probs, Y_test)
    test_metrics = evaluate_model(yt_d, yp_d)

    yt_d_val, yp_d_val = build_eval_dicts(val_probs, Y_val)
    val_metrics = evaluate_model(yt_d_val, yp_d_val, include_bootstrap=False, include_lead_time=False)

    results = {
        "model": "xgb_supervised",
        "best_params": best_params,
        "val_mean_f2": mean_f2(val_probs, Y_val),
        "test_mean_f2": float(np.mean([test_metrics[l]["f2"] for l in LABEL_COLS])),
        "val_metrics": val_metrics,
        "test_metrics": test_metrics,
        "per_park_test": per_park_metrics(test_df, test_probs, evaluate_model),
    }

    with open(RESULTS_DIR / "xgb_supervised_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    with open(XGB_MODEL_DIR / "test_metrics.json", "w") as f:
        json.dump(test_metrics, f, indent=2, default=str)

    with open(XGB_MODEL_DIR / "hyperparameters.json", "w") as f:
        json.dump(best_params, f, indent=2)

    with open(XGB_MODEL_DIR / "model.pkl", "wb") as f:
        pickle.dump({"models": xgb_models, "imputer": imputer, "calibrators": scalers}, f)

    print("\nXGB Test Results:")
    for label in LABEL_COLS:
        m = test_metrics[label]
        ci = m["bootstrap_f2"]
        print(f"  {label}: F2={m['f2']:.4f} "
              f"(95% CI [{ci['ci_lower']:.4f}, {ci['ci_upper']:.4f}])  "
              f"persist_F2={m['persistence_f2']:.4f}  beats={m['beats_baseline']}")

    print(f"\nTest mean-F2: {results['test_mean_f2']:.4f}")
    print("Saved to results/models/xgb_supervised/")


if __name__ == "__main__":
    run()