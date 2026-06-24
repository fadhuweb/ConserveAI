"""Application settings loaded from environment / .env file."""

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql://conserveai:conserveai@localhost:5432/conserveai"
    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 8

    environment: str = "development"
    log_level: str = "INFO"
    frontend_url: str = "http://localhost:5173"   # used to build the password-reset link + CORS

    # Shared secret the external scheduler (GitHub Actions cron) sends to trigger
    # the daily job in production. Empty = the endpoint is disabled.
    job_trigger_token: str = ""

    # Email (Gmail SMTP) — used to send new managers their temporary password
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    smtp_user: str = ""        # your Gmail address
    smtp_password: str = ""    # a Gmail App Password (not your normal password)
    smtp_from: str = ""        # defaults to smtp_user if blank

    # The six Nigerian national parks
    parks: List[str] = [
        "yankari",
        "cross_river",
        "gashaka_gumti",
        "kainji_lake",
        "chad_basin",
        "old_oyo",
    ]

    @property
    def jwt_expire_minutes(self) -> int:
        return self.jwt_expiry_hours * 60

    @property
    def email_enabled(self) -> bool:
        return bool(self.smtp_user and self.smtp_password)


settings = Settings()


PARKS_META = {
    "yankari": {
        "display_name": "Yankari Game Reserve",
        "state": "Bauchi",
        "ecosystem": "savanna",
        "area_km2": 2244,
        "lat": 9.87,
        "lon": 10.47,
    },
    "cross_river": {
        "display_name": "Cross River National Park",
        "state": "Cross River",
        "ecosystem": "rainforest",
        "area_km2": 4000,
        "lat": 5.92,
        "lon": 8.72,
    },
    "gashaka_gumti": {
        "display_name": "Gashaka-Gumti National Park",
        "state": "Taraba / Adamawa",
        "ecosystem": "mixed",
        "area_km2": 6731,
        "lat": 7.80,
        "lon": 11.88,
    },
    "kainji_lake": {
        "display_name": "Kainji Lake National Park",
        "state": "Niger / Kebbi",
        "ecosystem": "savanna",
        "area_km2": 5341,
        "lat": 10.32,
        "lon": 4.58,
    },
    "chad_basin": {
        "display_name": "Chad Basin National Park",
        "state": "Borno / Yobe",
        "ecosystem": "sahel",
        "area_km2": 2258,
        "lat": 12.87,
        "lon": 13.48,
    },
    "old_oyo": {
        "display_name": "Old Oyo National Park",
        "state": "Oyo",
        "ecosystem": "savanna",
        "area_km2": 2512,
        "lat": 8.37,
        "lon": 3.92,
    },
}


# Park bounding boxes (min_lon, min_lat, max_lon, max_lat), derived from the real
# WDPA boundary polygons (scripts/extract_park_boundaries.py) so the four zone
# quadrants tile the actual park. Chad Basin uses its WDPA-centroid approximation.
PARK_BBOX = {
    "yankari":       (10.195, 9.561, 10.797, 10.070),
    "cross_river":   (8.310,  5.096,  9.354,  6.467),
    "gashaka_gumti": (11.164, 6.945, 12.208,  8.079),
    "kainji_lake":   (3.680,  9.655,  5.306, 10.400),
    "chad_basin":    (13.951, 12.100, 14.449, 12.590),
    "old_oyo":       (3.581,  8.206,  4.343,  9.022),
}


def park_zones(park_id: str):
    """Return the four geographic quadrant zones for a park as a list of dicts.

    Each park is divided into North-West, North-East, South-West, South-East
    quadrants by splitting its bounding box at the midpoint. This is the
    "manual division into four zones based on geography" described in the proposal.
    """
    min_lon, min_lat, max_lon, max_lat = PARK_BBOX[park_id]
    mid_lon = (min_lon + max_lon) / 2
    mid_lat = (min_lat + max_lat) / 2
    return [
        {"name": "North-West", "min_lon": min_lon, "min_lat": mid_lat, "max_lon": mid_lon, "max_lat": max_lat},
        {"name": "North-East", "min_lon": mid_lon, "min_lat": mid_lat, "max_lon": max_lon, "max_lat": max_lat},
        {"name": "South-West", "min_lon": min_lon, "min_lat": min_lat, "max_lon": mid_lon, "max_lat": mid_lat},
        {"name": "South-East", "min_lon": mid_lon, "min_lat": min_lat, "max_lon": max_lon, "max_lat": mid_lat},
    ]