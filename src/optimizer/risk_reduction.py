"""Risk reduction utilities shared by the ILP recommender and baselines.

Effectiveness model
-------------------
Uses a multiplicative (diminishing-returns) model for post-processing:

    survival = product of (1 - eff_i) ^ units_i   for all interventions i
    overall_effectiveness = 1 - survival

This means each additional unit reduces the *remaining* risk rather than
a fixed absolute amount.  Example for water_truck (eff=0.18, 8 units):

    survival = (1 - 0.18)^8 = 0.82^8 = 0.204
    effectiveness = 1 - 0.204 = 79.6%   (not 144% → capped at 100%)

The ILP objective remains linear (units × per-unit effectiveness) for
tractability.  Only the displayed risk reduction numbers use this model.
"""

from typing import Dict

from catalog import CATALOG_BY_ID, THREAT_KEYS, Intervention


def compute_risk_reduction(
    allocation: Dict[str, int],
    probs: Dict[str, float],
    catalog_by_id: Dict[str, Intervention] = CATALOG_BY_ID,
) -> Dict[str, Dict]:
    """Return per-threat risk reduction using a diminishing-returns model.

    Args:
        allocation:    {intervention_id: units}
        probs:         {threat: probability}
        catalog_by_id: lookup dict (override for sensitivity analysis)

    Returns:
        {threat: {prob_before, effectiveness, prob_after,
                  risk_reduction, reduction_pct}}
    """
    result = {}
    for threat in THREAT_KEYS:
        # Multiplicative survival: each intervention independently reduces
        # the remaining risk fraction
        survival = 1.0
        for iid, units in allocation.items():
            if iid not in catalog_by_id or units <= 0:
                continue
            eff_per_unit = catalog_by_id[iid].effectiveness.get(threat, 0.0)
            if eff_per_unit > 0:
                survival *= (1.0 - eff_per_unit) ** units

        effectiveness = round(1.0 - survival, 4)
        p_before      = probs.get(threat, 0.0)

        result[threat] = {
            "prob_before":    round(p_before, 4),
            "effectiveness":  effectiveness,
            "prob_after":     round(p_before * survival, 4),
            "risk_reduction": round(p_before * effectiveness, 4),
            "reduction_pct":  round(effectiveness * 100, 1),
        }
    return result


def total_score(
    allocation: Dict[str, int],
    probs: Dict[str, float],
    catalog_by_id: Dict[str, Intervention] = CATALOG_BY_ID,
) -> float:
    """Weighted sum of risk reductions across threats."""
    rr = compute_risk_reduction(allocation, probs, catalog_by_id)
    return sum(rr[t]["risk_reduction"] for t in THREAT_KEYS)


def allocation_summary(
    allocation: Dict[str, int],
    probs: Dict[str, float],
    catalog_by_id: Dict[str, Intervention] = CATALOG_BY_ID,
) -> Dict:
    """Full summary dict suitable for JSON serialisation."""
    rr   = compute_risk_reduction(allocation, probs, catalog_by_id)
    cost = sum(
        catalog_by_id[iid].cost * u
        for iid, u in allocation.items()
        if iid in catalog_by_id
    )
    items = [
        {
            "id":    iid,
            "name":  catalog_by_id[iid].name if iid in catalog_by_id else iid,
            "units": u,
            "cost":  catalog_by_id[iid].cost * u if iid in catalog_by_id else 0,
        }
        for iid, u in allocation.items()
        if u > 0
    ]
    return {
        "allocation":     items,
        "total_cost":     round(cost, 2),
        "risk_reduction": rr,
        "total_score":    round(total_score(allocation, probs, catalog_by_id), 6),
    }