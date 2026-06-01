"""ILP-based intervention recommender using PuLP.

Formulation
-----------
Decision variables
    x[i]  ≥ 0, integer — units of intervention i deployed

Objective  (maximise)
    Σ_i  x[i] · Σ_j  prob[j] · effectiveness[i][j]

    Each unit of intervention i contributes prob[j] · eff[i][j] reduction
    to threat j.  Summing over threats gives the composite risk score.

Constraints (Tasks 43 & 44)
    1. Total budget:       Σ_i cost[i]·x[i]  ≤  budget
    2. Catalog capacity:   x[i]  ≤  catalog max_units[i]
    3. Type toggles:       x[i]  =  0  if intervention type is disabled
    4. Min spend/threat:   Σ_{i: eff[i][j]>0} cost[i]·x[i]  ≥  min_spend[j]
    5. Max units/type:     Σ_{i of type t} x[i]  ≤  max_units_per_type[t]

Risk reduction is capped at 1.0 per threat in post-processing; the
objective uses uncapped values so the formulation stays linear.

Urgency-aware constraints
    urgency_constraints(probs, budget) derives min_spend_per_threat
    automatically from threat probabilities so the ILP is forced to
    address high-probability threats even when cheaper interventions
    targeting other threats would otherwise dominate.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pulp

from catalog import CATALOG, CATALOG_BY_ID, INTERVENTION_TYPES, THREAT_KEYS, Intervention


# ── Constraint container ──────────────────────────────────────────────────────

@dataclass
class ILPConstraints:
    """User-adjustable constraints for the recommender.

    Attributes:
        budget:               Total USD available for this 30-day period.
        type_enabled:         Toggle each intervention type on/off.
        min_spend_per_threat: Minimum USD allocated to interventions that
                              address each threat (0.0 = no minimum).
        max_units_per_type:   Hard cap on total units of each type deployed
                              across all interventions of that type.
                              Empty dict = no additional cap beyond catalog.
    """
    budget:               float                = 10_000.0
    type_enabled:         Dict[str, bool]      = field(default_factory=lambda: {
                              t: True for t in INTERVENTION_TYPES
                          })
    min_spend_per_threat: Dict[str, float]     = field(default_factory=lambda: {
                              t: 0.0 for t in THREAT_KEYS
                          })
    max_units_per_type:   Dict[str, int]       = field(default_factory=dict)


# ── Result container ──────────────────────────────────────────────────────────

@dataclass
class ILPResult:
    status:         str               # "Optimal" | "Infeasible" | "Unbounded" | ...
    allocation:     Dict[str, int]    # {intervention_id: units}
    total_cost:     float
    risk_reduction: Dict[str, Dict]   # per-threat reduction detail
    total_score:    float             # objective value (sum of weighted reductions)
    solve_time_ms:  float
    infeasibility_hint: Optional[str] = None


# ── Urgency helper ───────────────────────────────────────────────────────────

def urgency_constraints(
    probs: Dict[str, float],
    budget: float,
) -> Dict[str, float]:
    """Derive min_spend_per_threat floors from threat probabilities.

    Tier      Probability     Min spend (% of budget)
    --------  --------------  -----------------------
    Critical  p >= 0.85       40 %
    High      p >= 0.70       25 %
    Moderate  p >= 0.50       10 %
    Low       p <  0.50        0 %

    If the sum of all floors exceeds 80 % of the budget (possible when
    multiple threats are simultaneously critical), every floor is scaled
    down proportionally so the ILP always has a feasible solution.

    Usage
    -----
        constraints = ILPConstraints(
            budget=10_000,
            min_spend_per_threat=urgency_constraints(probs, 10_000),
        )
    """
    floors: Dict[str, float] = {}
    for threat, p in probs.items():
        if p >= 0.85:
            floors[threat] = budget * 0.40
        elif p >= 0.70:
            floors[threat] = budget * 0.25
        elif p >= 0.50:
            floors[threat] = budget * 0.10
        else:
            floors[threat] = 0.0

    total = sum(floors.values())
    cap   = budget * 0.80
    if total > cap:
        scale  = cap / total
        floors = {t: v * scale for t, v in floors.items()}

    return {t: round(v, 2) for t, v in floors.items()}


# ── Solver ────────────────────────────────────────────────────────────────────

def recommend(
    probs: Dict[str, float],
    constraints: Optional[ILPConstraints] = None,
    catalog: List[Intervention] = CATALOG,
    verbose: bool = False,
) -> ILPResult:
    """Solve the ILP and return the optimal intervention allocation.

    Args:
        probs:       {threat: probability} for fire, drought, vegetation.
        constraints: User-adjustable constraints (defaults if None).
        catalog:     Intervention catalog (override for sensitivity analysis).
        verbose:     If True, print PuLP solver output.

    Returns:
        ILPResult with allocation, cost, risk reduction, and solve time.
    """
    if constraints is None:
        constraints = ILPConstraints()

    t0 = time.perf_counter()

    prob = pulp.LpProblem("conservation_recommender", pulp.LpMaximize)

    # Decision variables
    x = {
        inv.id: pulp.LpVariable(f"x_{inv.id}", lowBound=0, cat="Integer")
        for inv in catalog
    }

    # Composite score per intervention (weighted by current threat probabilities)
    score = {
        inv.id: sum(probs.get(t, 0.0) * inv.effectiveness.get(t, 0.0) for t in THREAT_KEYS)
        for inv in catalog
    }

    # Objective
    prob += pulp.lpSum(score[inv.id] * x[inv.id] for inv in catalog)

    # Constraint 1: total budget
    prob += pulp.lpSum(inv.cost * x[inv.id] for inv in catalog) <= constraints.budget, "budget"

    # Constraint 2: catalog capacity + Constraint 3: type toggles
    for inv in catalog:
        enabled = constraints.type_enabled.get(inv.type, True)
        if not enabled:
            prob += x[inv.id] == 0, f"toggle_{inv.id}"
        else:
            prob += x[inv.id] <= inv.max_units, f"cap_{inv.id}"

    # Constraint 4: minimum spend per threat
    for threat in THREAT_KEYS:
        min_spend = constraints.min_spend_per_threat.get(threat, 0.0)
        if min_spend <= 0:
            continue
        relevant = [inv for inv in catalog if inv.effectiveness.get(threat, 0.0) > 0
                    and constraints.type_enabled.get(inv.type, True)]
        if not relevant:
            # No enabled intervention addresses this threat — skip to avoid infeasibility
            continue
        prob += (
            pulp.lpSum(inv.cost * x[inv.id] for inv in relevant) >= min_spend,
            f"min_spend_{threat}",
        )

    # Constraint 5: max units per type
    for itype, max_u in constraints.max_units_per_type.items():
        group = [inv for inv in catalog if inv.type == itype]
        if group:
            prob += pulp.lpSum(x[inv.id] for inv in group) <= max_u, f"max_type_{itype}"

    # Solve
    solver = pulp.PULP_CBC_CMD(msg=1 if verbose else 0)
    prob.solve(solver)

    solve_ms = (time.perf_counter() - t0) * 1000
    status   = pulp.LpStatus[prob.status]

    allocation = {inv.id: int(pulp.value(x[inv.id]) or 0) for inv in catalog}
    total_cost = sum(
        CATALOG_BY_ID.get(iid, next(i for i in catalog if i.id == iid)).cost * units
        for iid, units in allocation.items()
    )

    # Risk reduction (post-process with cap)
    risk_reduction = {}
    for threat in THREAT_KEYS:
        raw_eff  = sum(
            next(i for i in catalog if i.id == iid).effectiveness.get(threat, 0.0) * units
            for iid, units in allocation.items()
        )
        eff_cap  = min(1.0, raw_eff)
        p_before = probs.get(threat, 0.0)
        risk_reduction[threat] = {
            "prob_before":       round(p_before, 4),
            "effectiveness":     round(eff_cap, 4),
            "prob_after":        round(p_before * (1 - eff_cap), 4),
            "risk_reduction":    round(p_before * eff_cap, 4),
            "reduction_pct":     round(eff_cap * 100, 1),
        }

    total_score = float(pulp.value(prob.objective) or 0.0)

    hint = None
    if status != "Optimal":
        hint = (
            "Check if min_spend constraints exceed budget, or all "
            "relevant intervention types are toggled off."
        )

    return ILPResult(
        status=status,
        allocation=allocation,
        total_cost=round(total_cost, 2),
        risk_reduction=risk_reduction,
        total_score=round(total_score, 6),
        solve_time_ms=round(solve_ms, 2),
        infeasibility_hint=hint,
    )
