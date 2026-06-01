"""Re-run inference on saved models and update results JSONs with new metrics.

Loads each model's .pkl, runs test-set inference (no retraining), calls
evaluate_model() with the current evaluate.py, and overwrites the results JSON.

Run once after adding new metrics to evaluate.py:
    python src/models/recompute_metrics.py
"""

import json
import pickle
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluate import evaluate_model
from model_utils import (
    LABEL_COLS,
    MODELS_DIR,
    RESULTS_DIR,
    apply_platt,
    build_eval_dicts,
    load_splits,
    mean_f2,
    per_park_metrics,
    prep_arrays,
)
from seq_utils import build_sequence_splits
from supervised.train_lstm import ThreatLSTM, predict_proba as lstm_predict
from supervised.train_transformer import ThreatTransformer, predict_proba as tf_predict


def _eval_full(probs, Y, df_test, include_bootstrap=True):
    yt_d, yp_d  = build_eval_dicts(probs, Y)
    test_metrics = evaluate_model(yt_d, yp_d, include_bootstrap=include_bootstrap)
    per_park     = per_park_metrics(df_test, probs, evaluate_model)
    return test_metrics, per_park


def _eval_seq(probs, Y_test, parks_test, include_bootstrap=True):
    yt_d, yp_d  = build_eval_dicts(probs, Y_test)
    test_metrics = evaluate_model(yt_d, yp_d, include_bootstrap=include_bootstrap)
    per_park = {}
    for park in np.unique(parks_test):
        mask = parks_test == park
        yt_p, yp_p = build_eval_dicts(probs[mask], Y_test[mask])
        per_park[park] = evaluate_model(yt_p, yp_p,
                                        include_bootstrap=False, include_lead_time=False)
    return test_metrics, per_park


def _update_json(path: Path, test_metrics, per_park):
    with open(path) as f:
        results = json.load(f)
    results["test_metrics"]  = test_metrics
    results["test_mean_f2"]  = float(np.mean([test_metrics[l]["f2"] for l in LABEL_COLS]))
    results["per_park_test"] = per_park
    with open(path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  Updated {path.name}")


# ── Load test data once ───────────────────────────────────────────────────────
print("Loading test data...")
_, _, test_df = load_splits()

print("Building sequence test split...")
(*_, X_test_seq, Y_test_seq, parks_test_seq) = build_sequence_splits()

device = torch.device("cpu")

# ── Tree models ───────────────────────────────────────────────────────────────
TREE_MODELS = [
    ("rf_supervised",  "rf",  RESULTS_DIR / "rf_supervised_results.json"),
    ("rf_self",        "rf",  RESULTS_DIR / "rf_self_results.json"),
    ("xgb_supervised", "xgb", RESULTS_DIR / "xgb_supervised_results.json"),
    ("xgb_self",       "xgb", RESULTS_DIR / "xgb_self_results.json"),
]

for model_dir, kind, json_path in TREE_MODELS:
    pkl = MODELS_DIR / model_dir / "model.pkl"
    if not pkl.exists() or not json_path.exists():
        print(f"  Skipping {model_dir} — files not found.")
        continue
    print(f"\n{model_dir}")
    with open(pkl, "rb") as f:
        b = pickle.load(f)
    X_test, Y_test, _ = prep_arrays(test_df, b["imputer"])
    if kind == "rf":
        raw = np.column_stack([p[:, 1] for p in b["model"].predict_proba(X_test)])
    else:
        raw = np.column_stack([m.predict_proba(X_test)[:, 1] for m in b["models"]])
    probs = apply_platt(raw, b["calibrators"])
    tm, pp = _eval_full(probs, Y_test, test_df)
    _update_json(json_path, tm, pp)

# ── Neural models ─────────────────────────────────────────────────────────────
NEURAL_MODELS = [
    ("lstm_supervised",        "lstm",        RESULTS_DIR / "lstm_supervised_results.json"),
    ("lstm_fixmatch",          "lstm",        RESULTS_DIR / "lstm_fixmatch_results.json"),
    ("transformer_supervised", "transformer", RESULTS_DIR / "transformer_supervised_results.json"),
    ("transformer_fixmatch",   "transformer", RESULTS_DIR / "transformer_fixmatch_results.json"),
]

for model_dir, kind, json_path in NEURAL_MODELS:
    pkl = MODELS_DIR / model_dir / "model.pkl"
    if not pkl.exists() or not json_path.exists():
        print(f"  Skipping {model_dir} — files not found.")
        continue
    print(f"\n{model_dir}")
    with open(pkl, "rb") as f:
        b = pickle.load(f)
    if kind == "lstm":
        model = ThreatLSTM(**b["model_config"])
        model.load_state_dict(b["model_state"])
        raw = lstm_predict(model, X_test_seq, device)
    else:
        model = ThreatTransformer(**b["model_config"])
        model.load_state_dict(b["model_state"])
        raw = tf_predict(model, X_test_seq, device)
    probs = apply_platt(raw, b["calibrators"])
    tm, pp = _eval_seq(probs, Y_test_seq, parks_test_seq)
    _update_json(json_path, tm, pp)

print("\nDone — all results JSONs updated.")