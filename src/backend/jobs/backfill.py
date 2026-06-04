"""Backfill jobs — run once on first deploy.

Two steps:
    1. populate_daily_features(): migrate combined_dataset.csv → daily_features table
       (gives rolling feature computation 90+ days of history)
    2. run_backfill():            run inference on last N days → forecasts table

Run:
    python -m src.backend.jobs.backfill
"""

import logging
import pickle
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

ROOT       = Path(__file__).resolve().parents[3]
PROD_MODEL = ROOT / "results" / "production" / "model.pkl"
COMBINED   = ROOT / "data" / "processed" / "combined_dataset.csv"

PARKS = ["yankari", "cross_river", "gashaka_gumti", "kainji_lake", "chad_basin", "old_oyo"]

PARKS_CONFIG = {
    "yankari":       {"dry_months": [11,12,1,2,3],       "park_id": 0, "ecosystem_id": 0},
    "cross_river":   {"dry_months": [11,12,1,2],          "park_id": 1, "ecosystem_id": 1},
    "gashaka_gumti": {"dry_months": [11,12,1,2,3],        "park_id": 2, "ecosystem_id": 2},
    "kainji_lake":   {"dry_months": [11,12,1,2,3,4],      "park_id": 3, "ecosystem_id": 0},
    "chad_basin":    {"dry_months": [10,11,12,1,2,3,4,5], "park_id": 4, "ecosystem_id": 3},
    "old_oyo":       {"dry_months": [11,12,1,2,3],        "park_id": 5, "ecosystem_id": 0},
}

FEATURE_COLS = [
    "rain_7d", "rain_30d", "rain_60d", "rain_deficit_30d",
    "temp_max_7d", "temp_max_30d", "hot_days_30d",
    "ndvi", "ndvi_30d_lag", "ndvi_change_30d", "ndvi_90d_avg", "ndvi_deviation",
    "fire_30d", "fire_90d", "days_since_fire",
    "doy_sin", "doy_cos", "dry_season", "park_id", "ecosystem_id",
]


# ── Step 1: populate daily_features from CSV ──────────────────────────────────

def populate_daily_features():
    """Migrate combined_dataset.csv into the daily_features table."""
    from src.backend.database import SessionLocal
    from src.backend.models.raw_features import DailyFeatures

    if not COMBINED.exists():
        logger.error("combined_dataset.csv not found at %s", COMBINED)
        return 0

    df = pd.read_csv(COMBINED, parse_dates=["date"])
    db = SessionLocal()
    saved = 0

    try:
        for _, row in df.iterrows():
            park = row.get("park")
            if park not in PARKS:
                continue

            row_date = row["date"].date() if hasattr(row["date"], "date") else row["date"]

            exists = db.query(DailyFeatures).filter(
                DailyFeatures.park == park,
                DailyFeatures.date == row_date,
            ).first()
            if exists:
                continue

            db.add(DailyFeatures(
                park=park,
                date=row_date,
                precipitation=_safe(row.get("om_precipitation_sum")),
                temp_max=_safe(row.get("om_temperature_2m_max")),
                temp_min=_safe(row.get("om_temperature_2m_min")),
                humidity_max=_safe(row.get("om_relative_humidity_2m_max")),
                wind_speed_max=_safe(row.get("om_windspeed_10m_max")),
                ndvi=_safe(row.get("ndvi_s2")),
                firms_count=int(row["firms_count"]) if not pd.isna(row.get("firms_count", float("nan"))) else 0,
            ))
            saved += 1

            if saved % 5000 == 0:
                db.commit()
                logger.info("  %d rows committed...", saved)

        db.commit()
        logger.info("daily_features populated: %d rows.", saved)
    except Exception:
        db.rollback()
        logger.exception("populate_daily_features failed")
        raise
    finally:
        db.close()

    return saved


def _safe(val):
    if val is None:
        return None
    try:
        f = float(val)
        return None if np.isnan(f) else f
    except (TypeError, ValueError):
        return None


# ── Step 2: run inference on last N days ──────────────────────────────────────

