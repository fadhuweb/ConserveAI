"""Train supervised Random Forest for multi-threat forecasting.

Outputs:
  results/models/rf_supervised/model.pkl
  results/models/rf_supervised/hyperparameters.json
  results/models/rf_supervised/test_metrics.json
"""

import json
import pickle
import sys
from itertools import product
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier

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

RF_MODEL_DIR = MODELS_DIR / "rf_supervised"

RF_PARAM_GRID = {
    "n_estimators": [200, 300],
    "max_depth": [None, 20],
    "min_samples_leaf": [1, 5],
}


def train_random_forest(X_train, Y_train, X_val, Y_val):
    best_score = -1.0
    best_params = {}
    best_model = None

    keys = list(RF_PARAM_GRID.keys())
    vals = list(RF_PARAM_GRID.values())

    for combo in product(*vals):
        params = dict(zip(keys, combo))
        rf = RandomForestClassifier(
            **params,
            class_weight="balanced",
            n_jobs=-1,
            random_state=SEED,
        )
        rf.fit(X_train, Y_train)
        val_probs_raw = np.column_stack([p[:, 1] for p in rf.predict_proba(X_val)])
        score = mean_f2(val_probs_raw, Y_val)
        print(f"  RF {params} -> val mean-F2={score:.4f}")
        if score > best_score:
            best_score = score
            best_params = params
            best_model = rf

    print(f"Best RF params: {best_params}, val mean-F2={best_score:.4f}")
    return best_model, best_params


def run():
    ensure_dirs()
    RF_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading data...")
    train_df, val_df, test_df = load_splits()
    print(f"  train={len(train_df)} val={len(val_df)} test={len(test_df)}")

    X_train, Y_train, imputer = prep_arrays(train_df)
    X_val, Y_val, _ = prep_arrays(val_df, imputer)
    X_test, Y_test, _ = prep_arrays(test_df, imputer)

    print("\n=== Random Forest ===")
    rf, best_params = train_random_forest(X_train, Y_train, X_val, Y_val)

    val_probs_raw = np.column_stack([p[:, 1] for p in rf.predict_proba(X_val)])
    scalers = fit_platt_scalers(val_probs_raw, Y_val)
    val_probs = apply_platt(val_probs_raw, scalers)

    test_probs_raw = np.column_stack([p[:, 1] for p in rf.predict_proba(X_test)])
    test_probs = apply_platt(test_probs_raw, scalers)

    yt_d, yp_d = build_eval_dicts(test_probs, Y_test)
    test_metrics = evaluate_model(yt_d, yp_d)

    yt_d_val, yp_d_val = build_eval_dicts(val_probs, Y_val)
    val_metrics = evaluate_model(yt_d_val, yp_d_val, include_bootstrap=False, include_lead_time=False)

    results = {
        "model": "rf_supervised",
        "best_params": best_params,
        "val_mean_f2": mean_f2(val_probs, Y_val),
        "test_mean_f2": float(np.mean([test_metrics[l]["f2"] for l in LABEL_COLS])),
        "val_metrics": val_metrics,
        "test_metrics": test_metrics,
        "per_park_test": per_park_metrics(test_df, test_probs, evaluate_model),
    }

    with open(RESULTS_DIR / "rf_supervised_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    with open(RF_MODEL_DIR / "test_metrics.json", "w") as f:
        json.dump(test_metrics, f, indent=2, default=str)

    with open(RF_MODEL_DIR / "hyperparameters.json", "w") as f:
        json.dump(best_params, f, indent=2)

    with open(RF_MODEL_DIR / "model.pkl", "wb") as f:
        pickle.dump({"model": rf, "imputer": imputer, "calibrators": scalers}, f)

    print("\nRF Test Results:")
    for label in LABEL_COLS:
        m = test_metrics[label]
        ci = m["bootstrap_f2"]
        print(f"  {label}: F2={m['f2']:.4f} "
              f"(95% CI [{ci['ci_lower']:.4f}, {ci['ci_upper']:.4f}])  "
              f"persist_F2={m['persistence_f2']:.4f}  beats={m['beats_baseline']}")

    print(f"\nTest mean-F2: {results['test_mean_f2']:.4f}")
    print("Saved to results/models/rf_supervised/")


if __name__ == "__main__":
    run()