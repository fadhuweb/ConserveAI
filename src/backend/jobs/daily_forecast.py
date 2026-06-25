"""Daily forecast job — fetches live data, computes features, runs inference.

Flow (runs at 03:00 Lagos time via APScheduler):
    1. For each park:
       a. Fetch yesterday's climate from Open-Meteo (free, no auth)
       b. Fetch last 7 days fire counts from FIRMS REST API
       c. Fetch MODIS MOD09GA daily NDVI via GEE (500m, 1-2 day lag)
          → falls back to last known DB value if GEE unavailable or cloudy
       d. Append new row to daily_features table
       e. Load last 90 days → compute rolling features
       f. Run production model → save to forecasts table

Failures per park are caught and logged so one park failing cannot
prevent other parks from being updated.
"""

import logging
import os
import pickle
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import time

import numpy as np
import pandas as pd
import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

ROOT       = Path(__file__).resolve().parents[3]
PROD_MODEL = ROOT / "results" / "production" / "model.pkl"

load_dotenv(ROOT / ".env")

PARKS_CONFIG = {
    "yankari":       {"lat": 9.87,  "lon": 10.47, "dry_months": [11,12,1,2,3],    "park_id": 0, "ecosystem_id": 0,
                      "bbox": "9.6,9.3,11.0,10.3"},
    "cross_river":   {"lat": 5.92,  "lon": 8.72,  "dry_months": [11,12,1,2],      "park_id": 1, "ecosystem_id": 1,
                      "bbox": "8.3,5.5,9.2,6.4"},
    "gashaka_gumti": {"lat": 7.80,  "lon": 11.88, "dry_months": [11,12,1,2,3],    "park_id": 2, "ecosystem_id": 2,
                      "bbox": "11.0,6.9,12.6,8.6"},
    "kainji_lake":   {"lat": 10.32, "lon": 4.58,  "dry_months": [11,12,1,2,3,4],  "park_id": 3, "ecosystem_id": 0,
                      "bbox": "4.2,9.8,5.1,11.0"},
    "chad_basin":    {"lat": 12.87, "lon": 13.48, "dry_months": [10,11,12,1,2,3,4,5], "park_id": 4, "ecosystem_id": 3,
                      "bbox": "13.0,12.2,14.5,13.5"},
    "old_oyo":       {"lat": 8.37,  "lon": 3.92,  "dry_months": [11,12,1,2,3],    "park_id": 5, "ecosystem_id": 0,
                      "bbox": "3.5,8.0,4.5,8.8"},
}

FEATURE_COLS = [
    "rain_7d", "rain_30d", "rain_60d", "rain_deficit_30d",
    "temp_max_7d", "temp_max_30d", "hot_days_30d",
    "ndvi", "ndvi_30d_lag", "ndvi_change_30d", "ndvi_90d_avg", "ndvi_deviation",
    "fire_30d", "fire_90d", "days_since_fire",
    "doy_sin", "doy_cos", "dry_season", "park_id", "ecosystem_id",
]

# Minimum days of continuous history needed for reliable rolling features
# (rain_30d / rain_60d / ndvi_90d). Below this a forecast would be garbage, so skip it.
MIN_HISTORY_DAYS = 45


# ── Data fetchers ─────────────────────────────────────────────────────────────

def _fetch_climate(park: str, target_date: date) -> dict:
    """Fetch a single day's climate from Open-Meteo with retry on 429."""
    cfg    = PARKS_CONFIG[park]
    ds     = target_date.isoformat()
    params = {
        "latitude":   cfg["lat"],
        "longitude":  cfg["lon"],
        "start_date": ds,
        "end_date":   ds,
        "daily":      "precipitation_sum,temperature_2m_max,temperature_2m_min,"
                      "relative_humidity_2m_max,windspeed_10m_max",
        "timezone":   "Africa/Lagos",
    }
    for attempt in range(4):
        resp = requests.get("https://archive-api.open-meteo.com/v1/archive", params=params, timeout=30)
        if resp.status_code == 429:
            wait = 2 ** attempt
            logger.warning("Open-Meteo rate limit for %s — retrying in %ds", park, wait)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        d = resp.json()["daily"]
        return {
            "precipitation":  d["precipitation_sum"][0],
            "temp_max":       d["temperature_2m_max"][0],
            "temp_min":       d["temperature_2m_min"][0],
            "humidity_max":   d["relative_humidity_2m_max"][0],
            "wind_speed_max": d["windspeed_10m_max"][0],
        }
    raise RuntimeError(f"Open-Meteo rate limit exceeded for {park} after 4 attempts")


