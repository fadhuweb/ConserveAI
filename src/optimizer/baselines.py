"""Baseline allocation strategies for comparison against the ILP recommender.

Two baselines:
  even_split   — divide budget equally across all enabled interventions,
                 rounding down to whole units.
  patrol_only  — spend entire budget on patrol interventions only
                 (fire_patrol first, then ranger), ignoring other types.
"""

import math
from typing import Dict, List, Optional

from catalog import CATALOG, INTERVENTION_TYPES, Intervention
from risk_reduction import allocation_summary


def even_split(
    probs: Dict[str, float],
    budget: float = 10_000.0,
    type_enabled: Optional[Dict[str, bool]] = None,
    catalog: List[Intervention] = CATALOG,
) -> Dict:
    """Allocate budget evenly across all enabled interventions.

    Divides budget equally per enabled intervention type, then buys as many
    units as possible within each share, respecting catalog max_units.
    """
    if type_enabled is None:
        type_enabled = {t: True for t in INTERVENTION_TYPES}

    enabled = [inv for inv in catalog if type_enabled.get(inv.type, True)]
    if not enabled:
        return allocation_summary({inv.id: 0 for inv in catalog}, probs)

    share = budget / len(enabled)
    allocation = {}
    for inv in catalog:
        if type_enabled.get(inv.type, True):
            units = min(inv.max_units, int(share // inv.cost))
        else:
            units = 0
        allocation[inv.id] = units

    return allocation_summary(allocation, probs)


def patrol_only(
    probs: Dict[str, float],
    budget: float = 10_000.0,
    catalog: List[Intervention] = CATALOG,
) -> Dict:
    """Spend entire budget on patrol interventions only.

    Prioritises fire_patrol (cheaper per unit) over ranger deployment.
    """
    patrol_invs = sorted(
        [inv for inv in catalog if inv.type == "patrol"],
        key=lambda i: i.cost,
    )
    allocation = {inv.id: 0 for inv in catalog}
    remaining  = budget

    for inv in patrol_invs:
        units = min(inv.max_units, int(remaining // inv.cost))
        allocation[inv.id] = units
        remaining -= units * inv.cost

    return allocation_summary(allocation, probs)
