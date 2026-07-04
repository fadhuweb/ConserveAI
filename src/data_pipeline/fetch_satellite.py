"""Fetch cloud-composited MODIS NDVI (MOD13Q1, 16-day, 250 m) via Google Earth Engine.

This replaces the earlier Sentinel-2 fetch. MOD13Q1 is a 16-day maximum-value composite
that already selects the best clear pixel per window, so it is far more robust to the
rainy-season cloud cover that left the optical Sentinel-2 series full of gaps. The live
serving pipeline reads MODIS too, so training and inference now share one source instead
of the previous Sentinel-2-vs-MODIS mismatch.

The output column keeps the name `ndvi_s2` for backward compatibility with the rest of
the pipeline (feature engineering, joins, labels); it now holds MOD13Q1 NDVI.
"""
import os
from pathlib import Path

import pandas as pd

from src.data_pipeline.config import PARKS, TRAIN_START, TRAIN_END, DATA_RAW
from src.utils.logging_config import get_logger

log = get_logger(__name__)

_COLLECTION = "MODIS/061/MOD13Q1"
_NDVI_SCALE = 0.0001   # MOD13Q1 NDVI is Int16 scaled by 1e-4


def _init_gee(project: str = None) -> None:
    """Initialise GEE with the service account from env (matches the backend), and
    fall back to application-default / interactive auth if those are not set."""
    import ee
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass
    project  = project or os.getenv("GEE_PROJECT", "") or None
    sa_email = os.getenv("GEE_SERVICE_ACCOUNT", "")
    key_file = os.getenv("GEE_KEY_FILE", "")
    key_data = os.getenv("GEE_KEY_DATA", "")
    if sa_email and key_data:
        ee.Initialize(ee.ServiceAccountCredentials(sa_email, key_data=key_data), project=project)
    elif sa_email and key_file and Path(key_file).exists():
        ee.Initialize(ee.ServiceAccountCredentials(sa_email, key_file), project=project)
    else:
        try:
            ee.Initialize(project=project)
        except Exception:
            ee.Authenticate()
            ee.Initialize(project=project)


def _add_ndvi(image):
    """Scale NDVI to [-1, 1], keep only good/marginal-quality pixels, and preserve the
    timestamp so `image.date()` still works after the transform.

    MOD13Q1 SummaryQA: 0 good, 1 marginal, 2 snow/ice, 3 cloudy — keep 0 and 1.
    """
    import ee
    good = image.select("SummaryQA").lte(1)
    ndvi = image.select("NDVI").multiply(_NDVI_SCALE).updateMask(good).rename("NDVI")
    return ee.Image(ndvi.copyProperties(image, ["system:time_start"]))


def _extract_mean_ndvi(image, geometry):
    import ee
    mean = image.select("NDVI").reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geometry,
        scale=250,
        maxPixels=1e9,
    )
    return ee.Feature(None, {
        "date": image.date().format("YYYY-MM-dd"),
        "ndvi_s2": mean.get("NDVI"),
    })


def fetch_ndvi_year(park_key: str, year: int, geometry, project: str = None) -> pd.DataFrame:
    """Fetch MOD13Q1 NDVI composites for one calendar year (about 23 per year)."""
    import ee
    collection = (
        ee.ImageCollection(_COLLECTION)
        .filterBounds(geometry)
        .filterDate(f"{year}-01-01", f"{year}-12-31")
        .map(_add_ndvi)
    )
    try:
        data = collection.map(lambda img: _extract_mean_ndvi(img, geometry)).getInfo()["features"]
    except Exception as exc:
        log.warning(f"  Skipped {year}: {exc}")
        return pd.DataFrame(columns=["ndvi_s2"])

    records = [
        {"date": f["properties"]["date"], "ndvi_s2": f["properties"].get("ndvi_s2")}
        for f in data
        if f["properties"].get("ndvi_s2") is not None
    ]
    if not records:
        log.warning(f"  No MOD13Q1 NDVI for {park_key} in {year}")
        return pd.DataFrame(columns=["ndvi_s2"])

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    df = df.groupby("date")["ndvi_s2"].mean().to_frame()
    df.index.name = "date"
    return df


def fetch_and_save_ndvi(
    park_key: str,
    start: str = TRAIN_START,
    end: str = TRAIN_END,
    project: str = None,
) -> pd.DataFrame:
    import ee
    start_year = pd.to_datetime(start).year
    end_year = pd.to_datetime(end).year
    out_path = DATA_RAW / "satellite" / f"{park_key}_ndvi_{start_year}_{end_year}.csv"

    if out_path.exists():
        log.info(f"NDVI already cached for {park_key} — loading from {out_path}")
        return pd.read_csv(out_path, index_col="date", parse_dates=True)

    log.info(f"Fetching MOD13Q1 NDVI for {park_key} ({start_year}-{end_year})...")
    _init_gee(project)
    park = PARKS[park_key]
    bbox = park["bbox"]
    geometry = ee.Geometry.Rectangle([
        bbox["min_lon"], bbox["min_lat"],
        bbox["max_lon"], bbox["max_lat"],
    ])

    chunks = []
    for year in range(start_year, end_year + 1):
        log.info(f"  Processing {year}...")
        try:
            chunks.append(fetch_ndvi_year(park_key, year, geometry, project))
        except Exception as exc:
            log.warning(f"  Skipped {year}: {exc}")

    if not chunks:
        raise RuntimeError(f"No NDVI data retrieved for {park_key}. Check GEE access and park bbox.")

    df = pd.concat(chunks).sort_index()
    df = df[~df.index.duplicated(keep="first")]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path)
    log.info(f"Saved NDVI data -> {out_path} ({len(df)} observations)")
    return df
