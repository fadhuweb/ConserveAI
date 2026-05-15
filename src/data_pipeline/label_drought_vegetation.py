"""Add climate-derived drought and vegetation degradation labels.

Drought label (drought_within_30d):
    Drought = 30-day rolling rainfall below 40% of that calendar month's
    historical average, AND occurring in the rainy season. This handles
    the savanna dry season (which always has zero rain — not a drought).
    drought_within_30d = 1 if any drought condition occurs in the next 30 days.

Vegetation label (vegetation_within_30d):
    Vegetation degradation = NDVI more than 0.15 below its 90-day rolling
    average on at least 10 of any 21-day window. The relaxed window (vs
    strict consecutive days) accommodates sparse satellite coverage (~33%).
    vegetation_within_30d = 1 if any degradation window occurs in the next 30 days.

Usage:
    python -m src.data_pipeline.label_drought_vegetation --park yankari
"""
import argparse
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

from src.data_pipeline.config import PARKS, DATA_LABELED
from src.utils.logging_config import get_logger

log = get_logger(__name__)

FORWARD_DAYS = 30
DROUGHT_ROLLING = 30       # days for rolling rainfall sum
DROUGHT_RATIO = 0.40       # flag when actual < 40% of historical monthly average
NDVI_WINDOW = 90           # days for NDVI rolling average
NDVI_THRESHOLD = 0.10      # deviation below average (~1 std for Yankari NDVI)
VEG_DAYS_IN_WINDOW = 5     # degraded days required within a 14-day window
VEG_WINDOW = 14


def _forward_label(flag_series: pd.Series) -> pd.Series:
    """Return 1 if any flag=1 occurs in the next FORWARD_DAYS days."""
    reversed_flag = flag_series.iloc[::-1]
    future_sum = (
        reversed_flag.shift(1).rolling(FORWARD_DAYS, min_periods=FORWARD_DAYS).sum()
    )
    result = future_sum.iloc[::-1]
    out = (result > 0).astype("Int64")
    out.iloc[-FORWARD_DAYS:] = pd.NA
    return out


def add_drought_label(df: pd.DataFrame, park_key: str) -> pd.DataFrame:
    precip = df["om_precipitation_sum"] if "om_precipitation_sum" in df.columns else df["power_prectotcorr"]

    rolling_actual = precip.rolling(DROUGHT_ROLLING, min_periods=DROUGHT_ROLLING // 2).sum()

    # Historical monthly average: mean daily rainfall per calendar month × window
    monthly_daily_avg = precip.groupby(precip.index.month).mean()
    rolling_expected = precip.index.month.map(monthly_daily_avg) * DROUGHT_ROLLING
    rolling_expected = pd.Series(rolling_expected.values, index=df.index)

    # Rainfall ratio: actual vs climatological expectation for that month
    ratio = rolling_actual / rolling_expected.replace(0, float("nan"))

    # Drought only meaningful in rainy season — dry season zero rain is normal
    dry_months = set(PARKS[park_key]["dry_season_months"])
    rainy_season = ~pd.Series(df.index.month, index=df.index).isin(dry_months)

    drought_flag = ((ratio < DROUGHT_RATIO) & rainy_season).astype(float)

    df = df.copy()
    df["drought_within_30d"] = _forward_label(drought_flag)

    n_drought = int(drought_flag.sum())
    n_pos = int(df["drought_within_30d"].sum(skipna=True))
    n_labeled = int(df["drought_within_30d"].notna().sum())
    log.info(
        f"  Drought threshold: <{DROUGHT_RATIO:.0%} of monthly average over {DROUGHT_ROLLING}d | "
        f"{n_drought} drought days in record | "
        f"{n_pos} rows labeled positive ({n_pos/n_labeled:.1%})"
    )
    return df


def add_vegetation_label(df: pd.DataFrame) -> pd.DataFrame:
    # Forward-fill NDVI up to 7 days (PDF feature engineering spec)
    ndvi = df["ndvi_s2"].ffill(limit=7)

    ndvi_90d_avg = ndvi.rolling(NDVI_WINDOW, min_periods=NDVI_WINDOW // 3).mean()
    ndvi_deviation = ndvi - ndvi_90d_avg

    # Days where NDVI is more than threshold below rolling average
    below = (ndvi_deviation < -NDVI_THRESHOLD).astype(float)
    below[ndvi.isna()] = float("nan")

    # At least VEG_DAYS_IN_WINDOW days degraded within any VEG_WINDOW-day period
    # min_periods set to half the window so sparse data can still qualify
    degraded_window = (
        below.fillna(0)
        .rolling(VEG_WINDOW, min_periods=VEG_WINDOW // 2)
        .sum()
        >= VEG_DAYS_IN_WINDOW
    ).astype(float)

    df = df.copy()
    df["vegetation_within_30d"] = _forward_label(degraded_window)

    n_veg = int(degraded_window.sum())
    n_pos = int(df["vegetation_within_30d"].sum(skipna=True))
    n_labeled = int(df["vegetation_within_30d"].notna().sum())
    log.info(
        f"  Vegetation degradation: {n_veg} days where ≥{VEG_DAYS_IN_WINDOW}/{VEG_WINDOW}d "
        f"NDVI < (90d_avg − {NDVI_THRESHOLD}) | "
        f"{n_pos} rows labeled positive ({n_pos/n_labeled:.1%})"
    )
    return df


def label_park(park_key: str) -> pd.DataFrame:
    labeled_files = sorted(DATA_LABELED.glob(f"{park_key}_labeled_*.csv"))
    if not labeled_files:
        raise FileNotFoundError(
            f"No labeled file for {park_key} in {DATA_LABELED}. Run label_fire.py first."
        )
    path = labeled_files[-1]
    log.info(f"Loading {path.name}...")
    df = pd.read_csv(path, index_col="date", parse_dates=True)

    log.info("Computing drought_within_30d...")
    df = add_drought_label(df, park_key)

    log.info("Computing vegetation_within_30d...")
    df = add_vegetation_label(df)

    df.to_csv(path)
    log.info(f"Saved → {path}")
    log.info(
        f"Label summary for {park_key}:\n"
        f"  fire_within_30d:        {int(df['fire_within_30d'].sum(skipna=True))} / "
        f"{df['fire_within_30d'].notna().sum()} labeled\n"
        f"  drought_within_30d:     {int(df['drought_within_30d'].sum(skipna=True))} / "
        f"{df['drought_within_30d'].notna().sum()} labeled\n"
        f"  vegetation_within_30d:  {int(df['vegetation_within_30d'].sum(skipna=True))} / "
        f"{df['vegetation_within_30d'].notna().sum()} labeled"
    )
    return df


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add drought and vegetation labels derived from climate/NDVI data"
    )
    parser.add_argument(
        "--park", default="yankari", choices=list(PARKS.keys()),
        help="Park to label (default: yankari)",
    )
    args = parser.parse_args()
    label_park(args.park)


if __name__ == "__main__":
    main()
