"""FixMatch LSTM for multi-threat semi-supervised forecasting.

FixMatch applies two augmentation levels to each unlabeled sequence:
  - Weak:   Gaussian additive noise with std=WEAK_NOISE  (5%)
  - Strong: Gaussian additive noise with std=STRONG_NOISE (15%)

For each unlabeled mini-batch:
  1. Generate pseudo-labels from the model's weak-augmented predictions
     (no gradient through this step).
  2. Accept the pseudo-label if max(p_i, 1-p_i) > CONF_THRESHOLD for
     every threat i (all-threat confidence gate).
  3. Compute unweighted BCE between strong-augmented predictions and
     accepted pseudo-labels (consistency loss).
  4. Total loss = supervised_loss + LAMBDA_U * consistency_loss.

Augmentation choice: Gaussian additive noise with fixed std is the standard
tabular FixMatch recipe. Feature-wise normalised noise would be more principled
but would require a normalisation layer absent from the supervised baseline.
Values of 0.05 / 0.15 match the task specification.

Unlabeled pool: training-period sequences whose target row has ndvi_missing==1,
built with the same sliding-window logic as the supervised splits.

Outputs:
  results/models/lstm_fixmatch/model.pkl
  results/models/lstm_fixmatch/test_metrics.json
  results/lstm_fixmatch_results.json
"""

import json
import math
import pickle
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

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
    mean_f2,
)
from seq_utils import SEQ_LEN, build_sequence_splits, build_unlabeled_sequences, compute_pos_weights
from supervised.train_lstm import ThreatLSTM, EarlyStopping, masked_weighted_bce, predict_proba

LSTM_FM_DIR    = MODELS_DIR / "lstm_fixmatch"
CONF_THRESHOLD = 0.95
LAMBDA_U       = 1.0
WEAK_NOISE     = 0.05
STRONG_NOISE   = 0.15

HPARAMS = {
    "seq_len":        SEQ_LEN,
    "hidden_size":    64,
    "n_layers":       1,
    "dropout":        0.4,
    "lr":             1e-4,
    "weight_decay":   1e-3,
    "batch_size":     128,
    "max_epochs":     100,
    "es_patience":    15,
    "es_min_delta":   1e-4,
}


def consistency_loss(logits_s: torch.Tensor, pseudo: torch.Tensor) -> torch.Tensor:
    """Unweighted BCE between strong-aug predictions and pseudo-labels."""
    total = torch.tensor(0.0, device=logits_s.device)
    for i in range(pseudo.shape[1]):
        crit   = nn.BCEWithLogitsLoss()
        total += crit(logits_s[:, i], pseudo[:, i])
    return total


def train_fixmatch(X_train, Y_train, X_ul, X_val, Y_val, device: torch.device):
    torch.manual_seed(SEED)
    n_features = X_train.shape[2]
    pw = torch.tensor(compute_pos_weights(Y_train))

    model = ThreatLSTM(
        n_features  = n_features,
        hidden_size = HPARAMS["hidden_size"],
        n_layers    = HPARAMS["n_layers"],
        dropout     = HPARAMS["dropout"],
    ).to(device)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr           = HPARAMS["lr"],
        weight_decay = HPARAMS["weight_decay"],
    )

    train_ds     = TensorDataset(torch.from_numpy(X_train), torch.from_numpy(Y_train))
    train_loader = DataLoader(train_ds, batch_size=HPARAMS["batch_size"], shuffle=True)

    X_val_t = torch.from_numpy(X_val).to(device)
    Y_val_t = torch.from_numpy(Y_val).to(device)

    stopper = EarlyStopping(
        patience  = HPARAMS["es_patience"],
        min_delta = HPARAMS["es_min_delta"],
    )

    use_ul   = len(X_ul) > 0
    ul_idx   = np.arange(len(X_ul)) if use_ul else np.empty(0, dtype=int)
    bs       = HPARAMS["batch_size"]

    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Device: {device} | train={len(X_train)} val={len(X_val)} "
          f"unlabeled={len(X_ul)} | params={n_params:,}")
    if not use_ul:
        print("  Warning: empty unlabeled pool — running supervised-only training.")

    for epoch in range(1, HPARAMS["max_epochs"] + 1):
        model.train()
        np.random.shuffle(ul_idx)
        ul_ptr         = 0
        epoch_sup      = 0.0
        epoch_unsup    = 0.0

        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()

            loss_sup = masked_weighted_bce(model(xb), yb, pw)

            loss_unsup = torch.tensor(0.0, device=device)
            if use_ul:
                if ul_ptr + bs > len(ul_idx):
                    np.random.shuffle(ul_idx)
                    ul_ptr = 0
                batch_ul = torch.from_numpy(
                    X_ul[ul_idx[ul_ptr : ul_ptr + bs]]
                ).to(device)
                ul_ptr += bs

                X_weak   = batch_ul + torch.randn_like(batch_ul) * WEAK_NOISE
                X_strong = batch_ul + torch.randn_like(batch_ul) * STRONG_NOISE

                with torch.no_grad():
                    probs_w = torch.sigmoid(model(X_weak))  # (B, 3)

                conf  = torch.max(probs_w, 1 - probs_w)           # (B, 3)
                gate  = conf.min(dim=1).values > CONF_THRESHOLD   # (B,)

                if gate.sum() > 0:
                    pseudo         = (probs_w[gate] > 0.5).float()
                    logits_s_gated = model(X_strong)[gate]
                    loss_unsup     = consistency_loss(logits_s_gated, pseudo)

            total = loss_sup + LAMBDA_U * loss_unsup
            total.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            epoch_sup   += loss_sup.item()   * len(xb)
            epoch_unsup += loss_unsup.item() * len(xb)

        epoch_sup   /= len(X_train)
        epoch_unsup /= len(X_train)

        model.eval()
        with torch.no_grad():
            val_loss = masked_weighted_bce(model(X_val_t), Y_val_t, pw).item()

        if epoch % 10 == 0 or epoch == 1:
            print(f"  epoch {epoch:3d}  sup={epoch_sup:.4f}  "
                  f"unsup={epoch_unsup:.4f}  val={val_loss:.4f}")

        if stopper.step(val_loss, model):
            print(f"  Early stopping at epoch {epoch}  (best val={stopper.best_loss:.4f})")
            break

    if stopper.best_state is not None:
        model.load_state_dict(stopper.best_state)

    return model