# Near-real-time first (recent dates), then standard/archived (older dates).
FIRMS_PRODUCTS = ["VIIRS_SNPP_NRT", "VIIRS_SNPP_SP"]


def _firms_count_for_product(api_key: str, bbox: str, target_date: date, product: str) -> Optional[int]:
    """Fire-detection count for one FIRMS product, or None if it doesn't serve this date.

    The area API returns a plain-text error (not CSV) for unsupported date/product
    combos, so we only count when the response is a real CSV (starts with 'latitude').
    """
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{api_key}/{product}/{bbox}/7/{target_date.isoformat()}"
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        text = resp.text.strip()
        if not text.lower().startswith("latitude"):
            return None                          # error message, not CSV → product can't serve this date
        return sum(1 for l in text.splitlines() if l and not l.startswith("latitude"))
    except Exception:
        return None


def _fetch_firms(park: str, target_date: date) -> int:
    """Count fire detections in the last 7 days from FIRMS.

    Tries near-real-time first, falling back to the standard/archived product so the
    live job stays robust at the ~2-month NRT boundary. Returns 0 if neither serves
    this date (e.g. genuinely no fires, or a date older than both products cover)."""
    api_key = os.getenv("NASA_FIRMS_API_KEY", "").strip()
    if not api_key:
        logger.warning("NASA_FIRMS_API_KEY not set — using 0 for firms_count")
        return 0

    bbox = PARKS_CONFIG[park]["bbox"]   # "west,south,east,north"
    for product in FIRMS_PRODUCTS:
        count = _firms_count_for_product(api_key, bbox, target_date, product)
        if count is not None:
            return count

    logger.warning("FIRMS unavailable for %s on %s (no product served it) — defaulting to 0",
                   park, target_date.isoformat())
    return 0


def _init_gee() -> bool:
    """Initialise GEE using service account from env, or interactive auth as fallback.
    Returns True if successful."""
    try:
        import ee
        project  = os.getenv("GEE_PROJECT", "")
        sa_email = os.getenv("GEE_SERVICE_ACCOUNT", "")
        key_file = os.getenv("GEE_KEY_FILE", "")
        key_data = os.getenv("GEE_KEY_DATA", "")   # raw JSON content (for headless/Fly secrets)

        if sa_email and key_data:
            credentials = ee.ServiceAccountCredentials(sa_email, key_data=key_data)
            ee.Initialize(credentials, project=project)
        elif sa_email and key_file and Path(key_file).exists():
            credentials = ee.ServiceAccountCredentials(sa_email, key_file)
            ee.Initialize(credentials, project=project)
        else:
            ee.Initialize(project=project or None)
        return True
    except Exception:
        logger.warning("GEE initialisation failed — NDVI will use DB fallback")
        return False


def _fetch_modis_ndvi(park: str, target_date: date) -> Optional[float]:
    """Fetch mean NDVI from MODIS MOD09GA (500m daily) via GEE.

    Uses a 3-day window around target_date to handle cloud cover and the
    1-2 day data processing lag.  Returns None if GEE is unavailable or
    all pixels are cloudy — caller falls back to last DB value.
    """
    try:
        import ee
        cfg  = PARKS_CONFIG[park]
        bbox = [float(v) for v in cfg["bbox"].split(",")]  # west, south, east, north
        geometry = ee.Geometry.Rectangle(bbox)

        # 3-day window: target_date-1 to target_date+2
        start = (target_date - timedelta(days=1)).isoformat()
        end   = (target_date + timedelta(days=2)).isoformat()

        collection = (
            ee.ImageCollection("MODIS/061/MOD09GA")
            .filterBounds(geometry)
            .filterDate(start, end)
        )

        def add_ndvi(image):
            nir  = image.select("sur_refl_b02")
            red  = image.select("sur_refl_b01")
            ndvi = nir.subtract(red).divide(nir.add(red)).rename("ndvi")
            # Mask cloudy pixels using state_1km QA band (bits 0-1 == 00 = clear)
            qa   = image.select("state_1km")
            clear = qa.bitwiseAnd(3).eq(0)
            return ndvi.updateMask(clear)

        ndvi_col = collection.map(add_ndvi)
        composite = ndvi_col.mean()

        result = composite.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=500,
            maxPixels=1e9,
        ).getInfo()

        val = result.get("ndvi")
        if val is None:
            logger.debug("MODIS NDVI returned null for %s (cloudy window) — using DB fallback", park)
            return None

        logger.debug("MODIS NDVI  park=%-18s  ndvi=%.4f", park, val)
        return round(float(val), 4)

    except Exception:
        logger.warning("MODIS NDVI fetch failed for %s — using DB fallback", park)
        return None


