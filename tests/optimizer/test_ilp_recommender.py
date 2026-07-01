"""Unit tests for the ILP intervention recommender.

These verify the optimiser's core guarantees (budget, capacity, type toggles,
urgency floors) and that it responds correctly to different input data values.
"""
from ilp_recommender import recommend, ILPConstraints, urgency_constraints
from catalog import CATALOG_BY_ID, INTERVENTION_TYPES
from explain import build_rationale

BALANCED  = {"fire": 0.5, "drought": 0.5, "vegetation": 0.5}
HIGH_FIRE = {"fire": 0.9, "drought": 0.2, "vegetation": 0.2}


def test_returns_optimal_solution():
    res = recommend(BALANCED, ILPConstraints(budget=10_000))
    assert res.status == "Optimal"
    assert res.allocation                      # at least one intervention chosen


def test_respects_budget():
    res = recommend(BALANCED, ILPConstraints(budget=8_000))
    assert res.total_cost <= 8_000


def test_respects_catalog_max_units():
    # With a huge budget the optimiser must still honour each catalog cap.
    res = recommend(BALANCED, ILPConstraints(budget=1_000_000))
    for iid, units in res.allocation.items():
        assert units <= CATALOG_BY_ID[iid].max_units


def test_zero_budget_allocates_nothing():
    res = recommend(BALANCED, ILPConstraints(budget=0))
    assert sum(res.allocation.values()) == 0
    assert res.total_cost == 0


def test_larger_budget_never_scores_worse():
    small = recommend(BALANCED, ILPConstraints(budget=3_000))
    large = recommend(BALANCED, ILPConstraints(budget=15_000))
    assert large.total_score >= small.total_score
    assert large.total_cost >= small.total_cost


def test_disabled_type_gets_no_units():
    enabled = {t: True for t in INTERVENTION_TYPES}
    enabled["water"] = False
    res = recommend(BALANCED, ILPConstraints(budget=20_000, type_enabled=enabled))
    for iid, units in res.allocation.items():
        if units > 0:
            assert CATALOG_BY_ID[iid].type != "water"


def test_high_fire_deploys_a_fire_effective_intervention():
    res = recommend(HIGH_FIRE, ILPConstraints(budget=10_000))
    deployed = [CATALOG_BY_ID[i] for i, u in res.allocation.items() if u > 0]
    assert deployed
    assert any(inv.effectiveness.get("fire", 0) > 0 for inv in deployed)


def test_urgency_floors_scale_with_probability():
    floors = urgency_constraints({"fire": 0.9, "drought": 0.6, "vegetation": 0.2}, 10_000)
    assert floors["fire"] == 10_000 * 0.40        # critical (>=0.85)
    assert floors["drought"] == 10_000 * 0.10     # moderate (>=0.50)
    assert floors["vegetation"] == 0.0            # low (<0.50)


def test_urgency_constraints_stay_feasible():
    # All three critical at once: floors get scaled down so a solution still exists.
    probs = {"fire": 0.9, "drought": 0.9, "vegetation": 0.9}
    floors = urgency_constraints(probs, 10_000)
    res = recommend(probs, ILPConstraints(budget=10_000, min_spend_per_threat=floors))
    assert res.status == "Optimal"


def test_rationale_justifies_every_selected_intervention():
    res = recommend(HIGH_FIRE, ILPConstraints(budget=10_000))
    expl = build_rationale(HIGH_FIRE, {}, res.allocation, res.total_cost, 10_000)
    assert "fire" in expl["summary"].lower()
    for iid, units in res.allocation.items():
        if units > 0:
            assert expl["reasons"].get(iid)          # every chosen item is explained


def test_rationale_notes_the_urgency_floor():
    probs = {"fire": 0.9, "drought": 0.9, "vegetation": 0.2}
    floors = urgency_constraints(probs, 10_000)
    res = recommend(probs, ILPConstraints(budget=10_000, min_spend_per_threat=floors))
    expl = build_rationale(probs, floors, res.allocation, res.total_cost, 10_000)
    assert any("minimum spend" in p for p in expl["points"])
