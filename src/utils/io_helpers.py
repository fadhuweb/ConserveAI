import pandas as pd
from pathlib import Path


def read_parquet(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path)


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)


def read_csv_indexed(path: Path, date_col: str = "date") -> pd.DataFrame:
    return pd.read_csv(path, index_col=date_col, parse_dates=True)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path)