def _get_ndvi(park: str, target_date: date, db) -> Optional[float]:
    """Get NDVI for target_date: try MODIS GEE first, fall back to last DB value."""
    from src.backend.models.raw_features import DailyFeatures

    # Try MODIS first
    ndvi = _fetch_modis_ndvi(park, target_date)
    if ndvi is not None:
        return ndvi

    # Fall back to last known value in DB (forward-fill up to 16 days — MODIS max gap)
    cutoff = target_date - timedelta(days=16)
    row = (
        db.query(DailyFeatures)
        .filter(
            DailyFeatures.park == park,
            DailyFeatures.ndvi.isnot(None),
            DailyFeatures.date >= cutoff,
        )
        .order_by(DailyFeatures.date.desc())
        .first()
    )
    if row:
        logger.debug("NDVI fallback  park=%-18s  using value from %s", park, row.date)
        return row.ndvi
    return None


# ── Feature engineering ───────────────────────────────────────────────────────

def _compute_features(history: pd.DataFrame, park: str, target_date: date) -> np.ndarray:
    """Given 90 days of raw history, compute the 20 model features for target_date."""
    cfg = PARKS_CONFIG[park]
    df  = history.sort_values("date").copy()
    df["date"] = pd.to_datetime(df["date"])
    df  = df.set_index("date")

    precip   = df["precipitation"].fillna(0)
    temp_max = df["temp_max"]
    ndvi_raw = df["ndvi"]
    fire     = df["firms_count"].fillna(0)

    # NDVI forward-fill up to 7 days then treat as missing
    ndvi_filled = ndvi_raw.ffill(limit=7)

    row = {}

    # Climate rolling
    row["rain_7d"]          = precip.rolling(7,  min_periods=1).sum().iloc[-1]
    row["rain_30d"]         = precip.rolling(30, min_periods=1).sum().iloc[-1]
    row["rain_60d"]         = precip.rolling(60, min_periods=1).sum().iloc[-1]
    monthly_avg             = precip.groupby(precip.index.month).mean()
    expected_30d            = precip.index[-1:].month.map(monthly_avg).values[0] * 30
    row["rain_deficit_30d"] = float(row["rain_30d"]) - float(expected_30d)
    row["temp_max_7d"]      = temp_max.rolling(7,  min_periods=1).mean().iloc[-1]
    row["temp_max_30d"]     = temp_max.rolling(30, min_periods=1).mean().iloc[-1]
    row["hot_days_30d"]     = float((temp_max > 35).astype(float).rolling(30, min_periods=1).sum().iloc[-1])

    # NDVI
    row["ndvi"]             = float(ndvi_filled.iloc[-1]) if not pd.isna(ndvi_filled.iloc[-1]) else 0.0
    row["ndvi_30d_lag"]     = float(ndvi_filled.shift(30).iloc[-1]) if len(ndvi_filled) > 30 else row["ndvi"]
    row["ndvi_change_30d"]  = row["ndvi"] - row["ndvi_30d_lag"]
    row["ndvi_90d_avg"]     = float(ndvi_filled.rolling(90, min_periods=1).mean().iloc[-1])
    row["ndvi_deviation"]   = row["ndvi"] - row["ndvi_90d_avg"]

    # Fire
    row["fire_30d"]         = float(fire.rolling(30, min_periods=1).sum().iloc[-1])
    row["fire_90d"]         = float(fire.rolling(90, min_periods=1).sum().iloc[-1])
    fire_detected           = fire > 0
    last_fire               = df.index[fire_detected].max() if fire_detected.any() else None
    row["days_since_fire"]  = float(min((pd.Timestamp(target_date) - last_fire).days, 365)) if last_fire else 365.0

    # Context
    doy                     = pd.Timestamp(target_date).dayofyear
    row["doy_sin"]          = float(np.sin(2 * np.pi * doy / 365.25))
    row["doy_cos"]          = float(np.cos(2 * np.pi * doy / 365.25))
    row["dry_season"]       = float(pd.Timestamp(target_date).month in cfg["dry_months"])
    row["park_id"]          = float(cfg["park_id"])
    row["ecosystem_id"]     = float(cfg["ecosystem_id"])

    return np.array([[row[f] for f in FEATURE_COLS]], dtype=float)


# ── Main job ──────────────────────────────────────────────────────────────────

