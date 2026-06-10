from typing import List, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.backend.auth.dependencies import get_current_user, require_admin, park_scoped
from src.backend.config import settings, PARKS_META
from src.backend.database import get_db
from src.backend.models.forecast import Forecast
from src.backend.models.intervention import InterventionCatalog
from src.backend.models.raw_features import DailyFeatures
from src.backend.models.user import User
from src.backend.models.zone import Zone
from src.backend.schemas.forecast import ForecastOut, ParkOverview, DriversResponse
from src.backend.schemas.park import ParkMeta, CatalogItem, ZoneOut

router = APIRouter(tags=["forecasts"])


# ── Parks ─────────────────────────────────────────────────────────────────────

@router.get("/parks", response_model=List[ParkMeta], summary="List all six parks with metadata")
def list_parks(_: User = Depends(get_current_user)):
    """Return metadata for all six parks."""
    return [ParkMeta(id=k, **v) for k, v in PARKS_META.items()]


@router.get("/parks/{park_id}", response_model=ParkMeta, summary="Get one park's metadata")
def get_park(park_id: str, _: User = Depends(get_current_user)):
    if park_id not in PARKS_META:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown park: {park_id}")
    return ParkMeta(id=park_id, **PARKS_META[park_id])


@router.get("/parks/{park_id}/zones", response_model=List[ZoneOut], summary="List a park's four zones")
def get_park_zones(
    park_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if park_id not in PARKS_META:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown park: {park_id}")
    park_scoped(park_id, current_user)
    return db.query(Zone).filter(Zone.park_id == park_id).order_by(Zone.id).all()


# ── Intervention catalog ──────────────────────────────────────────────────────

@router.get("/catalog", response_model=List[CatalogItem], summary="Intervention catalog with costs & cited effectiveness")
def get_catalog(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Return the full intervention catalog with costs and effectiveness values."""
    return db.query(InterventionCatalog).all()


# ── Forecasts ─────────────────────────────────────────────────────────────────

@router.get("/forecasts/{park}", response_model=List[ForecastOut], summary="Forecast history for a park (park-scoped)")
def get_park_forecasts(
    park: str,
    days: int = Query(default=60, ge=1, le=365),
    order: Literal["asc", "desc"] = Query(default="desc"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if park not in settings.parks:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown park: {park}")
    park_scoped(park, current_user)

    q = db.query(Forecast).filter(Forecast.park == park)
    if order == "asc":
        rows = q.order_by(Forecast.date.asc()).limit(days).all()
    else:
        rows = q.order_by(Forecast.date.desc()).limit(days).all()
    return rows


@router.get("/forecasts/{park}/latest", response_model=ForecastOut, summary="Most recent forecast for a park")
def get_latest_forecast(
    park: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if park not in settings.parks:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown park: {park}")
    park_scoped(park, current_user)

    row = (
        db.query(Forecast)
        .filter(Forecast.park == park)
        .order_by(Forecast.date.desc())
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No forecasts found")
    return row


@router.get("/forecasts/{park}/drivers", response_model=DriversResponse,
            summary="Key feature drivers behind a park's current forecast")
def forecast_drivers(
    park: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Plain-language drivers: which features are raising/lowering each threat."""
    import pandas as pd
    from datetime import timedelta
    from src.backend.services.drivers import compute_drivers

    if park not in settings.parks:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown park: {park}")
    park_scoped(park, current_user)

    fc = (
        db.query(Forecast)
        .filter(Forecast.park == park)
        .order_by(Forecast.date.desc())
        .first()
    )
    if fc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No forecasts found")

    probs = {"fire": fc.fire_prob, "drought": fc.drought_prob, "vegetation": fc.veg_prob}

    cutoff = fc.date - timedelta(days=90)
    daily = (
        db.query(DailyFeatures)
        .filter(DailyFeatures.park == park, DailyFeatures.date >= cutoff, DailyFeatures.date <= fc.date)
        .order_by(DailyFeatures.date)
        .all()
    )
    if not daily:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No feature history for this park")

    history = pd.DataFrame([{
        "date":          r.date,
        "precipitation": r.precipitation,
        "temp_max":      r.temp_max,
        "temp_min":      r.temp_min,
        "ndvi":          r.ndvi,
        "firms_count":   r.firms_count or 0,
    } for r in daily])

    drivers = compute_drivers(history, park, fc.date)
    return DriversResponse(park=park, date=str(fc.date), probs=probs, drivers=drivers)


@router.get("/national-overview", response_model=List[ParkOverview], summary="Latest forecast for all parks (admin only)")
def national_overview(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Latest forecast for each park — admin only."""
    overview = []
    for park in settings.parks:
        row = (
            db.query(Forecast)
            .filter(Forecast.park == park)
            .order_by(Forecast.date.desc())
            .first()
        )
        if row:
            overview.append(ParkOverview(
                park=park,
                latest_date=row.date,
                fire_prob=row.fire_prob,
                drought_prob=row.drought_prob,
                veg_prob=row.veg_prob,
            ))
    return overview