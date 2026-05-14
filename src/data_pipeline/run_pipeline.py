"""Orchestrate the data pipeline for one or more parks.

Usage (from project root):
    python -m src.data_pipeline.run_pipeline --parks yankari
    python -m src.data_pipeline.run_pipeline --parks yankari cross_river --gee-project my-gee-project
"""
import argparse
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

from src.data_pipeline.config import PARKS, TRAIN_START, TRAIN_END, DATA_RAW
from src.data_pipeline.fetch_climate import fetch_and_save_climate
from src.data_pipeline.fetch_satellite import fetch_and_save_ndvi
from src.data_pipeline.fetch_fire import fetch_and_save_firms
from src.data_pipeline.join_sources import join_park_sources
from src.utils.logging_config import get_logger

log = get_logger(__name__)


def run_park(
    park_key: str,
    start: str = TRAIN_START,
    end: str = TRAIN_END,
    gee_project: str = None,
) -> pd.DataFrame:
    log.info(f"{'=' * 50}")
    log.info(f"Pipeline: {PARKS[park_key]['display_name']}")
    log.info(f"{'=' * 50}")

    fetch_and_save_climate(park_key, start, end)
    fetch_and_save_ndvi(park_key, start, end, project=gee_project)
    fetch_and_save_firms(park_key, start, end, project=gee_project)

    raw_df = join_park_sources(park_key, start, end)

    start_year = pd.to_datetime(start).year
    end_year = pd.to_datetime(end).year
    out_path = DATA_RAW / f"{park_key}_raw_{start_year}_{end_year}.csv"
    raw_df.to_csv(out_path)
    log.info(f"Saved joined raw data → {out_path}")
    return raw_df


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ConserveAI data pipeline")
    parser.add_argument(
        "--parks",
        nargs="+",
        default=["yankari"],
        choices=list(PARKS.keys()),
        help="Parks to process (default: yankari)",
    )
    parser.add_argument("--start", default=TRAIN_START, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default=TRAIN_END, help="End date YYYY-MM-DD")
    parser.add_argument("--gee-project", default=None, help="Google Earth Engine project ID")
    args = parser.parse_args()

    for park in args.parks:
        run_park(park, args.start, args.end, args.gee_project)

    log.info("Pipeline complete.")


if __name__ == "__main__":
    main()