def _process_park(park: str, target_date: date, artefact: dict) -> Optional[dict]:
    """Fetch, compute features, and run inference for one park. Returns result dict or None."""
    from src.backend.database import SessionLocal
    from src.backend.models.raw_features import DailyFeatures

    model       = artefact["model"]
    imputer     = artefact["imputer"]
    calibrators = artefact.get("calibrators")

    db = SessionLocal()
    try:
        climate = _fetch_climate(park, target_date)
        firms   = _fetch_firms(park, target_date)
        ndvi    = _get_ndvi(park, target_date, db)

        existing = db.query(DailyFeatures).filter(
            DailyFeatures.park == park, DailyFeatures.date == target_date
        ).first()
        if not existing:
            db.add(DailyFeatures(
                park=park, date=target_date,
                precipitation=climate["precipitation"],
                temp_max=climate["temp_max"],
                temp_min=climate["temp_min"],
                humidity_max=climate["humidity_max"],
                wind_speed_max=climate["wind_speed_max"],
                ndvi=ndvi,
                firms_count=firms,
            ))
            db.commit()

        cutoff = target_date - timedelta(days=90)
        rows   = (
            db.query(DailyFeatures)
            .filter(DailyFeatures.park == park, DailyFeatures.date >= cutoff)
            .order_by(DailyFeatures.date)
            .all()
        )
        history = pd.DataFrame([{
            "date":          r.date,
            "precipitation": r.precipitation,
            "temp_max":      r.temp_max,
            "temp_min":      r.temp_min,
            "ndvi":          r.ndvi,
            "firms_count":   r.firms_count or 0,
        } for r in rows])

        # Guard: without enough continuous history the rolling features (rain_30d/60d,
        # ndvi_90d) are meaningless and the model produces garbage. Skip instead.
        if len(history) < MIN_HISTORY_DAYS:
            logger.warning(
                "Skipping %s on %s — only %d days of history (need %d); a forecast here "
                "would be unreliable. Fill the data gap first.",
                park, target_date, len(history), MIN_HISTORY_DAYS,
            )
            return None

        X      = _compute_features(history, park, target_date)
        X_imp  = imputer.transform(pd.DataFrame(X, columns=FEATURE_COLS))
        raw_p  = np.column_stack([p[:, 1] for p in model.predict_proba(X_imp)])

        if calibrators:
            probs = np.column_stack([
                calibrators[i].predict_proba(raw_p[:, i:i+1])[:, 1]
                for i in range(raw_p.shape[1])
            ])
        else:
            probs = raw_p

        probs = np.clip(probs, 0, 1)
        logger.info("Forecast OK  park=%-18s  fire=%.3f  drought=%.3f  veg=%.3f",
                    park, probs[0,0], probs[0,1], probs[0,2])
        return {"fire": float(probs[0,0]), "drought": float(probs[0,1]), "vegetation": float(probs[0,2])}

    except Exception:
        logger.exception("Failed for park %s", park)
        return None
    finally:
        db.close()


def run_and_save(target_date: Optional[date] = None):
    """Run inference for all parks in parallel and save forecasts."""
    if target_date is None:
        target_date = date.today() - timedelta(days=1)

    from concurrent.futures import ThreadPoolExecutor, as_completed
    from src.backend.database import SessionLocal
    from src.backend.models.forecast import Forecast

    try:
        with open(PROD_MODEL, "rb") as f:
            artefact = pickle.load(f)
    except Exception:
        logger.exception("Failed to load production model")
        return {}

    _init_gee()   # initialise once — threads share the session

    results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(_process_park, park, target_date, artefact): park
                   for park in PARKS_CONFIG}
        for future in as_completed(futures):
            park = futures[future]
            result = future.result()
            if result:
                results[park] = result

    # Save all results to DB in one transaction
    db = SessionLocal()
    try:
        for park, vals in results.items():
            if not db.query(Forecast).filter(
                Forecast.park == park, Forecast.date == target_date
            ).first():
                db.add(Forecast(
                    park=park, date=target_date,
                    fire_prob=vals["fire"],
                    drought_prob=vals["drought"],
                    veg_prob=vals["vegetation"],
                    computed_at=datetime.now(timezone.utc),
                ))
        db.commit()
        logger.info("Daily job complete — %d/%d parks saved.", len(results), len(PARKS_CONFIG))
    except Exception:
        db.rollback()
        logger.exception("DB commit failed")
    finally:
        db.close()

    return results


