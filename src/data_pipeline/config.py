from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
DATA_RAW = DATA_DIR / "raw"
DATA_PROCESSED = DATA_DIR / "processed"
DATA_LABELED = DATA_DIR / "labeled"

TRAIN_START = "2020-01-01"
TRAIN_END = "2025-12-31"

PARKS = {
    "yankari": {
        "display_name": "Yankari Game Reserve",
        "state": "Bauchi",
        "ecosystem": "savanna",
        "area_km2": 2244,
        "lat": 9.87,
        "lon": 10.47,
        "bbox": {"min_lon": 9.6, "min_lat": 9.3, "max_lon": 11.0, "max_lat": 10.3},
        "dry_season_months": [11, 12, 1, 2, 3],
    },
    "cross_river": {
        "display_name": "Cross River National Park",
        "state": "Cross River",
        "ecosystem": "rainforest",
        "area_km2": 4000,
        "lat": 5.92,
        "lon": 8.72,
        "bbox": {"min_lon": 8.3, "min_lat": 5.5, "max_lon": 9.2, "max_lat": 6.4},
        "dry_season_months": [11, 12, 1, 2],
    },
    "gashaka_gumti": {
        "display_name": "Gashaka-Gumti National Park",
        "state": "Taraba/Adamawa",
        "ecosystem": "mixed",
        "area_km2": 6731,
        "lat": 7.80,
        "lon": 11.88,
        "bbox": {"min_lon": 11.0, "min_lat": 6.9, "max_lon": 12.6, "max_lat": 8.6},
        "dry_season_months": [11, 12, 1, 2, 3],
    },
    "kainji_lake": {
        "display_name": "Kainji Lake National Park",
        "state": "Niger/Kebbi",
        "ecosystem": "savanna",
        "area_km2": 5341,
        "lat": 10.32,
        "lon": 4.58,
        "bbox": {"min_lon": 4.2, "min_lat": 9.8, "max_lon": 5.1, "max_lat": 11.0},
        "dry_season_months": [11, 12, 1, 2, 3, 4],
    },
    "chad_basin": {
        "display_name": "Chad Basin National Park",
        "state": "Borno/Yobe",
        "ecosystem": "sahel",
        "area_km2": 2258,
        "lat": 12.87,
        "lon": 13.48,
        "bbox": {"min_lon": 13.0, "min_lat": 12.2, "max_lon": 14.5, "max_lat": 13.5},
        "dry_season_months": [10, 11, 12, 1, 2, 3, 4, 5],
    },
    "old_oyo": {
        "display_name": "Old Oyo National Park",
        "state": "Oyo",
        "ecosystem": "savanna",
        "area_km2": 2512,
        "lat": 8.37,
        "lon": 3.92,
        "bbox": {"min_lon": 3.5, "min_lat": 8.0, "max_lon": 4.5, "max_lat": 8.8},
        "dry_season_months": [11, 12, 1, 2, 3],
    },
}

# API endpoints
OPEN_METEO_URL = "https://archive-api.open-meteo.com/v1/archive"
NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

# Nigeria bounding box for FIRMS download (W,S,E,N)
NIGERIA_BBOX = "2.7,4.3,14.7,13.9"

# Open-Meteo daily variables
OPEN_METEO_VARS = [
    "precipitation_sum",
    "temperature_2m_max",
    "temperature_2m_min",
    "relative_humidity_2m_max",
    "windspeed_10m_max",
]

# NASA POWER variables (comma-separated string, as API expects)
NASA_POWER_VARS = "ALLSKY_SFC_SW_DWN,GWETROOT,RH2M,T2M,T2M_MAX,T2M_MIN,PRECTOTCORR"
