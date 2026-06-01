"""Sequence building utilities for LSTM and Transformer models.

Converts the flat park-date dataset into sliding-window sequences.
Each target row becomes the last step of a seq_len-day window; the
30-day history is drawn from that park's sorted date index.

Shared by train_lstm.py and train_transformer.py.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer

from model_utils import DATA_PATH, FEATURE_COLS, LABEL_COLS

SEQ_LEN = 30


def _load_full(path: Path = DATA_PATH) -> pd.DataFrame:
    """Load dataset without the ndvi_missing filter, sorted by park + date.

    The original CSV row index is preserved in _orig_idx so that evaluation
    arrays can be reordered to match load_splits() (which reads the CSV as-is).
    """
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    df["_orig_idx"] = np.arange(len(df))
    return df.sort_values(["park", "date"]).reset_index(drop=True)


def _fit_imputer(df: pd.DataFrame) -> SimpleImputer:
    """Fit median imputer on clean training rows only."""
    train_clean = df[(df["split"] == "train") & (df["ndvi_missing"] == 0)]
    imp = SimpleImputer(strategy="median")
    imp.fit(train_clean[FEATURE_COLS])
    return imp


def build_sequence_splits(
    path: Path = DATA_PATH,
    seq_len: int = SEQ_LEN,
) -> tuple:
    """Build train / val / test sequence arrays.

    For each park, a sliding window of `seq_len` days is placed over every
    row where the target (last) row has ndvi_missing=0.  The sequence may
    include rows with ndvi_missing=1 in the look-back window — those feature
    values are imputed.

    Returns:
        imputer    — fitted SimpleImputer (needed at inference time)
        X_train    — (N_train, seq_len, n_features)  float32
        Y_train    — (N_train, n_labels)              float32, NaN where unlabeled
        X_val      — (N_val,   seq_len, n_features)  float32
        Y_val      — (N_val,   n_labels)              float32
        X_test     — (N_test,  seq_len, n_features)  float32
        Y_test     — (N_test,  n_labels)              float32
    """
    df = _load_full(path)
    imputer = _fit_imputer(df)

    # Pre-impute all feature rows once
    X_all = imputer.transform(df[FEATURE_COLS]).astype(np.float32)
    Y_all = df[LABEL_COLS].values.astype(np.float32)   # NaN preserved

    split_col  = df["split"].values
    ndvi_miss  = df["ndvi_missing"].values
    park_col   = df["park"].values
    orig_idx   = df["_orig_idx"].values

    # Four lists per split: X windows, Y labels, original CSV row index, park name
    buckets = {"train": ([], [], [], []), "val": ([], [], [], []), "test": ([], [], [], [])}

    for park in np.unique(park_col):
        mask = park_col == park
        idx  = np.where(mask)[0]          # global row indices for this park

        for local_i in range(seq_len - 1, len(idx)):
            global_i = idx[local_i]

            # Skip rows with missing NDVI at the target position
            if ndvi_miss[global_i] != 0:
                continue

            split = split_col[global_i]
            if split not in buckets:
                continue

            window = X_all[idx[local_i - seq_len + 1 : local_i + 1]]  # (seq_len, F)
            label  = Y_all[global_i]                                   # (n_labels,)

            buckets[split][0].append(window)
            buckets[split][1].append(label)
            buckets[split][2].append(orig_idx[global_i])
            buckets[split][3].append(park)

    result = {}
    for split, (xs, ys, oi, parks) in buckets.items():
        # Sort by original CSV row index so ordering matches load_splits()
        order = np.argsort(oi)
        result[f"X_{split}"]     = np.stack(xs)[order].astype(np.float32)
        result[f"Y_{split}"]     = np.stack(ys)[order].astype(np.float32)
        result[f"parks_{split}"] = np.array(parks)[order]

    print("Sequence splits built:")
    for split in ("train", "val", "test"):
        X = result[f"X_{split}"]
        Y = result[f"Y_{split}"]
        print(f"  {split:5s}  X={X.shape}  Y={Y.shape}")

    return (
        imputer,
        result["X_train"], result["Y_train"], result["parks_train"],
        result["X_val"],   result["Y_val"],   result["parks_val"],
        result["X_test"],  result["Y_test"],  result["parks_test"],
    )


def build_unlabeled_sequences(
    path: Path = DATA_PATH,
    seq_len: int = SEQ_LEN,
    imputer: SimpleImputer | None = None,
) -> np.ndarray:
    """Build sequences for the unlabeled pool used in FixMatch training.

    Unlabeled pool = training-period rows with ndvi_missing==1.  These rows
    are excluded from supervised training but their feature windows are usable
    for semi-supervised consistency training.

    Args:
        imputer: fitted SimpleImputer from build_sequence_splits(); if None a
                 new one is fitted (not recommended — share the supervised one).

    Returns:
        X_ul  — (N_ul, seq_len, n_features)  float32  (shape[0]==0 if pool is empty)
    """
    df = _load_full(path)
    if imputer is None:
        imputer = _fit_imputer(df)

    X_all     = imputer.transform(df[FEATURE_COLS]).astype(np.float32)
    split_col = df["split"].values
    ndvi_miss = df["ndvi_missing"].values
    park_col  = df["park"].values

    xs = []
    for park in np.unique(park_col):
        mask = park_col == park
        idx  = np.where(mask)[0]

        for local_i in range(seq_len - 1, len(idx)):
            global_i = idx[local_i]
            if split_col[global_i] != "train" or ndvi_miss[global_i] == 0:
                continue
            window = X_all[idx[local_i - seq_len + 1 : local_i + 1]]
            xs.append(window)

    if len(xs) == 0:
        print("  [unlabeled] No ndvi_missing==1 sequences in train split — pool is empty.")
        return np.empty((0, seq_len, len(FEATURE_COLS)), dtype=np.float32)

    X_ul = np.stack(xs).astype(np.float32)
    print(f"  [unlabeled] {len(X_ul)} sequences in unlabeled pool (ndvi_missing==1, split==train)")
    return X_ul


def compute_pos_weights(Y_train: np.ndarray) -> np.ndarray:
    """Return pos_weight per threat for weighted BCE loss.

    pos_weight = n_neg / n_pos, same logic as XGBoost scale_pos_weight.
    NaN rows are excluded from the count.
    """
    weights = []
    for i in range(Y_train.shape[1]):
        col = Y_train[:, i]
        valid = col[~np.isnan(col)]
        n_pos = float(valid.sum())
        n_neg = float(len(valid) - n_pos)
        weights.append(n_neg / n_pos if n_pos > 0 else 1.0)
    return np.array(weights, dtype=np.float32)