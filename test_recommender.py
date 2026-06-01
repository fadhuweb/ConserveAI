import sys
sys.path.insert(0, 'src/optimizer')

from ilp_recommender import ILPConstraints, recommend, urgency_constraints
from catalog import CATALOG_BY_ID

BUDGET = 10_000.0

scenarios = [
    ("Fire critical",            {"fire": 0.92, "drought": 0.30, "vegetation": 0.25}),
    ("Drought + veg high",       {"fire": 0.30, "drought": 0.88, "vegetation": 0.80}),
    ("All threats moderate",     {"fire": 0.60, "drought": 0.55, "vegetation": 0.52}),
    ("Calm period",              {"fire": 0.20, "drought": 0.15, "vegetation": 0.18}),
]

for label, probs in scenarios:
    floors = urgency_constraints(probs, BUDGET)
    constraints = ILPConstraints(budget=BUDGET, min_spend_per_threat=floors)
    result = recommend(probs, constraints)

    print(f"=== {label} ===")
    print(f"  Probs  : {probs}")
    print(f"  Floors : {floors}")
    print(f"  Status : {result.status}   Score: {result.total_score}   Cost: ${result.total_cost:,}")
    print("  Allocation:")
    for iid, u in result.allocation.items():
        if u > 0:
            inv = CATALOG_BY_ID[iid]
            print(f"    {inv.name:<25} {u} units   ${inv.cost * u:,.0f}")
    print("  Risk reduction:")
    for threat, d in result.risk_reduction.items():
        print(f"    {threat:<12} {d['reduction_pct']}%")
    print()