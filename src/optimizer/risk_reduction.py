"""Risk reduction utilities shared by the ILP recommender and baselines."""

from typing import Dict

from catalog import CATALOG_BY_ID, THREAT_KEYS, Intervention


def compute_risk_reduction(
    allocation: Dict[str, int],
    probs: Dict[str, float],
    catalog_by_id: Dict[str, Intervention] = CATALOG_BY_ID,
) -> Dict[str, Dict]:
    """Return per-threat risk reduction metrics for a given allocation.

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
        raw_eff = sum(
            catalog_by_id[iid].effectiveness.get(threat, 0.0) * units
            for iid, units in allocation.items()
            if iid in catalog_by_id
        )
        eff_cap  = min(1.0, raw_eff)
        p_before = probs.get(threat, 0.0)
        result[threat] = {
            "prob_before":    round(p_before, 4),
            "effectiveness":  round(eff_cap, 4),
            "prob_after":     round(p_before * (1 - eff_cap), 4),
            "risk_reduction": round(p_before * eff_cap, 4),
            "reduction_pct":  round(eff_cap * 100, 1),
        }
    return result


def total_score(
    allocation: Dict[str, int],
    probs: Dict[str, float],
    catalog_by_id: Dict[str, Intervention] = CATALOG_BY_ID,
) -> float:
    """Weighted sum of risk reductions across threats (ILP objective value)."""
    rr = compute_risk_reduction(allocation, probs, catalog_by_id)
    return sum(rr[t]["risk_reduction"] for t in THREAT_KEYS)


def allocation_summary(
    allocation: Dict[str, int],
    probs: Dict[str, float],
    catalog_by_id: Dict[str, Intervention] = CATALOG_BY_ID,
) -> Dict:
    """Full summary dict suitable for JSON serialisation."""
    rr         = compute_risk_reduction(allocation, probs, catalog_by_id)
    cost       = sum(
        catalog_by_id[iid].cost * u
        for iid, u in allocation.items()
        if iid in catalog_by_id
    )
    items      = [
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
