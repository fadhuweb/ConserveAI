"""Engineer ~20 features per row from the combined labeled dataset.

Input:  data/processed/combined_dataset.csv
Output: data/processed/featured_dataset.csv
        data/processed/split_indices.csv

Feature groups:
  Climate (7):   rain_7d, rain_30d, rain_60d, rain_deficit_30d,
                 temp_max_7d, temp_max_30d, hot_days_30d
  Satellite (5): ndvi, ndvi_30d_lag, ndvi_change_30d, ndvi_90d_avg, ndvi_deviation
  Fire (3):      fire_30d, fire_90d, days_since_fire
  Context (5):   doy_sin, doy_cos, dry_season, park_id, ecosystem_id

Total: 20 features.

Rows where NDVI is unavailable after 7-day forward-fill are flagged with
ndvi_missing=1 and excluded from training but retained in the file.
The first 60 rows of each park are dropped (rolling window warm-up).

Usage:
    python -m src.data_pipeline.feature_engineering
"""
import numpy as np
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

from src.data_pipeline.config import PARKS, DATA_PROCESSED
from src.utils.logging_config import get_logger

log = get_logger(__name__)

WARMUP_DAYS = 60
TRAIN_END   = "2023-06-30"
VAL_START   = "2023-07-01"
VAL_END     = "2023-12-31"
TEST_START  = "2024-01-01"

PARK_IDS = {k: i for i, k in enumerate(PARKS.keys())}
ECOSYSTEM_IDS = {"savanna": 0, "rainforest": 1, "mixed": 2, "sahel": 3, "wetland": 4}

FEATURE_COLS = [
    "rain_7d", "rain_30d", "rain_60d", "rain_deficit_30d",
    "temp_max_7d", "temp_max_30d", "hot_days_30d",
    "ndvi", "ndvi_30d_lag", "ndvi_change_30d", "ndvi_90d_avg", "ndvi_deviation",
    "fire_30d", "fire_90d", "days_since_fire",
    "doy_sin", "doy_cos", "dry_season", "park_id", "ecosystem_id",
]
LABEL_COLS = ["fire_within_30d", "drought_within_30d", "vegetation_within_30d"]
META_COLS  = ["park", "ecosystem", "ndvi_missing"]


def _engineer_park(df: pd.DataFrame, park_key: str) -> pd.DataFrame:
    park_cfg = PARKS[park_key]
    df = df.copy().sort_index()

    # ── Climate ──────────────────────────────────────────────────────────────
    precip   = df["om_precipitation_sum"].fillna(0)
    temp_max = df["om_temperature_2m_max"]

    df["rain_7d"]  = precip.rolling(7,  min_periods=4).sum()
    df["rain_30d"] = precip.rolling(30, min_periods=15).sum()
    df["rain_60d"] = precip.rolling(60, min_periods=30).sum()

    monthly_avg   = precip.groupby(precip.index.month).mean()
    expected_30d  = pd.Series(
        precip.index.month.map(monthly_avg).values * 30, index=df.index
    )
    df["rain_deficit_30d"] = df["rain_30d"] - expected_30d

    df["temp_max_7d"]  = temp_max.rolling(7,  min_periods=4).mean()
    df["temp_max_30d"] = temp_max.rolling(30, min_periods=15).mean()
    df["hot_days_30d"] = (
        (temp_max > 35).astype(float).rolling(30, min_periods=15).sum()
    )

    # ── Satellite ─────────────────────────────────────────────────────────────
    ndvi_filled = df["ndvi_s2"].ffill(limit=7)

    df["ndvi"]         = ndvi_filled
    df["ndvi_missing"] = ndvi_filled.isna().astype(int)
    df["ndvi_30d_lag"] = ndvi_filled.shift(30)
    df["ndvi_change_30d"] = ndvi_filled - ndvi_filled.shift(30)
    df["ndvi_90d_avg"] = ndvi_filled.rolling(90, min_periods=30).mean()
    df["ndvi_deviation"] = ndvi_filled - df["ndvi_90d_avg"]

    # ── Fire history ──────────────────────────────────────────────────────────
    fire = df["firms_count"].fillna(0)

    df["fire_30d"] = fire.rolling(30, min_periods=15).sum()
    df["fire_90d"] = fire.rolling(90, min_periods=45).sum()

    fire_detected = (fire > 0)
    fire_dates = pd.Series(
        np.where(fire_detected, df.index.values, pd.NaT),
        index=df.index,
        dtype="datetime64[ns]",
    ).ffill()
    days_since = (df.index - fire_dates).dt.days
    df["days_since_fire"] = days_since.fillna(365).clip(upper=365)

    # ── Context ───────────────────────────────────────────────────────────────
    doy = df.index.dayofyear
    df["doy_sin"]      = np.sin(2 * np.pi * doy / 365.25)
    df["doy_cos"]      = np.cos(2 * np.pi * doy / 365.25)
    df["dry_season"]   = df.index.month.isin(park_cfg["dry_season_months"]).astype(int)
    df["park_id"]      = PARK_IDS[park_key]
    df["ecosystem_id"] = ECOSYSTEM_IDS.get(park_cfg["ecosystem"], 0)

    # ── Drop warm-up rows ─────────────────────────────────────────────────────
    df = df.iloc[WARMUP_DAYS:]

    return df


