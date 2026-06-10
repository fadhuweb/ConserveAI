"""Feature-contribution 'drivers' for a forecast (the lightweight, non-SHAP view).

For each threat we report a curated set of the engineered features that drive it,
their current values, and whether each is currently raising or lowering the risk.
This is transparent and fast — no model inference needed beyond the feature values.
"""

import pandas as pd

from src.backend.jobs.daily_forecast import _compute_features, FEATURE_COLS

# (feature_key, human label, unit, direction)
#   direction: "low"    → a low value raises the threat (vs THRESHOLDS)
#              "high"   → a high value raises the threat (vs THRESHOLDS)
#              "lowval" → a negative value raises the threat (deficit / decline)
#              "bool"   → 1 raises the threat
DRIVER_SPECS = {
    "fire": [
        ("rain_30d",        "30-day rainfall",        "mm",   "low"),
        ("temp_max_30d",    "Avg max temperature",    "degC", "high"),
        ("days_since_fire", "Days since last fire",   "days", "low"),
        ("dry_season",      "Dry season",             "bool", "high"),
    ],
    "drought": [
        ("rain_30d",         "30-day rainfall",        "mm", "low"),
        ("rain_deficit_30d", "Rainfall deficit (30d)", "mm", "lowval"),
        ("rain_60d",         "60-day rainfall",        "mm", "low"),
        ("dry_season",       "Dry season",             "bool", "high"),
    ],
    "vegetation": [
        ("ndvi",            "Vegetation index (NDVI)", "ndvi", "low"),
        ("ndvi_deviation",  "NDVI vs 90-day normal",   "ndvi", "lowval"),
        ("ndvi_change_30d", "NDVI change (30d)",       "ndvi", "lowval"),
        ("rain_30d",        "30-day rainfall",         "mm",   "low"),
    ],
}

THRESHOLDS = {"rain_30d": 20.0, "rain_60d": 50.0, "temp_max_30d": 34.0, "days_since_fire": 30.0}


def _fmt(value, unit):
    if unit == "mm":   return f"{value:.1f} mm"
    if unit == "degC": return f"{value:.1f} °C"
    if unit == "days": return f"{int(value)} days"
    if unit == "ndvi": return f"{value:.2f}"
    if unit == "bool": return "Yes" if value >= 0.5 else "No"
    return f"{value:.2f}"


def _impact(feat, value, direction):
    if direction == "bool":   return "raises" if value >= 0.5 else "lowers"
    if direction == "lowval": return "raises" if value < 0 else "lowers"
    if direction == "low":    return "raises" if value < THRESHOLDS.get(feat, 0) else "lowers"
    if direction == "high":   return "raises" if value > THRESHOLDS.get(feat, 0) else "lowers"
    return "lowers"


def compute_drivers(history: pd.DataFrame, park: str, target_date) -> dict:
    """Return {threat: [{label, value, impact}, ...]} for the latest feature row."""
    feats = _compute_features(history, park, target_date)[0]
    fdict = dict(zip(FEATURE_COLS, feats))

    drivers = {}
    for threat, specs in DRIVER_SPECS.items():
        items = []
        for feat, label, unit, direction in specs:
            v = float(fdict.get(feat, 0.0))
            items.append({
                "label":  label,
                "value":  _fmt(v, unit),
                "impact": _impact(feat, v, direction),
            })
        drivers[threat] = items
    return drivers
