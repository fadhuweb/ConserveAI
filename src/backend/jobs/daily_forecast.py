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
from datetime import date, datetime, timedelta
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


def _fetch_firms(park: str, target_date: date) -> int:
    """Count fire detections in last 7 days from FIRMS REST API."""
    api_key = os.getenv("NASA_FIRMS_API_KEY", "")
    if not api_key:
        logger.warning("NASA_FIRMS_API_KEY not set — using 0 for firms_count")
        return 0

    cfg  = PARKS_CONFIG[park]
    bbox = cfg["bbox"]   # "west,south,east,north"
    url  = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{api_key}/VIIRS_SNPP_NRT/{bbox}/7/{target_date.isoformat()}"

    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        lines = [l for l in resp.text.strip().splitlines() if l and not l.startswith("latitude")]
        return len(lines)
    except Exception:
        logger.warning("FIRMS fetch failed for %s — defaulting to 0", park)
        return 0


def _init_gee() -> bool:
    """Initialise GEE using service account from env, or interactive auth as fallback.
    Returns True if successful."""
    try:
        import ee
        project  = os.getenv("GEE_PROJECT", "")
        sa_email = os.getenv("GEE_SERVICE_ACCOUNT", "")
        key_file = os.getenv("GEE_KEY_FILE", "")

        if sa_email and key_file and Path(key_file).exists():
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

        X      = _compute_features(history, park, target_date)
        X_imp  = imputer.transform(X)
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
        return

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
                    computed_at=datetime.utcnow(),
                ))
        db.commit()
        logger.info("Daily job complete — %d/%d parks saved.", len(results), len(PARKS_CONFIG))
    except Exception:
        db.rollback()
        logger.exception("DB commit failed")
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run_and_save()