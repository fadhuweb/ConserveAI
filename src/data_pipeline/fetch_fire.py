"""Fetch MODIS daily fire detections per park via Google Earth Engine."""
import pandas as pd

from src.data_pipeline.config import PARKS, TRAIN_START, TRAIN_END, DATA_RAW
from src.utils.logging_config import get_logger

log = get_logger(__name__)


def _init_gee(project: str = None) -> None:
    import ee
    try:
        ee.Initialize(project=project)
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=project)


def fetch_fire_year(park_key: str, year: int, geometry, project: str = None) -> pd.DataFrame:
    """Fetch MODIS Terra+Aqua daily fire detections for a park for one calendar year."""
    import ee

    terra = ee.ImageCollection("MODIS/061/MOD14A1")
    aqua = ee.ImageCollection("MODIS/061/MYD14A1")
    collection = (
        terra.merge(aqua)
        .filterBounds(geometry)
        .filterDate(f"{year}-01-01", f"{year}-12-31")
    )

    def extract_fire(image):
        fire_mask = image.select("FireMask")
        fire_pixels = fire_mask.gte(7)
        count = fire_pixels.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=1000,
            maxPixels=1e9,
        )
        frp = (
            image.select("MaxFRP")
            .updateMask(fire_pixels)
            .reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometry,
                scale=1000,
                maxPixels=1e9,
            )
        )
        return ee.Feature(None, {
            "acq_date": image.date().format("YYYY-MM-dd"),
            "firms_count": count.get("FireMask"),
            "firms_frp_mean": frp.get("MaxFRP"),
        })

    try:
        features = collection.map(extract_fire).getInfo()["features"]
    except Exception as exc:
        log.warning(f"  GEE fire fetch failed for {park_key} {year}: {exc}")
        return pd.DataFrame(columns=["firms_count", "firms_frp_mean"])

    records = [
        {
            "acq_date": f["properties"]["acq_date"],
            "firms_count": int(f["properties"].get("firms_count") or 0),
            "firms_frp_mean": f["properties"].get("firms_frp_mean"),
        }
        for f in features
        if (f["properties"].get("firms_count") or 0) > 0
    ]

    if not records:
        return pd.DataFrame(columns=["firms_count", "firms_frp_mean"])

    df = pd.DataFrame(records)
    df["acq_date"] = pd.to_datetime(df["acq_date"])
    df = df.set_index("acq_date")
    df.index.name = "acq_date"
    return df


def fetch_and_save_firms(
    park_key: str,
    start: str = TRAIN_START,
    end: str = TRAIN_END,
    project: str = None,
) -> pd.DataFrame:
    import ee

    start_year = pd.to_datetime(start).year
    end_year = pd.to_datetime(end).year
    out_path = DATA_RAW / "fire" / f"{park_key}_fire_{start_year}_{end_year}.csv"

    if out_path.exists():
        log.info(f"Fire data already cached for {park_key} — loading from {out_path}")
        return pd.read_csv(out_path, index_col="acq_date", parse_dates=True)

    log.info(
        f"Fetching MODIS fire detections for {park_key} ({start_year}–{end_year}) via GEE..."
    )

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
        chunk = fetch_fire_year(park_key, year, geometry, project)
        if not chunk.empty:
            chunks.append(chunk)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not chunks:
        log.warning(f"No fire detections found for {park_key}. Saving empty file.")
        empty_df = pd.DataFrame(columns=["firms_count", "firms_frp_mean"])
        empty_df.index.name = "acq_date"
        empty_df.to_csv(out_path)
        return empty_df

    df = pd.concat(chunks).sort_index()
    df = df[~df.index.duplicated(keep="first")]
    df.to_csv(out_path)
    log.info(f"Saved {len(df)} fire-detection days → {out_path}")
    return df
