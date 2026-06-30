import sys
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.backend.auth.dependencies import get_current_user, park_scoped
from src.backend.database import get_db
from src.backend.models.forecast import Forecast
from src.backend.models.user import User
from src.backend.models.zone import Zone
from src.backend.models.recommendation import Recommendation, Allocation
from src.backend.schemas.recommendation import (
    RecommendRequest, RecommendResponse,
    SensitivityRequest, SensitivityResponse,
    AllocationItem, ThreatReduction, PostInterventionForecast,
    ZoneAllocationItem, RecommendationSummary, BaselineRow,
)
from src.backend.config import settings

# Optimizer lives in src/optimizer
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "optimizer"))
from ilp_recommender import ILPConstraints, recommend, urgency_constraints
from sensitivity import run_sensitivity
from catalog import CATALOG_BY_ID, INTERVENTION_TYPES
from baselines import even_split, patrol_only

router = APIRouter(tags=["recommendations"])


def _distribute_units(total_units: int, weights: List[float], offset: int = 0) -> List[int]:
    """Split total_units across zones proportional to weights (largest-remainder).

    Equal weights reduce to an even split. Integer units always sum to total_units.
    `offset` rotates the tie-break order so that, across several interventions,
    leftover units spread across zones instead of always landing on the first one.
    """
    n = len(weights)
    if total_units <= 0 or n == 0:
        return [0] * n
    s = sum(weights)
    if s <= 0:                       # all-zero weights → fall back to equal
        weights = [1.0] * n
        s = float(n)
    raw   = [total_units * w / s for w in weights]
    floor = [int(x) for x in raw]
    rem   = total_units - sum(floor)
    # Rank by largest fractional part; break ties by a rotated index so equal
    # weights don't systematically favour the lowest-index zone.
    order = sorted(
        range(n),
        key=lambda i: (-(raw[i] - floor[i]), (i + offset) % n),
    )
    for i in range(rem):
        floor[order[i]] += 1
    return floor


def _latest_probs(park: str, db: Session) -> dict:
    row = (
        db.query(Forecast)
        .filter(Forecast.park == park)
        .order_by(Forecast.date.desc())
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No forecasts found for {park}. Run the backfill job first.",
        )
    return {"fire": row.fire_prob, "drought": row.drought_prob, "vegetation": row.veg_prob}


@router.post("/recommend", response_model=RecommendResponse, summary="Budget-constrained ILP recommendation with zone allocation")
def recommend_interventions(
    body: RecommendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    park_scoped(body.park, current_user)

    probs = _latest_probs(body.park, db)

    if body.use_urgency_constraints and body.min_spend_per_threat is None:
        floors = urgency_constraints(probs, body.budget)
    else:
        floors = body.min_spend_per_threat or {}

    constraints = ILPConstraints(
        budget=body.budget,
        min_spend_per_threat=floors,
        type_enabled=body.type_enabled or {t: True for t in INTERVENTION_TYPES},
        max_units_per_type=body.max_units_per_type or {},
    )

    result = recommend(probs, constraints)
    rr = result.risk_reduction

    # Park-level totals by intervention
    allocation_items = [
        AllocationItem(
            id=iid,
            name=CATALOG_BY_ID[iid].name,
            units=units,
            cost=CATALOG_BY_ID[iid].cost * units,
        )
        for iid, units in result.allocation.items()
        if units > 0
    ]

    # Persist the recommendation
    rec = Recommendation(
        park_id=body.park,
        user_id=current_user.id,
        budget=body.budget,
        total_cost=result.total_cost,
        total_risk_reduction=result.total_score,
    )
    db.add(rec)
    db.flush()   # assign rec.id

    # Distribute each intervention's units across the park's four zones,
    # proportional to manager-set zone priority weights (equal if omitted).
    zones = db.query(Zone).filter(Zone.park_id == body.park).order_by(Zone.id).all()
    weights = [
        (body.zone_weights or {}).get(z.id, 1.0)
        for z in zones
    ]
    zone_allocations: List[ZoneAllocationItem] = []

    for offset, (iid, units) in enumerate(result.allocation.items()):
        if units <= 0:
            continue
        unit_cost = CATALOG_BY_ID[iid].cost
        per_zone  = _distribute_units(units, weights, offset=offset)
        for zone, z_units in zip(zones, per_zone):
            if z_units <= 0:
                continue
            z_cost = unit_cost * z_units
            db.add(Allocation(
                recommendation_id=rec.id,
                intervention_id=iid,
                park_id=body.park,
                zone_id=zone.id,
                units=z_units,
                total_cost=z_cost,
            ))
            zone_allocations.append(ZoneAllocationItem(
                zone_id=zone.id,
                zone_name=zone.name,
                intervention_id=iid,
                intervention_name=CATALOG_BY_ID[iid].name,
                units=z_units,
                cost=z_cost,
            ))

    db.commit()

    # Baseline comparison: how the ILP plan stacks up against naive strategies
    even = even_split(probs, body.budget)
    patrol = patrol_only(probs, body.budget)
    baseline_comparison = [
        BaselineRow(strategy="ILP (optimal)", total_score=result.total_score, total_cost=result.total_cost),
        BaselineRow(strategy="Even split",    total_score=even["total_score"],   total_cost=even["total_cost"]),
        BaselineRow(strategy="Patrol only",   total_score=patrol["total_score"], total_cost=patrol["total_cost"]),
    ]

    return RecommendResponse(
        recommendation_id=rec.id,
        status=result.status,
        allocation=allocation_items,
        zone_allocations=zone_allocations,
        total_cost=result.total_cost,
        risk_reduction={t: ThreatReduction(**d) for t, d in rr.items()},
        total_score=result.total_score,
        solve_time_ms=result.solve_time_ms,
        urgency_floors=floors,
        current_forecast=PostInterventionForecast(
            fire=probs["fire"],
            drought=probs["drought"],
            vegetation=probs["vegetation"],
        ),
        post_intervention_forecast=PostInterventionForecast(
            fire=rr["fire"]["prob_after"],
            drought=rr["drought"]["prob_after"],
            vegetation=rr["vegetation"]["prob_after"],
        ),
        baseline_comparison=baseline_comparison,
    )


@router.get("/recommendations/{park}", response_model=List[RecommendationSummary], summary="Past recommendations for a park")
def list_recommendations(
    park: str,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List past recommendations for a park (most recent first)."""
    park_scoped(park, current_user)
    rows = (
        db.query(Recommendation)
        .filter(Recommendation.park_id == park)
        .order_by(Recommendation.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        RecommendationSummary(
            id=r.id,
            park_id=r.park_id,
            budget=float(r.budget),
            total_cost=float(r.total_cost),
            total_risk_reduction=float(r.total_risk_reduction),
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]


@router.post("/sensitivity", response_model=SensitivityResponse, summary="Sensitivity analysis on cost & effectiveness assumptions")
def sensitivity_analysis(
    body: SensitivityRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    park_scoped(body.park, current_user)

    probs = _latest_probs(body.park, db)
    floors = urgency_constraints(probs, body.budget)
    constraints = ILPConstraints(budget=body.budget, min_spend_per_threat=floors)

    report = run_sensitivity(probs, constraints, n_samples=body.n_samples, perturb_pct=body.perturb_pct)

    return SensitivityResponse(
        nominal_score=report["nominal"]["total_score"],
        score_mean=report["score_mean"],
        score_std=report["score_std"],
        score_ci_95=report["score_ci_95"],
        selection_freq=report["selection_freq"],
        units_mean=report["units_mean"],
        n_optimal=report["n_optimal"],
        n_samples=report["n_samples"],
    )