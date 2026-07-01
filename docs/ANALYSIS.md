# Analysis, discussion, and recommendations

This document analyses the results against the project proposal objectives, discusses
what the milestones mean, and gives recommendations and future work.

## Results against the proposal objectives

### Forecasting
The proposal set out to forecast three threats over a 30-day window for six parks:
fire, drought, and vegetation degradation. The project met this objective. The
deployed model produces daily forecasts for all six parks. On a held-out 2024 to
2025 test set the model scored an F2 of 0.94 for fire, 0.89 for drought, and 0.75
for vegetation. The fire and drought results are strong. Vegetation is weaker, which
the discussion examines. Measured against a persistence baseline, the naive forecast
that the next 30 days resemble the last 30, the model wins on every threat, and by a
wide margin on drought (F2 0.89 versus 0.40) and fire (0.94 versus 0.78). It is
therefore learning real structure rather than repeating recent history.

The proposal also called for a comparison of eight model configurations: Random
Forest, XGBoost, LSTM, and Transformer, each in a supervised and a semi-supervised
form. The project trained and evaluated all eight. A self-training Random Forest
performed best and runs in production. The evaluation used the planned metrics:
precision, recall, F2, ROC-AUC, Brier score, lead time, a persistence baseline, and
bootstrap confidence intervals.

### Recommender
The proposal called for a budget-constrained recommender built with integer linear
programming, allocating interventions across four zones per park. The project met
this objective. The optimiser respects the budget and the per-intervention capacity
in every test, scales its plan up as the budget grows, and allocates units to zones.
The live system solves a plan in under 60 milliseconds.

The optimiser maximises threat reduction, not budget spend. Its objective is to
maximise, across all interventions, the number of units times the sum over threats of
threat probability times per-unit effectiveness, subject to five constraints: a total
budget ceiling, each intervention's catalog capacity, on and off toggles per
intervention type, an optional cap on units per type, and urgency floors that force a
minimum spend on any threat whose probability is high (40 percent of budget at a
probability of 0.85 or more, 25 percent at 0.70, and 10 percent at 0.50). Because the
objective rewards risk reduction and the budget is only a ceiling, the plan favours
threat minimisation over cost utilisation. It buys the interventions with the highest
probability-weighted effectiveness per dollar first and stops once further units add
no reduction or hit a capacity cap. This shows in the budget runs: a 5,000 dollar
budget spends only 4,800, because the most cost-effective units are cheap and quickly
capped, while a 50,000 dollar budget spends the full amount, because the caps still
leave useful units to buy. The urgency floors are the one place cost efficiency gives
way to prioritisation. They push money toward an urgent threat even when a cheaper
intervention for another threat would score marginally higher, so the plan cannot
ignore a severe threat simply because addressing it is expensive.

The interventions the plan selects follow the risk profile through the catalog. When
fire risk dominates, it leans on the Fire Patrol Unit (500 dollars, 0.12 fire
reduction per unit), which has the best fire reduction per dollar, then adds Fire Break
Construction (2,000 dollars, 0.22 per unit) for depth. When drought dominates, as at
Chad Basin where drought risk is near-certain, the urgency floor forces spend onto
water interventions: the plan buys Waterhole Maintenance (800 dollars, 0.18 drought
reduction) first for cost efficiency and adds Borehole or Well Repair (3,000 dollars,
0.28) when the budget allows a deeper cut. Vegetation risk pulls in the Revegetation
Plot (1,500 dollars, 0.22 vegetation reduction), the only strong single-threat
vegetation tool. Community Liaison and Ranger Deployment, which spread modest
effectiveness across all three threats, act as fill, added when a threat is moderate
rather than severe or when budget remains after the specialised tools reach their caps.
When several threats are severe at once, the urgency floors scale down proportionally
so the plan stays within budget while still addressing each threat, producing a
balanced allocation rather than a single-threat one.