def fill_range(start_date: date, end_date: date):
    """Repair a data gap: fetch + persist daily_features and (over)write forecasts for
    every date in [start_date, end_date], processed chronologically so each day's
    90-day rolling window is complete. Loads the model and GEE once."""
    from src.backend.database import SessionLocal
    from src.backend.models.forecast import Forecast

    try:
        with open(PROD_MODEL, "rb") as f:
            artefact = pickle.load(f)
    except Exception:
        logger.exception("Failed to load production model")
        return

    _init_gee()

    total = (end_date - start_date).days + 1
    d = start_date
    i = 0
    while d <= end_date:
        i += 1
        results = {}
        for park in PARKS_CONFIG:                 # sequential — gentler on the APIs/GEE
            r = _process_park(park, d, artefact)
            if r:
                results[park] = r

        db = SessionLocal()
        try:
            for park, vals in results.items():
                existing = db.query(Forecast).filter(
                    Forecast.park == park, Forecast.date == d
                ).first()
                if existing:
                    existing.fire_prob    = vals["fire"]
                    existing.drought_prob = vals["drought"]
                    existing.veg_prob     = vals["vegetation"]
                    existing.computed_at  = datetime.now(timezone.utc)
                else:
                    db.add(Forecast(
                        park=park, date=d,
                        fire_prob=vals["fire"], drought_prob=vals["drought"], veg_prob=vals["vegetation"],
                        computed_at=datetime.now(timezone.utc),
                    ))
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("save failed for %s", d)
        finally:
            db.close()

        logger.info("[%d/%d] filled %s — %d/%d parks", i, total, d, len(results), len(PARKS_CONFIG))
        d += timedelta(days=1)


def repredict_range(start_date: date, end_date: date):
    """Recompute forecasts from EXISTING daily_features (no API fetches) and update
    the forecasts table. Use after a model/calibration change — fast, since it only
    re-runs inference over data already in the DB."""
    from src.backend.database import SessionLocal
    from src.backend.models.forecast import Forecast
    from src.backend.models.raw_features import DailyFeatures

    try:
        with open(PROD_MODEL, "rb") as f:
            artefact = pickle.load(f)
    except Exception:
        logger.exception("Failed to load production model")
        return
    model       = artefact["model"]
    imputer     = artefact["imputer"]
    calibrators = artefact.get("calibrators")

    total = (end_date - start_date).days + 1
    d = start_date
    i = 0
    updated = 0
    while d <= end_date:
        i += 1
        db = SessionLocal()
        try:
            for park in PARKS_CONFIG:
                cutoff = d - timedelta(days=90)
                rows = (
                    db.query(DailyFeatures)
                    .filter(DailyFeatures.park == park, DailyFeatures.date >= cutoff, DailyFeatures.date <= d)
                    .order_by(DailyFeatures.date)
                    .all()
                )
                if len(rows) < MIN_HISTORY_DAYS:
                    continue
                history = pd.DataFrame([{
                    "date": r.date, "precipitation": r.precipitation, "temp_max": r.temp_max,
                    "temp_min": r.temp_min, "ndvi": r.ndvi, "firms_count": r.firms_count or 0,
                } for r in rows])

                X     = _compute_features(history, park, d)
                X_imp = imputer.transform(pd.DataFrame(X, columns=FEATURE_COLS))
                raw_p = np.column_stack([p[:, 1] for p in model.predict_proba(X_imp)])
                if calibrators:
                    probs = np.column_stack([
                        calibrators[k].predict_proba(raw_p[:, k:k+1])[:, 1] for k in range(raw_p.shape[1])
                    ])
                else:
                    probs = raw_p
                probs = np.clip(probs, 0, 1)

                fc = db.query(Forecast).filter(Forecast.park == park, Forecast.date == d).first()
                if fc:
                    fc.fire_prob    = float(probs[0, 0])
                    fc.drought_prob = float(probs[0, 1])
                    fc.veg_prob     = float(probs[0, 2])
                    fc.computed_at  = datetime.now(timezone.utc)
                    updated += 1
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("repredict failed for %s", d)
        finally:
            db.close()
        if i % 20 == 0 or i == total:
            logger.info("[%d/%d] repredicted up to %s (%d rows updated)", i, total, d, updated)
        d += timedelta(days=1)

    logger.info("Repredict complete — %d forecast rows updated.", updated)


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Daily forecast job / gap-fill / repredict")
    parser.add_argument("--fill-from", help="YYYY-MM-DD start date (gap-fill mode)")
    parser.add_argument("--fill-to",   help="YYYY-MM-DD end date (gap-fill mode)")
    parser.add_argument("--repredict-from", help="YYYY-MM-DD start (repredict from existing data)")
    parser.add_argument("--repredict-to",   help="YYYY-MM-DD end (repredict from existing data)")
    args = parser.parse_args()

    if args.fill_from and args.fill_to:
        fill_range(date.fromisoformat(args.fill_from), date.fromisoformat(args.fill_to))
    elif args.repredict_from and args.repredict_to:
        repredict_range(date.fromisoformat(args.repredict_from), date.fromisoformat(args.repredict_to))
    else:
        run_and_save()