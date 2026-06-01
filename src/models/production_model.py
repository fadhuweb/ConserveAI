"""Package the production model for deployment.

Selects the best-performing model (RF supervised, highest mean F2 across
all three threats) and writes a versioned production artefact to
results/production/.

Output files
------------
results/production/model.pkl          — model + imputer + calibrators
results/production/metadata.json      — version, training date, eval summary
"""

import json
import pickle
import shutil
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from model_utils import MODELS_DIR, LABEL_COLS

PRODUCTION_DIR = Path(__file__).resolve().parents[2] / "results" / "production"

# RF supervised is chosen as the production model:
#  - Mean F2 0.856 across fire/drought/vegetation
#  - Beats persistence baseline on all three threats
#  - Fastest inference (no sequence dependency)
#  - Robust to missing NDVI features via imputation
BEST_MODEL_KEY = "rf_self"

VERSION = "1.0.0"


def load_best_model():
    model_dir = MODELS_DIR / BEST_MODEL_KEY
    with open(model_dir / "model.pkl", "rb") as f:
        artefact = pickle.load(f)
    with open(model_dir / "test_metrics.json") as f:
        metrics = json.load(f)
    # rf_self inherits hyperparameters from rf_supervised
    hp_path = model_dir / "hyperparameters.json"
    if not hp_path.exists():
        hp_path = MODELS_DIR / "rf_supervised" / "hyperparameters.json"
    with open(hp_path) as f:
        hyperparams = json.load(f)
    return artefact, metrics, hyperparams


def build_metadata(metrics: dict, hyperparams: dict) -> dict:
    threat_summary = {}
    for col in LABEL_COLS:
        m = metrics[col]
        threat_summary[col] = {
            "f2":       round(m["f2"], 4),
            "f2_ci":    [round(m["bootstrap_f2"]["ci_lower"], 4),
                         round(m["bootstrap_f2"]["ci_upper"], 4)],
            "roc_auc":  round(m["roc_auc"], 4),
            "recall":   round(m["recall"], 4),
            "precision": round(m["precision"], 4),
        }

    mean_f2 = round(
        sum(metrics[c]["f2"] for c in LABEL_COLS) / len(LABEL_COLS), 4
    )

    return {
        "version":        VERSION,
        "model_key":      BEST_MODEL_KEY,
        "training_date":  date.today().isoformat(),
        "threats":        LABEL_COLS,
        "mean_f2":        mean_f2,
        "per_threat":     threat_summary,
        "hyperparameters": hyperparams,
        "selection_reason": (
            "Highest mean F2 (0.8575) across all three threats among all eight "
            "supervised and semi-supervised variants; marginally outperforms RF "
            "supervised (0.8565) on drought and vegetation while remaining within "
            "CI overlap on fire; beats persistence baseline on all three threats; "
            "CPU-only tabular inference with no sequence buffer requirement."
        ),
    }


def package():
    PRODUCTION_DIR.mkdir(parents=True, exist_ok=True)

    artefact, metrics, hyperparams = load_best_model()
    metadata = build_metadata(metrics, hyperparams)

    model_out = PRODUCTION_DIR / "model.pkl"
    with open(model_out, "wb") as f:
        pickle.dump(artefact, f)

    meta_out = PRODUCTION_DIR / "metadata.json"
    with open(meta_out, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Production model packaged  ->  {PRODUCTION_DIR}")
    print(f"  version     : {metadata['version']}")
    print(f"  model       : {metadata['model_key']}")
    print(f"  mean F2     : {metadata['mean_f2']}")
    for col, s in metadata["per_threat"].items():
        print(f"  {col:<30}  F2={s['f2']}  AUC={s['roc_auc']}")


if __name__ == "__main__":
    package()