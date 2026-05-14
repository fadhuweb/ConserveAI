

"""Fetch Sentinel-2 NDVI via Google Earth Engine for a given park."""
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


def _mask_clouds_s2(image):
    import ee
    qa = image.select("QA60")
    cloud_bit = 1 << 10
    cirrus_bit = 1 << 11
    mask = qa.bitwiseAnd(cloud_bit).eq(0).And(qa.bitwiseAnd(cirrus_bit).eq(0))
    return image.updateMask(mask)


def _add_ndvi(image):
    import ee
    ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
    return image.addBands(ndvi)


def _extract_mean_ndvi(image, geometry):
    import ee
    mean = image.select("NDVI").reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geometry,
        scale=500,
        maxPixels=1e9,
    )
    return ee.Feature(None, {
        "date": image.date().format("YYYY-MM-dd"),
        "ndvi_s2": mean.get("NDVI"),
    })


def fetch_ndvi_year(park_key: str, year: int, geometry, project: str = None) -> pd.DataFrame:
    """Fetch Sentinel-2 NDVI for one calendar year, one month at a time."""
    import ee
    import calendar

    all_records = []
    for month in range(1, 13):
        m_start = f"{year}-{month:02d}-01"
        m_end = f"{year}-{month:02d}-{calendar.monthrange(year, month)[1]}"

        collection = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(geometry)
            .filterDate(m_start, m_end)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 80))
            .map(_mask_clouds_s2)
            .map(_add_ndvi)
        )

        try:
            data = collection.map(
                lambda img: _extract_mean_ndvi(img, geometry)
            ).getInfo()["features"]
        except Exception as exc:
            log.warning(f"  Skipped {year}-{month:02d}: {exc}")
            continue

        all_records.extend([
            {"date": f["properties"]["date"], "ndvi_s2": f["properties"].get("ndvi_s2")}
            for f in data
            if f["properties"].get("ndvi_s2") is not None
        ])

    if not all_records:
        log.warning(f"  No cloud-free Sentinel-2 observations for {park_key} in {year}")
        return pd.DataFrame(columns=["ndvi_s2"])

    df = pd.DataFrame(all_records)
    df["date"] = pd.to_datetime(df["date"])
    df = df.groupby("date")["ndvi_s2"].mean().to_frame()
    df.index.name = "date"
    return df


def fetch_and_save_ndvi(
    park_key: str,
    start: str = TRAIN_START,
    end: str = TRAIN_END,
    project: str = None,
) -> pd.DataFrame:
    import ee
    start_year = pd.to_datetime(start).year
    end_year = pd.to_datetime(end).year
    out_path = DATA_RAW / "satellite" / f"{park_key}_ndvi_{start_year}_{end_year}.csv"

    if out_path.exists():
        log.info(f"NDVI already cached for {park_key} — loading from {out_path}")
        return pd.read_csv(out_path, index_col="date", parse_dates=True)

    log.info(f"Fetching Sentinel-2 NDVI for {park_key} ({start_year}–{end_year})...")
    log.info("  This may take several minutes. GEE processes one year at a time.")

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
        try:
            chunk = fetch_ndvi_year(park_key, year, geometry, project)
            chunks.append(chunk)
        except Exception as exc:
            log.warning(f"  Skipped {year}: {exc}")

    if not chunks:
        raise RuntimeError(f"No NDVI data retrieved for {park_key}. Check GEE access and park bbox.")

    df = pd.concat(chunks).sort_index()
    df = df[~df.index.duplicated(keep="first")]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path)
    log.info(f"Saved NDVI data → {out_path} ({len(df)} observations)")
    return df
