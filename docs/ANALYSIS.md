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
the discussion examines.

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

Vegetation forecasting reached only moderate accuracy. The model separates
vegetation risk across parks, but the signal moves little within a park over a short
window.

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
