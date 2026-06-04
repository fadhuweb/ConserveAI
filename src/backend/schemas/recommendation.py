from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class RecommendRequest(BaseModel):
    park:   str
    budget: float = Field(default=10_000.0, gt=0)
    use_urgency_constraints: bool = True
    min_spend_per_threat: Optional[Dict[str, float]] = None   # manual override
    type_enabled:         Optional[Dict[str, bool]]  = None
    max_units_per_type:   Optional[Dict[str, int]]   = None
    # Per-zone priority weights {zone_id: weight} from manager local knowledge.
    # Units distribute proportionally to weight; omitted = equal split.
    zone_weights:         Optional[Dict[int, float]] = None


class AllocationItem(BaseModel):
    id:    str
    name:  str
    units: int
    cost:  float


class ThreatReduction(BaseModel):
    prob_before:    float
    effectiveness:  float
    prob_after:     float
    risk_reduction: float
    reduction_pct:  float


class PostInterventionForecast(BaseModel):
    fire:       float
    drought:    float
    vegetation: float


class ZoneAllocationItem(BaseModel):
    zone_id:           int
    zone_name:         str
    intervention_id:   str
    intervention_name: str
    units:             int
    cost:              float


class RecommendResponse(BaseModel):
    recommendation_id:         int
    status:                    str
    allocation:                List[AllocationItem]       # park-level totals by intervention
    zone_allocations:          List[ZoneAllocationItem]   # per-zone breakdown
    total_cost:                float
    risk_reduction:            Dict[str, ThreatReduction]
    total_score:               float
    solve_time_ms:             float
    urgency_floors:            Dict[str, float]
    current_forecast:          PostInterventionForecast   # probabilities WITHOUT intervention
    post_intervention_forecast: PostInterventionForecast  # projected probabilities AFTER intervention


class RecommendationSummary(BaseModel):
    id:                   int
    park_id:              str
    budget:               float
    total_cost:           float
    total_risk_reduction: float
    created_at:           str


class SensitivityRequest(BaseModel):
    park:        str
    budget:      float = Field(default=10_000.0, gt=0)
    n_samples:   int   = Field(default=50, ge=10, le=100)
    perturb_pct: float = Field(default=0.25, gt=0, le=0.5)


class SensitivityResponse(BaseModel):
    nominal_score:   float
    score_mean:      float
    score_std:       float
    score_ci_95:     List[float]
    selection_freq:  Dict[str, float]
    units_mean:      Dict[str, float]
    n_optimal:       int
    n_samples:       int