def _assign_split(df: pd.DataFrame) -> pd.DataFrame:
    conditions = [
        df.index <= TRAIN_END,
        (df.index >= VAL_START) & (df.index <= VAL_END),
        df.index >= TEST_START,
    ]
    df["split"] = np.select(conditions, ["train", "val", "test"], default="train")
    return df


def build_features() -> pd.DataFrame:
    combined_path = DATA_PROCESSED / "combined_dataset.csv"
    if not combined_path.exists():
        raise FileNotFoundError(
            f"{combined_path} not found. Run build_combined_dataset.py first."
        )

    log.info("Loading combined dataset...")
    combined = pd.read_csv(combined_path, index_col="date", parse_dates=True)

    frames = []
    for park_key in PARKS:
        park_df = combined[combined["park"] == park_key].copy()
        if park_df.empty:
            log.warning(f"No data for {park_key} — skipping")
            continue
        log.info(f"Engineering features for {park_key}...")
        engineered = _engineer_park(park_df, park_key)
        frames.append(engineered)

    featured = pd.concat(frames).sort_index()
    featured = _assign_split(featured)

    keep_cols = FEATURE_COLS + LABEL_COLS + META_COLS + ["split"]
    featured = featured[[c for c in keep_cols if c in featured.columns]]

    # Summary
    log.info(f"\nFeatured dataset: {len(featured):,} rows, {len(featured.columns)} columns")
    log.info(f"  After {WARMUP_DAYS}-day warm-up drop per park")
    log.info(f"  ndvi_missing rows: {featured['ndvi_missing'].sum():,} "
             f"({featured['ndvi_missing'].mean():.1%})")

    split_counts = featured["split"].value_counts().sort_index()
    log.info(f"  Train: {split_counts.get('train', 0):,} | "
             f"Val: {split_counts.get('val', 0):,} | "
             f"Test: {split_counts.get('test', 0):,}")

    # Test set label check (flag if <30 positives per park per threat)
    test_df = featured[featured["split"] == "test"]
    log.info("\nTest set positives per park (flag if <30):")
    for park_key in PARKS:
        park_test = test_df[test_df["park"] == park_key]
        parts = []
        for col in LABEL_COLS:
            n_pos = int(park_test[col].sum(skipna=True))
            flag = "⚠" if n_pos < 30 else ""
            parts.append(f"{col.replace('_within_30d','')}: {n_pos}{flag}")
        log.info(f"  {park_key}: {' | '.join(parts)}")

    # Save
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    size_mb = featured.memory_usage(deep=True).sum() / 1e6
    if size_mb > 100:
        out_path = DATA_PROCESSED / "featured_dataset.parquet"
        featured.to_parquet(out_path)
    else:
        out_path = DATA_PROCESSED / "featured_dataset.csv"
        featured.to_csv(out_path)
    log.info(f"Saved featured dataset ({size_mb:.1f} MB) → {out_path}")

    # Save split indices separately
    split_path = DATA_PROCESSED / "split_indices.csv"
    featured[["park", "split"]].to_csv(split_path)
    log.info(f"Saved split indices → {split_path}")

    return featured


if __name__ == "__main__":
    build_features()
