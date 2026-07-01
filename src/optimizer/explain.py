"""Human-readable rationale for an ILP recommendation.

Turns the numeric allocation into plain sentences a park manager can audit:
which threats drive the plan, why each intervention was chosen, and how the
budget was used. This is the recommender's explainability layer, the decision
counterpart to the forecast drivers panel on the forecasting side.
"""
from typing import Dict, List

from catalog import CATALOG, THREAT_KEYS

_THREAT_LABEL = {
    "fire": "fire",
    "drought": "drought",
    "vegetation": "vegetation degradation",
}


def _tier(p: float) -> str:
    if p >= 0.85:
        return "critical"
    if p >= 0.70:
        return "high"
    if p >= 0.50:
        return "moderate"
    return "low"


def build_rationale(
    probs: Dict[str, float],
    floors: Dict[str, float],
    allocation: Dict[str, int],
    total_cost: float,
    budget: float,
    catalog: List = CATALOG,
) -> dict:
    """Explain one recommendation.

    Returns {summary, points, reasons} where `reasons` maps each selected
    intervention id to a one-line justification tied to the risk it addresses.
    """
    catalog_map = {inv.id: inv for inv in catalog}

    # 1. Risk profile, highest first.
    ranked = sorted(THREAT_KEYS, key=lambda t: probs.get(t, 0.0), reverse=True)
    profile = ", ".join(
        f"{_THREAT_LABEL[t]} {round(probs.get(t, 0.0) * 100)}% ({_tier(probs.get(t, 0.0))})"
        for t in ranked
    )
    summary = (
        f"Current 30-day risk is {profile}. "
        "The plan spends on the highest risks first, staying within budget."
    )

    points: List[str] = []

    # 2. Urgency floors that reshaped the allocation.
    forced = sorted(
        [t for t in THREAT_KEYS if floors.get(t, 0.0) > 0],
        key=lambda t: floors[t],
        reverse=True,
    )
    if forced:
        floor_txt = ", ".join(
            f"{round(floors[t] / budget * 100)}% of the budget on {_THREAT_LABEL[t]}"
            for t in forced
        )
        points.append(
            "Because " + " and ".join(_THREAT_LABEL[t] for t in forced)
            + f" risk is elevated, the planner reserved a minimum spend ({floor_txt}) "
            "before allocating the rest to the best overall value."
        )

    # 3. Per-intervention justification, tied to the risk it most reduces.
    reasons: Dict[str, str] = {}
    for iid, units in allocation.items():
        if units <= 0 or iid not in catalog_map:
            continue
        inv = catalog_map[iid]
        contrib = {t: probs.get(t, 0.0) * inv.effectiveness.get(t, 0.0) for t in THREAT_KEYS}
        main = max(contrib, key=contrib.get)
        eff = inv.effectiveness.get(main, 0.0)
        reasons[iid] = (
            f"Targets {_THREAT_LABEL[main]} risk: {int(round(eff * 100))}% reduction per unit."
        )

    # 4. How the budget was used.
    if budget <= 0:
        points.append("No budget was available, so no interventions were selected.")
    else:
        pct = round(total_cost / budget * 100)
        if pct < 95:
            points.append(
                f"The plan uses about {pct}% of the budget. The rest is left unspent because the "
                "most effective interventions reached their capacity limits, and weaker ones would "
                "not reduce risk enough to be worthwhile."
            )
        else:
            points.append(
                "The plan uses essentially the full budget, placing it where it removes the most risk."
            )

    return {"summary": summary, "points": points, "reasons": reasons}