def _compute_features(history: pd.DataFrame, park: str, target_date: date) -> np.ndarray:
    cfg = PARKS_CONFIG[park]
    df  = history.sort_values("date").copy()
    df["date"] = pd.to_datetime(df["date"])
    df  = df.set_index("date")

    precip      = df["precipitation"].fillna(0)
    temp_max    = df["temp_max"]
    ndvi_raw    = df["ndvi"]
    fire        = df["firms_count"].fillna(0)
    ndvi_filled = ndvi_raw.ffill(limit=7)

    row = {}
    row["rain_7d"]          = float(precip.rolling(7,  min_periods=1).sum().iloc[-1])
    row["rain_30d"]         = float(precip.rolling(30, min_periods=1).sum().iloc[-1])
    row["rain_60d"]         = float(precip.rolling(60, min_periods=1).sum().iloc[-1])
    monthly_avg             = precip.groupby(precip.index.month).mean()
    expected_30d            = float(precip.index[-1:].month.map(monthly_avg).values[0]) * 30
    row["rain_deficit_30d"] = row["rain_30d"] - expected_30d
    row["temp_max_7d"]      = float(temp_max.rolling(7,  min_periods=1).mean().iloc[-1])
    row["temp_max_30d"]     = float(temp_max.rolling(30, min_periods=1).mean().iloc[-1])
    row["hot_days_30d"]     = float((temp_max > 35).astype(float).rolling(30, min_periods=1).sum().iloc[-1])

    ndvi_val                = ndvi_filled.iloc[-1]
    row["ndvi"]             = float(ndvi_val) if not pd.isna(ndvi_val) else 0.0
    lag_val                 = ndvi_filled.shift(30).iloc[-1]
    row["ndvi_30d_lag"]     = float(lag_val) if not pd.isna(lag_val) else row["ndvi"]
    row["ndvi_change_30d"]  = row["ndvi"] - row["ndvi_30d_lag"]
    row["ndvi_90d_avg"]     = float(ndvi_filled.rolling(90, min_periods=1).mean().iloc[-1])
    row["ndvi_deviation"]   = row["ndvi"] - row["ndvi_90d_avg"]

    row["fire_30d"]         = float(fire.rolling(30, min_periods=1).sum().iloc[-1])
    row["fire_90d"]         = float(fire.rolling(90, min_periods=1).sum().iloc[-1])
    fire_detected           = fire > 0
    last_fire               = df.index[fire_detected].max() if fire_detected.any() else None
    row["days_since_fire"]  = float(min((pd.Timestamp(target_date) - last_fire).days, 365)) if last_fire else 365.0

    doy                     = pd.Timestamp(target_date).dayofyear
    row["doy_sin"]          = float(np.sin(2 * np.pi * doy / 365.25))
    row["doy_cos"]          = float(np.cos(2 * np.pi * doy / 365.25))
    row["dry_season"]       = float(pd.Timestamp(target_date).month in cfg["dry_months"])
    row["park_id"]          = float(cfg["park_id"])
    row["ecosystem_id"]     = float(cfg["ecosystem_id"])

    return np.array([[row[f] for f in FEATURE_COLS]], dtype=float)


def run_backfill(days: int = 60):
    """Run inference on the last `days` days and populate the forecasts table."""
    from src.backend.database import SessionLocal
    from src.backend.models.raw_features import DailyFeatures
    from src.backend.models.forecast import Forecast

    with open(PROD_MODEL, "rb") as f:
        artefact = pickle.load(f)
    model       = artefact["model"]
    imputer     = artefact["imputer"]
    calibrators = artefact.get("calibrators")

    db      = SessionLocal()
    saved   = 0

    # Use latest date in daily_features as end (CSV data may not reach today)
    latest = db.query(DailyFeatures.date).order_by(DailyFeatures.date.desc()).first()
    if latest is None:
        logger.error("daily_features is empty — run populate_daily_features first")
        db.close()
        return 0
    end   = latest[0]
    start = end - timedelta(days=days - 1)

    try:
        for park in PARKS:
            # Load 90-day context window for rolling feature computation
            context_start = start - timedelta(days=90)
            rows = (
                db.query(DailyFeatures)
                .filter(DailyFeatures.park == park, DailyFeatures.date >= context_start)
                .order_by(DailyFeatures.date)
                .all()
            )
            if not rows:
                logger.warning("No daily_features rows for park %s — skipping", park)
                continue

            history_full = pd.DataFrame([{
                "date":          r.date,
                "precipitation": r.precipitation,
                "temp_max":      r.temp_max,
                "temp_min":      r.temp_min,
                "ndvi":          r.ndvi,
                "firms_count":   r.firms_count or 0,
            } for r in rows])

            current = start
            while current <= end:
                # Skip if forecast already exists
                if db.query(Forecast).filter(
                    Forecast.park == park, Forecast.date == current
                ).first():
                    current += timedelta(days=1)
                    continue

                history = history_full[history_full["date"] <= current]
                if len(history) < 7:
                    current += timedelta(days=1)
                    continue

                try:
                    X     = _compute_features(history, park, current)
                    X_imp = imputer.transform(X)
                    raw_p = np.column_stack([p[:, 1] for p in model.predict_proba(X_imp)])

                    if calibrators:
                        probs = np.column_stack([
                            calibrators[i].predict_proba(raw_p[:, i:i+1])[:, 1]
                            for i in range(raw_p.shape[1])
                        ])
                    else:
                        probs = raw_p

                    probs = np.clip(probs, 0, 1)

                    db.add(Forecast(
                        park=park, date=current,
                        fire_prob=float(probs[0, 0]),
                        drought_prob=float(probs[0, 1]),
                        veg_prob=float(probs[0, 2]),
                        computed_at=datetime.utcnow(),
                    ))
                    saved += 1
                except Exception:
                    logger.exception("Inference failed for %s on %s", park, current)

                current += timedelta(days=1)

            logger.info("Park %-18s  backfill complete.", park)

        db.commit()
        logger.info("Backfill complete: %d forecast rows saved.", saved)
    except Exception:
        db.rollback()
        logger.exception("Backfill failed")
        raise
    finally:
        db.close()

    return saved


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=60, help="Days of forecast history to backfill")
    parser.add_argument("--features-only", action="store_true", help="Only populate daily_features, skip forecasts")
    args = parser.parse_args()

    logger.info("Step 1: Populating daily_features from combined_dataset.csv...")
    n = populate_daily_features()
    logger.info("  %d raw feature rows inserted.", n)

    if not args.features_only:
        logger.info("Step 2: Running inference for last %d days...", args.days)
        saved = run_backfill(days=args.days)
        logger.info("  %d forecast rows saved.", saved)