def run():
    ensure_dirs()
    LSTM_FM_DIR.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    print("\nBuilding sequences...")
    (imputer,
     X_train, Y_train, parks_train,
     X_val,   Y_val,   parks_val,
     X_test,  Y_test,  parks_test) = build_sequence_splits()

    print("\nBuilding unlabeled pool...")
    X_ul = build_unlabeled_sequences(imputer=imputer)

    print("\n=== LSTM FixMatch ===")
    model = train_fixmatch(X_train, Y_train, X_ul, X_val, Y_val, device)

    val_probs_raw  = predict_proba(model, X_val, device)
    scalers        = fit_platt_scalers(val_probs_raw, Y_val)
    val_probs      = apply_platt(val_probs_raw, scalers)

    test_probs_raw = predict_proba(model, X_test, device)
    test_probs     = apply_platt(test_probs_raw, scalers)

    yt_d, yp_d   = build_eval_dicts(test_probs, Y_test)
    test_metrics  = evaluate_model(yt_d, yp_d)

    yt_v, yp_v   = build_eval_dicts(val_probs, Y_val)
    val_metrics   = evaluate_model(yt_v, yp_v, include_bootstrap=False, include_lead_time=False)

    per_park = {}
    for park in np.unique(parks_test):
        mask = parks_test == park
        yt_p, yp_p = build_eval_dicts(test_probs[mask], Y_test[mask])
        per_park[park] = evaluate_model(yt_p, yp_p,
                                        include_bootstrap=False, include_lead_time=False)

    results = {
        "model":          "lstm_fixmatch",
        "hparams":        HPARAMS,
        "conf_threshold": CONF_THRESHOLD,
        "lambda_u":       LAMBDA_U,
        "weak_noise":     WEAK_NOISE,
        "strong_noise":   STRONG_NOISE,
        "unlabeled_pool": len(X_ul),
        "val_mean_f2":    mean_f2(val_probs, Y_val),
        "test_mean_f2":   float(np.mean([test_metrics[l]["f2"] for l in LABEL_COLS])),
        "val_metrics":    val_metrics,
        "test_metrics":   test_metrics,
        "per_park_test":  per_park,
    }

    with open(RESULTS_DIR / "lstm_fixmatch_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    with open(LSTM_FM_DIR / "test_metrics.json", "w") as f:
        json.dump(test_metrics, f, indent=2, default=str)
    with open(LSTM_FM_DIR / "model.pkl", "wb") as f:
        pickle.dump({
            "model_state":  model.state_dict(),
            "model_config": {
                "n_features":  X_train.shape[2],
                "hidden_size": HPARAMS["hidden_size"],
                "n_layers":    HPARAMS["n_layers"],
                "dropout":     HPARAMS["dropout"],
            },
            "imputer":      imputer,
            "calibrators":  scalers,
        }, f)

    print("\nLSTM FixMatch Test Results:")
    for label in LABEL_COLS:
        m  = test_metrics[label]
        ci = m["bootstrap_f2"]
        print(f"  {label}: F2={m['f2']:.4f} "
              f"(95% CI [{ci['ci_lower']:.4f}, {ci['ci_upper']:.4f}])  "
              f"beats={m['beats_baseline']}")
    print(f"\nTest mean-F2: {results['test_mean_f2']:.4f}")
    print("Saved to results/models/lstm_fixmatch/")


if __name__ == "__main__":
    run()