### Web application and deployment
The proposal called for a React and FastAPI web application with role-based access
and a free-tier deployment. The project met this objective. The application is
deployed on Vercel, Fly.io, and Neon, with a daily GitHub Actions cron that keeps
the data current. Login, park-scoping, the national overview, the park dashboard,
the recommender, and manager provisioning all work on the live site.

### Objectives the project missed or only partly met
The drought and vegetation labels come from climate thresholds, not from the
independent news sources described in the proposal. This is a label-leakage
limitation. The drought and vegetation evaluation therefore measures consistency
with the data the labels came from in part, rather than against a fully independent
ground truth.

Vegetation forecasting is the weakest part of the system, and a live observation
sharpened why. Vegetation risk is driven by NDVI, an optical satellite index, and two
problems compound. First, the model was trained on Sentinel-2 NDVI, but the live
pipeline reads NDVI from MODIS, a different sensor, so inference sees a source the
model did not learn on. Second, optical NDVI is blocked by cloud, and during the
rainy season the daily source is unavailable for most parks, so the vegetation input
falls back to an imputed value. When that happens the vegetation forecast collapses to
a near-constant output: on 30 June 2026, five of the six parks returned an identical
vegetation probability of 0.53, and only the arid Sahel park, Chad Basin, which keeps
clear-sky NDVI, differed. The vegetation figures should therefore be read with low
confidence during cloudy periods.

The threat set follows what free satellite and climate data can measure. It does not
cover the threats the proposal itself identifies as central to Nigerian parks, such
as poaching, grazing encroachment, and insecurity in the north-east, because none of
these are observable from the open climate and satellite sources the model relies on.
The intervention
cost and effectiveness values are literature-informed estimates rather than figures
measured in these parks. The system does not yet log actual deployments, so the
per-plan capacity cap is not tracked across a real 30-day period.

## Discussion

The milestones matter because they connect three steps that are usually kept apart.
The system turns open satellite and climate data into a forecast, then turns that
forecast into a budget-constrained plan, then explains both. Most conservation
machine-learning work stops at a risk map. This project goes from the map to the
allocation and to the reasons behind it.

The results show that open data can drive a usable decision-support tool for a
resource-constrained setting. The fire and drought forecasts are accurate enough to
be informative. The recommender produces plans a manager could act on, within a
stated budget and down to the zone. The live deployment shows the pipeline runs
without manual steps once it is set up.

The impact is methodological rather than operational. The project demonstrates an
approach. It does not yet prove a field outcome. The label-leakage and parameter
limitations mean the numbers should be read as evidence for the method, not as a
validated claim about real conservation gains.

## Recommendations and future work

For the conservation community, the system suits early triage and planning support,
not final decisions. A manager should treat a recommendation as a starting point and
apply local knowledge, especially for the threats the model does not cover.

Future work follows from the limitations.

- Move vegetation onto a cloud-robust NDVI source and align training with serving.
  Replace the daily optical NDVI with a cloud-composited product (the 16-day MODIS
  MOD13Q1, which keeps the best clear pixel per window) as the primary signal, and add
  Sentinel-1 radar, which sees through cloud, as a backup for days optical fails.
  Rebuild the training data on the same source the live system serves so the model no
  longer faces a sensor mismatch, then retrain and re-validate. Impute any remaining
  gaps with each park's seasonal NDVI baseline rather than a global default, and mark
  the vegetation forecast low-confidence when coverage is poor.
- Replace the climate-derived drought and vegetation labels with independent ground
  truth to remove the label leakage.
- Add deployment logging so the system tracks actual unit use against the 30-day
  capacity and can learn from outcomes.
- Forecast at the zone level rather than the park level.
- Make the optimiser intervention-aware, so a planned action feeds into the next
  forecast.
- Replace the linear effectiveness assumption with a model that captures diminishing
  returns.
- Extend planning across several 30-day periods rather than one.
- Widen the threat set toward the threats that dominate Nigerian parks, using sources
  such as ranger patrol records for poaching and grazing.
