"""Add fire_within_30d label to a park's raw dataset.

For each date t, fire_within_30d = 1 if any MODIS fire detection
(firms_count > 0) occurs in the 30 days AFTER t. Rows where a full
30-day forward window cannot be computed are set to NaN.

Usage:
    python -m src.data_pipeline.label_fire --park yankari
"""
import argparse
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

from src.data_pipeline.config import PARKS, DATA_RAW, DATA_LABELED
from src.utils.logging_config import get_logger

log = get_logger(__name__)

FORWARD_DAYS = 30


def add_fire_label(df: pd.DataFrame) -> pd.DataFrame:
    """Return df with fire_within_30d column added (Int64, NaN for incomplete windows)."""
    fire_binary = (df["firms_count"] > 0).astype(float)

    # Rolling over the reversed series gives a forward-looking window.
    # shift(1) excludes the current day so we look at [t+1 ... t+30].
    reversed_fire = fire_binary.iloc[::-1]
    future_sum = reversed_fire.shift(1).rolling(FORWARD_DAYS, min_periods=FORWARD_DAYS).sum()
    fire_within_30d = future_sum.iloc[::-1]

    df = df.copy()
    df["fire_within_30d"] = (fire_within_30d > 0).astype("Int64")
    # Last FORWARD_DAYS rows have incomplete windows → NaN
    df.loc[df.index[-FORWARD_DAYS:], "fire_within_30d"] = pd.NA
    return df


def label_park(park_key: str) -> pd.DataFrame:
    # Infer year range from the raw file
    raw_files = sorted((DATA_RAW).glob(f"{park_key}_raw_*.csv"))
    if not raw_files:
        raise FileNotFoundError(
            f"No raw file found for {park_key} in {DATA_RAW}. "
            "Run the data pipeline first."
        )
    raw_path = raw_files[-1]
    log.info(f"Loading {raw_path.name}...")
    df = pd.read_csv(raw_path, index_col="date", parse_dates=True)

    log.info(f"Computing fire_within_30d for {park_key} ({len(df)} rows)...")
    df = add_fire_label(df)

    labeled = df["fire_within_30d"].notna().sum()
    positive = int(df["fire_within_30d"].sum(skipna=True))
    log.info(
        f"  {labeled} labeled rows | {positive} positive ({positive/labeled:.1%}) "
        f"| {FORWARD_DAYS} rows set to NaN (end of series)"
    )

    DATA_LABELED.mkdir(parents=True, exist_ok=True)
    stem = raw_path.stem.replace("_raw_", "_labeled_")
    out_path = DATA_LABELED / f"{stem}.csv"
    df.to_csv(out_path)
    log.info(f"Saved → {out_path}")
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Add fire_within_30d label")
    parser.add_argument(
        "--park",
        default="yankari",
        choices=list(PARKS.keys()),
        help="Park to label (default: yankari)",
    )
    args = parser.parse_args()
    label_park(args.park)


if __name__ == "__main__":
    main()
