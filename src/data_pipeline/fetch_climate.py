"""Fetch climate data from Open-Meteo and NASA POWER for a given park."""
import time
import requests
import pandas as pd

from src.data_pipeline.config import (
    PARKS, TRAIN_START, TRAIN_END, DATA_RAW,
    OPEN_METEO_URL, OPEN_METEO_VARS,
    NASA_POWER_URL, NASA_POWER_VARS,
)
from src.utils.logging_config import get_logger

log = get_logger(__name__)


def fetch_open_meteo(park_key: str, start: str = TRAIN_START, end: str = TRAIN_END) -> pd.DataFrame:
    park = PARKS[park_key]
    params = {
        "latitude": park["lat"],
        "longitude": park["lon"],
        "start_date": start,
        "end_date": end,
        "daily": ",".join(OPEN_METEO_VARS),
        "timezone": "Africa/Lagos",
    }
    resp = requests.get(OPEN_METEO_URL, params=params, timeout=60)
    resp.raise_for_status()
    raw = resp.json()

    df = pd.DataFrame(raw["daily"])
    df["date"] = pd.to_datetime(df["time"])
    df = df.drop(columns=["time"]).set_index("date")
    df.columns = [f"om_{c}" for c in df.columns]

    log.info(f"Open-Meteo: {len(df)} rows for {park_key}")
    return df


def fetch_nasa_power(park_key: str, start: str = TRAIN_START, end: str = TRAIN_END) -> pd.DataFrame:
    park = PARKS[park_key]
    params = {
        "parameters": NASA_POWER_VARS,
        "community": "AG",
        "longitude": park["lon"],
        "latitude": park["lat"],
        "start": start.replace("-", ""),
        "end": end.replace("-", ""),
        "format": "JSON",
    }
    resp = requests.get(NASA_POWER_URL, params=params, timeout=120)
    resp.raise_for_status()
    raw = resp.json()

    # raw["properties"]["parameter"] = {VAR: {"YYYYMMDD": value, ...}, ...}
    params_data = raw["properties"]["parameter"]
    df = pd.DataFrame(params_data)
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df.index.name = "date"
    df.columns = [f"power_{c.lower()}" for c in df.columns]

    # NASA POWER uses -999 for missing
    df = df.replace(-999.0, float("nan"))

    log.info(f"NASA POWER: {len(df)} rows for {park_key}")
    return df


def fetch_and_save_climate(park_key: str, start: str = TRAIN_START, end: str = TRAIN_END) -> pd.DataFrame:
    start_year = pd.to_datetime(start).year
    end_year = pd.to_datetime(end).year
    out_path = DATA_RAW / "climate" / f"{park_key}_climate_{start_year}_{end_year}.csv"

    if out_path.exists():
        log.info(f"Climate already cached for {park_key} — loading from {out_path}")
        return pd.read_csv(out_path, index_col="date", parse_dates=True)

    log.info(f"Fetching climate data for {park_key}...")
    om = fetch_open_meteo(park_key, start, end)

    time.sleep(1)  # be polite between APIs
    power = fetch_nasa_power(park_key, start, end)

    df = om.join(power, how="outer")
    df.index.name = "date"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path)
    log.info(f"Saved climate data → {out_path}")
    return df
