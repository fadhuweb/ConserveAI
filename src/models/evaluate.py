"""Shared evaluation utilities for supervised classifiers."""

import numpy as np
from sklearn.metrics import (
    precision_score,
    recall_score,
    fbeta_score,
    brier_score_loss,
    roc_auc_score,
    average_precision_score,
)


THREAT_LABELS = ["fire_within_30d", "drought_within_30d", "vegetation_within_30d"]
LEAD_THRESHOLD = 0.7
BOOTSTRAP_RESAMPLES = 1000


def compute_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> dict:
    """Return classification metrics for a single threat.

    F2 is the primary metric (beta=2, recall-weighted).
    """
    y_true = np.asarray(y_true, dtype=int)
    y_prob = np.asarray(y_prob, dtype=float)
    y_pred = (y_prob >= threshold).astype(int)

    n_pos = int(y_true.sum())
    n_neg = int((1 - y_true).sum())

    metrics = {
        "n": len(y_true),
        "n_pos": n_pos,
        "n_neg": n_neg,
        "prevalence": float(n_pos / len(y_true)) if len(y_true) > 0 else 0.0,
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f2": float(fbeta_score(y_true, y_pred, beta=2, zero_division=0)),
        "f1": float(fbeta_score(y_true, y_pred, beta=1, zero_division=0)),
        "brier": float(brier_score_loss(y_true, y_prob)),
    }

    if n_pos > 0 and n_neg > 0:
        metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob))
        metrics["pr_auc"] = float(average_precision_score(y_true, y_prob))
    else:
        metrics["roc_auc"] = float("nan")
        metrics["pr_auc"] = float("nan")

    return metrics


def compute_lead_time(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = LEAD_THRESHOLD) -> float:
    """Return mean days of advance warning across all positive-event onsets.

    A positive-event onset is the first day of each contiguous run of 1s in y_true.
    Lead time for a given onset = number of days before it that y_prob first crosses
    `threshold` (within the preceding 30-day window). Returns NaN if no onset found.
    """
    y_true = np.asarray(y_true, dtype=int)
    y_prob = np.asarray(y_prob, dtype=float)
    n = len(y_true)

    lead_times = []
    i = 0
    while i < n:
        if y_true[i] == 1 and (i == 0 or y_true[i - 1] == 0):
            # onset at index i — search backwards up to 30 days
            window_start = max(0, i - 30)
            for j in range(i - 1, window_start - 1, -1):
                if y_prob[j] >= threshold:
                    lead_times.append(i - j)
                    break
            else:
                lead_times.append(0)
        i += 1

    return float(np.mean(lead_times)) if lead_times else float("nan")


def compute_persistence_baseline(y_true: np.ndarray) -> dict:
    """Naive baseline: predict today's label as tomorrow's label.

    Uses the same metrics as compute_metrics for direct comparison.
    """
    y_true = np.asarray(y_true, dtype=int)
    if len(y_true) < 2:
        raise ValueError("Need at least 2 rows for persistence baseline.")

    y_true_shifted = y_true[1:]
    y_pred_persist = y_true[:-1]

    # Convert integer predictions to float probabilities for brier/auc
    y_prob_persist = y_pred_persist.astype(float)

    metrics = compute_metrics(y_true_shifted, y_prob_persist, threshold=0.5)
    metrics["model"] = "persistence"
    return metrics


def bootstrap_ci(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    metric_key: str = "f2",
    n_resamples: int = BOOTSTRAP_RESAMPLES,
    alpha: float = 0.05,
    threshold: float = 0.5,
    seed: int = 42,
) -> tuple[float, float, float]:
    """Return (point_estimate, lower_ci, upper_ci) via non-parametric bootstrap.

    Resamples rows with replacement and recomputes `metric_key` each time.
    """
    rng = np.random.default_rng(seed)
    y_true = np.asarray(y_true, dtype=int)
    y_prob = np.asarray(y_prob, dtype=float)
    n = len(y_true)

    point = compute_metrics(y_true, y_prob, threshold)[metric_key]

    boot_scores = []
    for _ in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        yt = y_true[idx]
        yp = y_prob[idx]
        if yt.sum() == 0 or yt.sum() == n:
            # degenerate resample — skip
            continue
        boot_scores.append(compute_metrics(yt, yp, threshold)[metric_key])

    if not boot_scores:
        return point, float("nan"), float("nan")

    lo = float(np.percentile(boot_scores, 100 * alpha / 2))
    hi = float(np.percentile(boot_scores, 100 * (1 - alpha / 2)))
    return point, lo, hi


def evaluate_model(
    y_true_dict: dict,
    y_prob_dict: dict,
    threat_labels: list[str] = THREAT_LABELS,
    threshold: float = 0.5,
    include_bootstrap: bool = True,
    include_lead_time: bool = True,
) -> dict:
    """Run full evaluation across all threats and return a nested results dict.

    Args:
        y_true_dict: {label: np.ndarray} for each threat
        y_prob_dict: {label: np.ndarray} of calibrated probabilities
        threshold: classification threshold for binary metrics
        include_bootstrap: add 95% CIs for F2 via bootstrap
        include_lead_time: add lead-time computation at LEAD_THRESHOLD

    Returns nested dict:
        {label: {metrics..., "bootstrap_f2": {...}, "lead_time_days": float}}
    """
    results = {}
    for label in threat_labels:
        y_true_raw = np.asarray(y_true_dict[label], dtype=float)
        y_prob = np.asarray(y_prob_dict[label], dtype=float)

        # drop rows where label is NaN (unlabeled rows)
        valid = ~np.isnan(y_true_raw)
        y_true = y_true_raw[valid].astype(int)
        y_prob = y_prob[valid]

        m = compute_metrics(y_true, y_prob, threshold)

        if include_bootstrap:
            f2_pt, f2_lo, f2_hi = bootstrap_ci(y_true, y_prob, metric_key="f2")
            m["bootstrap_f2"] = {"point": f2_pt, "ci_lower": f2_lo, "ci_upper": f2_hi}

        if include_lead_time:
            m["lead_time_days"] = compute_lead_time(y_true, y_prob)

        # persistence baseline for comparison
        persist = compute_persistence_baseline(y_true)
        m["persistence_f2"] = persist["f2"]
        m["beats_baseline"] = m["f2"] > persist["f2"]

        results[label] = m

    return results