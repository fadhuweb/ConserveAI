"""Re-package the production model with isotonic vegetation calibration.

The shared rf_self model already ranks all three threats well, but Platt
calibration compresses the moderate-AUC vegetation probability to ~base rate
(flat on the dashboard). This swaps ONLY the vegetation calibrator to isotonic
(which preserves spread), keeping the original Platt calibrators for fire and
drought. No retraining, no architecture change.

Run:  python -m src.models.recalibrate_production
"""

import pickle
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))   # src/models (model_utils, evaluate)
sys.path.insert(0, str(ROOT))                              # repo root (src.models.per_threat_model)

from model_utils import LABEL_COLS, load_splits, prep_arrays, build_eval_dicts
from evaluate import evaluate_model
from src.models.per_threat_model import IsotonicCalibrator

RF_SELF  = ROOT / "results" / "models" / "rf_self" / "model.pkl"
PROD_DIR = ROOT / "results" / "production"


def run():
    artefact = pickle.load(open(RF_SELF, "rb"))
    model, imputer = artefact["model"], artefact["imputer"]
    calibrators = list(artefact["calibrators"])          # [fire(Platt), drought(Platt), veg(Platt)]

    _, val_df, test_df = load_splits()
    X_val, Y_val, _ = prep_arrays(val_df, imputer)

    veg_i = LABEL_COLS.index("vegetation_within_30d")
    val_raw = np.column_stack([p[:, 1] for p in model.predict_proba(X_val)])
    calibrators[veg_i] = IsotonicCalibrator().fit(val_raw[:, veg_i], Y_val[:, veg_i])  # swap veg only

    new_artefact = {"model": model, "imputer": imputer, "calibrators": calibrators}

    # validate on test
    X_test, Y_test, _ = prep_arrays(test_df, imputer)
    test_raw = np.column_stack([p[:, 1] for p in model.predict_proba(X_test)])
    test_cal = np.column_stack([
        calibrators[i].predict_proba(test_raw[:, i:i + 1])[:, 1] for i in range(len(LABEL_COLS))
    ])
    yt, yp = build_eval_dicts(test_cal, Y_test)
    mets = evaluate_model(yt, yp)

    print("=== re-packaged production model (test) ===")
    for i, L in enumerate(LABEL_COLS):
        print(f"  {L:24s} F2={mets[L]['f2']:.3f}  AUC={mets[L]['roc_auc']:.3f}  | "
              f"pred std={test_cal[:, i].std():.3f}  med={np.median(test_cal[:, i]):.2f}")
    print(f"  mean-F2 = {np.mean([mets[L]['f2'] for L in LABEL_COLS]):.3f}")

    pickle.dump(new_artefact, open(RF_SELF, "wb"))
    PROD_DIR.mkdir(parents=True, exist_ok=True)
    pickle.dump(new_artefact, open(PROD_DIR / "model.pkl", "wb"))
    print(f"\nsaved -> {RF_SELF}\n     -> {PROD_DIR / 'model.pkl'}")


if __name__ == "__main__":
    run()
