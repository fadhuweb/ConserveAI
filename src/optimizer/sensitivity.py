"""Sensitivity analysis for the ILP recommender.

Samples N parameter sets by perturbing catalog costs and effectiveness
values uniformly within ±PERTURB_PCT of their nominal values, then
solves the ILP on each sample.  Summarises:
  - distribution of total_score
  - selection frequency of each intervention
  - which parameter perturbations correlate most with score change
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from catalog import CATALOG, THREAT_KEYS, Intervention
from ilp_recommender import ILPConstraints, recommend
from risk_reduction import allocation_summary


# ── Defaults ──────────────────────────────────────────────────────────────────

N_SAMPLES    = 100
PERTURB_PCT  = 0.25   # ±25 %
RNG_SEED     = 42


# ── Helpers ───────────────────────────────────────────────────────────────────

def _perturb_catalog(
    rng: np.random.Generator,
    catalog: List[Intervention] = CATALOG,
    perturb_pct: float = PERTURB_PCT,
) -> List[Intervention]:
    """Return a catalog copy with costs and effectiveness randomly perturbed."""
    perturbed = []
    for inv in catalog:
        factor_cost = 1.0 + rng.uniform(-perturb_pct, perturb_pct)
        new_cost = max(1.0, inv.cost * factor_cost)

        new_eff = {}
        for threat, val in inv.effectiveness.items():
            factor_eff = 1.0 + rng.uniform(-perturb_pct, perturb_pct)
            new_eff[threat] = min(1.0, max(0.0, val * factor_eff))

        perturbed.append(Intervention(
            id=inv.id,
            name=inv.name,
            type=inv.type,
            cost=round(new_cost, 2),
            max_units=inv.max_units,
            effectiveness=new_eff,
        ))
    return perturbed


# ── Main analysis ─────────────────────────────────────────────────────────────

def run_sensitivity(
    probs: Dict[str, float],
    constraints: Optional[ILPConstraints] = None,
    n_samples: int = N_SAMPLES,
    perturb_pct: float = PERTURB_PCT,
    seed: int = RNG_SEED,
) -> Dict:
    """Run sensitivity analysis over perturbed catalog samples.

    Args:
        probs:       {threat: probability} — held fixed across all samples.
        constraints: ILP constraints (budget etc.) — held fixed.
        n_samples:   number of perturbation draws.
        perturb_pct: fractional perturbation range (0.25 = ±25%).
        seed:        RNG seed for reproducibility.

    Returns:
        {
          "nominal":           allocation_summary for the unperturbed run,
          "score_mean":        float,
          "score_std":         float,
          "score_min":         float,
          "score_max":         float,
          "score_ci_95":       [lower, upper],
          "selection_freq":    {intervention_id: fraction of samples selected},
          "units_mean":        {intervention_id: mean units deployed},
          "units_std":         {intervention_id: std units deployed},
          "n_optimal":         int   — samples where status == "Optimal",
          "n_samples":         int,
        }
    """
    if constraints is None:
        constraints = ILPConstraints()

    rng = np.random.default_rng(seed)

    # Nominal run (unperturbed)
    nominal_result  = recommend(probs, constraints)
    nominal_summary = allocation_summary(nominal_result.allocation, probs)

    scores: List[float] = []
    units_tracker: Dict[str, List[int]] = {inv.id: [] for inv in CATALOG}
    n_optimal = 0

    for _ in range(n_samples):
        perturbed_catalog = _perturb_catalog(rng, CATALOG, perturb_pct)
        result = recommend(probs, constraints, catalog=perturbed_catalog)

        if result.status == "Optimal":
            n_optimal += 1

        # Score evaluated on nominal probs so samples are comparable
        summary = allocation_summary(result.allocation, probs)
        scores.append(summary["total_score"])

        for inv in CATALOG:
            units_tracker[inv.id].append(result.allocation.get(inv.id, 0))

    scores_arr = np.array(scores)
    ci_lower   = float(np.percentile(scores_arr, 2.5))
    ci_upper   = float(np.percentile(scores_arr, 97.5))

    selection_freq = {
        iid: round(float(np.mean(np.array(vals) > 0)), 4)
        for iid, vals in units_tracker.items()
    }
    units_mean = {
        iid: round(float(np.mean(vals)), 4)
        for iid, vals in units_tracker.items()
    }
    units_std = {
        iid: round(float(np.std(vals)), 4)
        for iid, vals in units_tracker.items()
    }

    return {
        "nominal":        nominal_summary,
        "score_mean":     round(float(scores_arr.mean()), 6),
        "score_std":      round(float(scores_arr.std()), 6),
        "score_min":      round(float(scores_arr.min()), 6),
        "score_max":      round(float(scores_arr.max()), 6),
        "score_ci_95":    [round(ci_lower, 6), round(ci_upper, 6)],
        "selection_freq": selection_freq,
        "units_mean":     units_mean,
        "units_std":      units_std,
        "n_optimal":      n_optimal,
        "n_samples":      n_samples,
    }


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ILP sensitivity analysis")
    parser.add_argument("--fire",       type=float, default=0.72)
    parser.add_argument("--drought",    type=float, default=0.58)
    parser.add_argument("--vegetation", type=float, default=0.45)
    parser.add_argument("--budget",     type=float, default=10_000.0)
    parser.add_argument("--n",          type=int,   default=N_SAMPLES)
    parser.add_argument("--perturb",    type=float, default=PERTURB_PCT)
    parser.add_argument("--seed",       type=int,   default=RNG_SEED)
    parser.add_argument("--out",        type=str,   default=None)
    args = parser.parse_args()

    probs       = {"fire": args.fire, "drought": args.drought, "vegetation": args.vegetation}
    constraints = ILPConstraints(budget=args.budget)

    print(f"Running {args.n}-sample sensitivity analysis  (±{args.perturb*100:.0f}% perturbation)…")
    report = run_sensitivity(probs, constraints, args.n, args.perturb, args.seed)

    print(f"\nNominal total_score : {report['nominal']['total_score']:.6f}")
    print(f"Perturbed score     : {report['score_mean']:.6f} ± {report['score_std']:.6f}")
    print(f"95 % CI             : [{report['score_ci_95'][0]:.6f}, {report['score_ci_95'][1]:.6f}]")
    print(f"Optimal solves      : {report['n_optimal']} / {report['n_samples']}")
    print("\nSelection frequency (fraction of samples where units > 0):")
    for iid, freq in sorted(report["selection_freq"].items(), key=lambda x: -x[1]):
        mean_u = report["units_mean"][iid]
        std_u  = report["units_std"][iid]
        print(f"  {iid:<20}  {freq:.2f}   mean units {mean_u:.2f} ± {std_u:.2f}")

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved → {out_path}")