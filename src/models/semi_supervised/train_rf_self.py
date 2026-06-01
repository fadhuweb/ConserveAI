"""Self-training Random Forest for multi-threat semi-supervised forecasting.

Algorithm (up to N_ITER rounds):
  1. Start from the supervised RF best hyperparameters
     (loaded from results/models/rf_supervised/hyperparameters.json).
  2. Predict probabilities on the unlabeled pool.
  3. For each sample where max(p_i, 1-p_i) > CONF_THRESHOLD for every
     threat i, assign pseudo-labels and move to the labeled set.
  4. Retrain RF on labeled + pseudo-labeled set.
  5. Repeat until pool is exhausted or no new pseudo-labels are added.

Unlabeled pool: training-period rows with ndvi_missing==1 (NDVI sensor gaps).
Features are imputed with the median imputer fitted on clean training rows.

Requiring all three threats to be confident before adding a row ensures the
retrained model always receives NaN-free label arrays.

Outputs:
  results/models/rf_self/model.pkl
  results/models/rf_self/test_metrics.json
  results/rf_self_results.json
"""

import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

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

RF_SELF_DIR    = MODELS_DIR / "rf_self"
CONF_THRESHOLD = 0.9
N_ITER         = 5


def _load_best_params() -> dict:
    hp_path = MODELS_DIR / "rf_supervised" / "hyperparameters.json"
    if hp_path.exists():
        with open(hp_path) as f:
            return json.load(f)
    return {"n_estimators": 300, "max_depth": None, "min_samples_leaf": 1}


def load_unlabeled(imputer) -> np.ndarray:
    df = pd.read_csv(DATA_PATH)
    ul = df[(df["split"] == "train") & (df["ndvi_missing"] == 1)].copy()
    if len(ul) == 0:
        print("  [unlabeled] No ndvi_missing==1 rows in train split — pool is empty.")
        return np.empty((0, len(FEATURE_COLS)), dtype=np.float32)
    X_ul = imputer.transform(ul[FEATURE_COLS]).astype(np.float32)
    print(f"  [unlabeled] Pool: {len(X_ul)} rows (ndvi_missing==1, split==train)")
    return X_ul


def fit_rf(X: np.ndarray, Y: np.ndarray, params: dict) -> RandomForestClassifier:
    valid = ~np.any(np.isnan(Y), axis=1)
    rf = RandomForestClassifier(
        **params,
        class_weight="balanced",
        n_jobs=-1,
        random_state=SEED,
    )
    rf.fit(X[valid], Y[valid].astype(int))
    return rf


def get_probs(rf: RandomForestClassifier, X: np.ndarray) -> np.ndarray:
    return np.column_stack([p[:, 1] for p in rf.predict_proba(X)])


def run():
    ensure_dirs()
    RF_SELF_DIR.mkdir(parents=True, exist_ok=True)

    params = _load_best_params()
    print(f"RF params: {params}")

    train_df, val_df, test_df = load_splits()
    X_train, Y_train, imputer = prep_arrays(train_df)
    X_val,   Y_val,   _       = prep_arrays(val_df,  imputer)
    X_test,  Y_test,  _       = prep_arrays(test_df, imputer)

    X_ul = load_unlabeled(imputer)

    print("\n=== RF Self-Training ===")
    model = fit_rf(X_train, Y_train, params)

    X_lab = X_train.copy()
    Y_lab = Y_train.copy()
    added_total = 0

    for it in range(1, N_ITER + 1):
        if len(X_ul) == 0:
            print(f"  Iter {it}: unlabeled pool exhausted.")
            break

        probs_ul = get_probs(model, X_ul)
        conf     = np.maximum(probs_ul, 1 - probs_ul)     # (N, 3)
        mask     = np.all(conf > CONF_THRESHOLD, axis=1)  # all-threat gate
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
        model = fit_rf(X_lab, Y_lab, params)

    print(f"\n  Total pseudo-labels added: {added_total}")

    val_probs_raw  = get_probs(model, X_val)
    scalers        = fit_platt_scalers(val_probs_raw, Y_val)
    val_probs      = apply_platt(val_probs_raw, scalers)

    test_probs_raw = get_probs(model, X_test)
    test_probs     = apply_platt(test_probs_raw, scalers)

    yt_d, yp_d   = build_eval_dicts(test_probs, Y_test)
    test_metrics  = evaluate_model(yt_d, yp_d)

    yt_v, yp_v   = build_eval_dicts(val_probs, Y_val)
    val_metrics   = evaluate_model(yt_v, yp_v, include_bootstrap=False, include_lead_time=False)

    results = {
        "model":          "rf_self",
        "n_iter":         N_ITER,
        "conf_threshold": CONF_THRESHOLD,
        "added_total":    added_total,
        "val_mean_f2":    mean_f2(val_probs, Y_val),
        "test_mean_f2":   float(np.mean([test_metrics[l]["f2"] for l in LABEL_COLS])),
        "val_metrics":    val_metrics,
        "test_metrics":   test_metrics,
        "per_park_test":  per_park_metrics(test_df, test_probs, evaluate_model),
    }

    with open(RESULTS_DIR / "rf_self_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    with open(RF_SELF_DIR / "test_metrics.json", "w") as f:
        json.dump(test_metrics, f, indent=2, default=str)
    with open(RF_SELF_DIR / "model.pkl", "wb") as f:
        pickle.dump({"model": model, "imputer": imputer, "calibrators": scalers}, f)

    print("\nRF Self-Training Test Results:")
    for label in LABEL_COLS:
        m  = test_metrics[label]
        ci = m["bootstrap_f2"]
        print(f"  {label}: F2={m['f2']:.4f} "
              f"(95% CI [{ci['ci_lower']:.4f}, {ci['ci_upper']:.4f}])  "
              f"beats={m['beats_baseline']}")
    print(f"\nTest mean-F2: {results['test_mean_f2']:.4f}")
    print("Saved to results/models/rf_self/")


if __name__ == "__main__":
    run()