from typing import List, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.backend.auth.dependencies import get_current_user, require_admin, park_scoped
from src.backend.config import settings, PARKS_META
from src.backend.database import get_db
from src.backend.models.forecast import Forecast
from src.backend.models.intervention import InterventionCatalog
from src.backend.models.user import User
from src.backend.models.zone import Zone
from src.backend.schemas.forecast import ForecastOut, ParkOverview
from src.backend.schemas.park import ParkMeta, CatalogItem, ZoneOut

router = APIRouter(tags=["forecasts"])


# ── Parks ─────────────────────────────────────────────────────────────────────

@router.get("/parks", response_model=List[ParkMeta])
def list_parks(_: User = Depends(get_current_user)):
    """Return metadata for all six parks."""
    return [ParkMeta(id=k, **v) for k, v in PARKS_META.items()]


@router.get("/parks/{park_id}", response_model=ParkMeta)
def get_park(park_id: str, _: User = Depends(get_current_user)):
    if park_id not in PARKS_META:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown park: {park_id}")
    return ParkMeta(id=park_id, **PARKS_META[park_id])


@router.get("/parks/{park_id}/zones", response_model=List[ZoneOut])
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

@router.get("/catalog", response_model=List[CatalogItem])
def get_catalog(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Return the full intervention catalog with costs and effectiveness values."""
    return db.query(InterventionCatalog).all()


# ── Forecasts ─────────────────────────────────────────────────────────────────

@router.get("/forecasts/{park}", response_model=List[ForecastOut])
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


@router.get("/forecasts/{park}/latest", response_model=ForecastOut)
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


@router.get("/national-overview", response_model=List[ParkOverview])
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