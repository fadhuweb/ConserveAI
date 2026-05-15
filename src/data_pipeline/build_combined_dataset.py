"""Combine labeled CSVs from all parks into one dataset.

Loads all per-park labeled CSVs from data/labeled/, concatenates them,
prints a per-park summary, and saves to data/processed/. Uses Parquet
if the combined file exceeds 100 MB, otherwise CSV.

Usage:
    python -m src.data_pipeline.build_combined_dataset
"""
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

from src.data_pipeline.config import PARKS, DATA_LABELED, DATA_PROCESSED
from src.utils.logging_config import get_logger

log = get_logger(__name__)

SIZE_THRESHOLD_MB = 100
LABEL_COLS = ["fire_within_30d", "drought_within_30d", "vegetation_within_30d"]


def load_park(park_key: str) -> pd.DataFrame:
    files = sorted(DATA_LABELED.glob(f"{park_key}_labeled_*.csv"))
    if not files:
        raise FileNotFoundError(
            f"No labeled file for {park_key}. "
            "Run label_fire.py and label_drought_vegetation.py first."
        )
    df = pd.read_csv(files[-1], index_col="date", parse_dates=True)
    df["park"] = park_key
    return df


def park_summary(park_key: str, df: pd.DataFrame) -> dict:
    summary = {
        "park": PARKS[park_key]["display_name"],
        "ecosystem": PARKS[park_key]["ecosystem"],
        "rows": len(df),
    }
    for col in LABEL_COLS:
        if col in df.columns:
            n_labeled = int(df[col].notna().sum())
            n_pos = int(df[col].sum(skipna=True))
            summary[f"{col}_positive"] = n_pos
            summary[f"{col}_rate"] = f"{n_pos/n_labeled:.1%}" if n_labeled else "N/A"
        else:
            summary[f"{col}_positive"] = "missing"
            summary[f"{col}_rate"] = "missing"
    return summary


def build(parks: list = None) -> pd.DataFrame:
    parks = parks or list(PARKS.keys())
    frames = []
    summaries = []

    for park_key in parks:
        log.info(f"Loading {park_key}...")
        try:
            df = load_park(park_key)
            frames.append(df)
            summaries.append(park_summary(park_key, df))
        except FileNotFoundError as e:
            log.warning(str(e))

    if not frames:
        raise RuntimeError("No labeled data found. Run the full pipeline first.")

    combined = pd.concat(frames, axis=0).sort_index()
    log.info(f"Combined dataset: {len(combined):,} rows, {len(combined.columns)} columns")

    # Per-park summary
    summary_df = pd.DataFrame(summaries).set_index("park")
    log.info("\nPer-park summary:\n" + summary_df.to_string())

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    # Save summary report
    report_path = DATA_PROCESSED / "park_summary.md"
    _write_summary_report(summary_df, report_path)
    log.info(f"Summary report → {report_path}")

    # Save combined dataset (CSV or Parquet depending on size)
    size_mb = combined.memory_usage(deep=True).sum() / 1e6
    if size_mb > SIZE_THRESHOLD_MB:
        out_path = DATA_PROCESSED / "combined_dataset.parquet"
        combined.to_parquet(out_path)
        log.info(f"Saved as Parquet ({size_mb:.1f} MB) → {out_path}")
    else:
        out_path = DATA_PROCESSED / "combined_dataset.csv"
        combined.to_csv(out_path)
        log.info(f"Saved as CSV ({size_mb:.1f} MB) → {out_path}")

    return combined


def _write_summary_report(summary_df: pd.DataFrame, path) -> None:
    lines = [
        "# Per-Park Dataset Summary",
        "",
        f"Generated from `data/labeled/` — {pd.Timestamp.now().date()}",
        "",
        "## Label Base Rates",
        "",
        "| Park | Ecosystem | Rows | Fire+ | Fire% | Drought+ | Drought% | Vegetation+ | Vegetation% |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for park_name, row in summary_df.iterrows():
        lines.append(
            f"| {park_name} | {row['ecosystem']} | {row['rows']} "
            f"| {row['fire_within_30d_positive']} | {row['fire_within_30d_rate']} "
            f"| {row['drought_within_30d_positive']} | {row['drought_within_30d_rate']} "
            f"| {row['vegetation_within_30d_positive']} | {row['vegetation_within_30d_rate']} |"
        )
    lines += [
        "",
        "## Notes",
        "",
        "- Rainforest parks (Cross River) are expected to have low fire base rates.",
        "- Drought labels exclude dry-season months (park-specific).",
        "- Vegetation labels use 90-day NDVI rolling average with 10/14-day window.",
        "- Last 30 rows per park are unlabeled (incomplete forward window).",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    build()
