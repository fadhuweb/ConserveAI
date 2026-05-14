"""Merge climate, NDVI, and FIRMS data into one daily dataframe per park."""
import pandas as pd

from src.data_pipeline.config import PARKS, TRAIN_START, TRAIN_END, DATA_RAW
from src.utils.logging_config import get_logger

log = get_logger(__name__)


def _load_climate(park_key: str, start_year: int, end_year: int) -> pd.DataFrame:
    path = DATA_RAW / "climate" / f"{park_key}_climate_{start_year}_{end_year}.csv"
    return pd.read_csv(path, index_col="date", parse_dates=True)


def _load_ndvi(park_key: str, start_year: int, end_year: int) -> pd.DataFrame:
    path = DATA_RAW / "satellite" / f"{park_key}_ndvi_{start_year}_{end_year}.csv"
    return pd.read_csv(path, index_col="date", parse_dates=True)


def _load_firms(park_key: str, start_year: int, end_year: int) -> pd.DataFrame:
    path = DATA_RAW / "fire" / f"{park_key}_fire_{start_year}_{end_year}.csv"
    return pd.read_csv(path, index_col="acq_date", parse_dates=True)


def _build_fire_daily(firms_park: pd.DataFrame, date_index: pd.DatetimeIndex) -> pd.DataFrame:
    """Reindex GEE-aggregated daily fire data onto the full date spine."""
    base = pd.DataFrame(
        {"firms_count": 0, "firms_frp_mean": float("nan")},
        index=date_index,
    )
    if firms_park.empty:
        return base

    firms_park = firms_park.copy()
    firms_park.index = pd.DatetimeIndex(firms_park.index).normalize()
    firms_park.index.name = "date"

    for col in ("firms_count", "firms_frp_mean"):
        if col in firms_park.columns:
            base[col] = firms_park[col].reindex(date_index)

    base["firms_count"] = base["firms_count"].fillna(0).astype(int)
    return base


def join_park_sources(
    park_key: str,
    start: str = TRAIN_START,
    end: str = TRAIN_END,
) -> pd.DataFrame:
    start_year = pd.to_datetime(start).year
    end_year = pd.to_datetime(end).year

    log.info(f"Joining data sources for {park_key}...")

    climate = _load_climate(park_key, start_year, end_year)
    ndvi = _load_ndvi(park_key, start_year, end_year)
    firms_park = _load_firms(park_key, start_year, end_year)

    # Full daily date spine
    date_index = pd.date_range(start=start, end=end, freq="D", name="date")

    # Climate is daily and complete — use as the base
    df = climate.reindex(date_index)

    # NDVI is sparse (satellite revisit ~5 days + cloud gaps)
    df = df.join(ndvi, how="left")

    # Fire: aggregate point detections to daily counts
    fire_daily = _build_fire_daily(firms_park, date_index)
    df = df.join(fire_daily, how="left")

    # Park metadata
    df["park"] = park_key
    df["ecosystem"] = PARKS[park_key]["ecosystem"]

    ndvi_coverage = df["ndvi_s2"].notna().mean() if "ndvi_s2" in df.columns else 0.0
    fire_days = int((df.get("firms_count", pd.Series(0)) > 0).sum())
    log.info(
        f"  {len(df)} rows | NDVI coverage {ndvi_coverage:.1%} | "
        f"{fire_days} days with fire detections"
    )
    return df
