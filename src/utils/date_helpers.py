import pandas as pd
from typing import Iterator, Tuple


def date_range(start: str, end: str) -> pd.DatetimeIndex:
    return pd.date_range(start=start, end=end, freq="D", name="date")


def year_chunks(start: str, end: str) -> Iterator[Tuple[str, str]]:
    start_year = pd.to_datetime(start).year
    end_year = pd.to_datetime(end).year
    for year in range(start_year, end_year + 1):
        yield f"{year}-01-01", f"{year}-12-31"
