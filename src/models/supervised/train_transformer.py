"""Train a supervised Transformer encoder for multi-threat forecasting.

Architecture: positional encoding → Transformer encoder → mean pooling →
dropout → 3 independent sigmoid heads.
Input: last 30 days of features per park-date row (seq_len × n_features).
Output: probability of fire / drought / vegetation degradation in next 30 days.

Outputs:
  results/models/transformer_supervised/model.pkl
  results/models/transformer_supervised/hyperparameters.json
  results/models/transformer_supervised/test_metrics.json
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
from seq_utils import SEQ_LEN, build_sequence_splits, compute_pos_weights

TRANSFORMER_MODEL_DIR = MODELS_DIR / "transformer_supervised"

HPARAMS = {
    "seq_len":        SEQ_LEN,
    "d_model":        64,
    "nhead":          4,
    "num_layers":     2,
    "dim_feedforward": 128,
    "dropout":        0.1,
    "lr":             1e-4,
    "weight_decay":   1e-3,
    "batch_size":     128,
    "max_epochs":     100,
    "es_patience":    15,
    "es_min_delta":   1e-4,
}


# ── Positional encoding ───────────────────────────────────────────────────────

class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 512, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(dropout)

        pe = torch.zeros(max_len, d_model)
        pos = torch.arange(0, max_len).unsqueeze(1).float()
        div = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(pos * div)
        pe[:, 1::2] = torch.cos(pos * div)
        self.register_buffer("pe", pe.unsqueeze(0))   # (1, max_len, d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dropout(x + self.pe[:, : x.size(1)])


# ── Model ─────────────────────────────────────────────────────────────────────

class ThreatTransformer(nn.Module):
    def __init__(self, n_features: int, d_model: int = 64, nhead: int = 4,
                 num_layers: int = 2, dim_feedforward: int = 128,
                 dropout: float = 0.1, n_threats: int = 3):
        super().__init__()
        self.input_proj = nn.Linear(n_features, d_model)
        self.pos_enc    = PositionalEncoding(d_model, dropout=dropout)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model         = d_model,
            nhead           = nhead,
            dim_feedforward = dim_feedforward,
            dropout         = dropout,
            batch_first     = True,
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.drop    = nn.Dropout(dropout)
        self.heads   = nn.ModuleList([nn.Linear(d_model, 1) for _ in range(n_threats)])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.pos_enc(self.input_proj(x))   # (B, seq_len, d_model)
        x = self.encoder(x)                    # (B, seq_len, d_model)
        x = self.drop(x.mean(dim=1))           # (B, d_model) — mean pooling
        return torch.cat([h(x) for h in self.heads], dim=1)   # (B, 3) logits


# ── Loss (shared logic with LSTM) ─────────────────────────────────────────────

def masked_weighted_bce(logits: torch.Tensor, targets: torch.Tensor,
                        pos_weights: torch.Tensor) -> torch.Tensor:
    """Weighted BCE summed across threats; NaN positions are masked out."""
    total = torch.tensor(0.0, device=logits.device)
    for i in range(targets.shape[1]):
        mask = ~torch.isnan(targets[:, i])
        if mask.sum() == 0:
            continue
        criterion = nn.BCEWithLogitsLoss(
            pos_weight=pos_weights[i].unsqueeze(0).to(logits.device)
        )
        total = total + criterion(logits[mask, i], targets[mask, i])
    return total


# ── Early stopping ────────────────────────────────────────────────────────────

class EarlyStopping:
    def __init__(self, patience: int = 15, min_delta: float = 1e-4):
        self.patience   = patience
        self.min_delta  = min_delta
        self.best_loss  = float("inf")
        self.counter    = 0
        self.best_state = None

    def step(self, val_loss: float, model: nn.Module) -> bool:
        if val_loss < self.best_loss - self.min_delta:
            self.best_loss  = val_loss
            self.counter    = 0
            self.best_state = {k: v.clone() for k, v in model.state_dict().items()}
        else:
            self.counter += 1
        return self.counter >= self.patience


# ── Training loop ─────────────────────────────────────────────────────────────

def train_transformer(X_train, Y_train, X_val, Y_val, device: torch.device):
    torch.manual_seed(SEED)
    n_features = X_train.shape[2]
    pw = torch.tensor(compute_pos_weights(Y_train))

    model = ThreatTransformer(
        n_features      = n_features,
        d_model         = HPARAMS["d_model"],
        nhead           = HPARAMS["nhead"],
        num_layers      = HPARAMS["num_layers"],
        dim_feedforward = HPARAMS["dim_feedforward"],
        dropout         = HPARAMS["dropout"],
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

    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Training on {device}  |  {len(X_train)} train  {len(X_val)} val")
    print(f"  Architecture: Transformer d_model={HPARAMS['d_model']} "
          f"nhead={HPARAMS['nhead']} layers={HPARAMS['num_layers']} "
          f"ffn={HPARAMS['dim_feedforward']}  params={n_params:,}")

    for epoch in range(1, HPARAMS["max_epochs"] + 1):
        model.train()
        epoch_loss = 0.0
        for xb, yb in train_loader:
            xb, yb = xb.to(device), yb.to(device)
            optimizer.zero_grad()
            logits = model(xb)
            loss   = masked_weighted_bce(logits, yb, pw)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            epoch_loss += loss.item() * len(xb)
        epoch_loss /= len(X_train)

        model.eval()
        with torch.no_grad():
            val_logits = model(X_val_t)
            val_loss   = masked_weighted_bce(val_logits, Y_val_t, pw).item()

        if epoch % 10 == 0 or epoch == 1:
            print(f"  epoch {epoch:3d}  train_loss={epoch_loss:.4f}  val_loss={val_loss:.4f}")

        if stopper.step(val_loss, model):
            print(f"  Early stopping at epoch {epoch}  (best val_loss={stopper.best_loss:.4f})")
            break

    if stopper.best_state is not None:
        model.load_state_dict(stopper.best_state)

    return model


# ── Inference ─────────────────────────────────────────────────────────────────

@torch.no_grad()
def predict_proba(model: ThreatTransformer, X: np.ndarray, device: torch.device,
                  batch_size: int = 512) -> np.ndarray:
    model.eval()
    probs = []
    for start in range(0, len(X), batch_size):
        xb     = torch.from_numpy(X[start : start + batch_size]).to(device)
        logits = model(xb)
        probs.append(torch.sigmoid(logits).cpu().numpy())
    return np.vstack(probs).astype(np.float32)


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    ensure_dirs()
    TRANSFORMER_MODEL_DIR.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    print("\nBuilding sequences...")
    (imputer,
     X_train, Y_train, parks_train,
     X_val,   Y_val,   parks_val,
     X_test,  Y_test,  parks_test) = build_sequence_splits()

    print("\n=== Transformer ===")
    model = train_transformer(X_train, Y_train, X_val, Y_val, device)

    # Calibration
    val_probs_raw  = predict_proba(model, X_val, device)
    scalers        = fit_platt_scalers(val_probs_raw, Y_val)
    val_probs      = apply_platt(val_probs_raw, scalers)

    test_probs_raw = predict_proba(model, X_test, device)
    test_probs     = apply_platt(test_probs_raw, scalers)

    # Overall evaluation
    yt_d, yp_d         = build_eval_dicts(test_probs, Y_test)
    test_metrics        = evaluate_model(yt_d, yp_d)

    yt_d_val, yp_d_val = build_eval_dicts(val_probs, Y_val)
    val_metrics         = evaluate_model(yt_d_val, yp_d_val,
                                         include_bootstrap=False,
                                         include_lead_time=False)

    # Per-park evaluation
    per_park = {}
    for park in np.unique(parks_test):
        mask = parks_test == park
        yt_p, yp_p = build_eval_dicts(test_probs[mask], Y_test[mask])
        per_park[park] = evaluate_model(yt_p, yp_p,
                                        include_bootstrap=False,
                                        include_lead_time=False)

    results = {
        "model":         "transformer_supervised",
        "hparams":       HPARAMS,
        "val_mean_f2":   mean_f2(val_probs, Y_val),
        "test_mean_f2":  float(np.mean([test_metrics[l]["f2"] for l in LABEL_COLS])),
        "val_metrics":   val_metrics,
        "test_metrics":  test_metrics,
        "per_park_test": per_park,
    }

    with open(RESULTS_DIR / "transformer_supervised_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    with open(TRANSFORMER_MODEL_DIR / "test_metrics.json", "w") as f:
        json.dump(test_metrics, f, indent=2, default=str)
    with open(TRANSFORMER_MODEL_DIR / "hyperparameters.json", "w") as f:
        json.dump(HPARAMS, f, indent=2)
    with open(TRANSFORMER_MODEL_DIR / "model.pkl", "wb") as f:
        pickle.dump({
            "model_state": model.state_dict(),
            "model_config": {
                "n_features":      X_train.shape[2],
                "d_model":         HPARAMS["d_model"],
                "nhead":           HPARAMS["nhead"],
                "num_layers":      HPARAMS["num_layers"],
                "dim_feedforward": HPARAMS["dim_feedforward"],
                "dropout":         HPARAMS["dropout"],
            },
            "imputer":     imputer,
            "calibrators": scalers,
        }, f)

    print("\nTransformer Test Results:")
    for label in LABEL_COLS:
        m  = test_metrics[label]
        ci = m["bootstrap_f2"]
        print(f"  {label}: F2={m['f2']:.4f} "
              f"(95% CI [{ci['ci_lower']:.4f}, {ci['ci_upper']:.4f}])  "
              f"persist_F2={m['persistence_f2']:.4f}  beats={m['beats_baseline']}")

    print(f"\nTest mean-F2: {results['test_mean_f2']:.4f}")
    print("Saved to results/models/transformer_supervised/")


if __name__ == "__main__":
    run()