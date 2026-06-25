"""Intervention catalog for Nigerian national park conservation management.

Each intervention is deployable per 30-day period per park zone.
Costs are in USD. Effectiveness values are the expected fractional reduction
in risk probability per unit deployed; they are additive and capped at 1.0
in post-processing (a park cannot have more than 100% of a threat removed).

Calibration: fully deploying the catalog within a $15,000 budget can
realistically reduce fire risk by ~80%, drought risk by ~55%, and
vegetation degradation risk by ~45% — consistent with the conservation
management literature for sub-Saharan savanna ecosystems.
"""

from dataclasses import dataclass
from typing import Dict

THREAT_KEYS = ["fire", "drought", "vegetation"]

INTERVENTION_TYPES = [
    "patrol", "infrastructure", "water", "vegetation", "community", "survey"
]


@dataclass(frozen=True)
class Intervention:
    id:            str
    name:          str
    type:          str
    cost:          float          # USD per unit per 30-day period
    max_units:     int            # catalog capacity limit
    effectiveness: Dict[str, float]  # {threat: fractional reduction per unit}


CATALOG: list[Intervention] = [
    Intervention(
        id="fire_patrol",
        name="Fire Patrol Unit",
        type="patrol",
        cost=500,
        max_units=10,
        effectiveness={"fire": 0.12, "drought": 0.00, "vegetation": 0.02},
    ),
    Intervention(
        id="ranger",
        name="Ranger Deployment",
        type="patrol",
        cost=1_200,
        max_units=8,
        effectiveness={"fire": 0.10, "drought": 0.02, "vegetation": 0.02},
    ),
    Intervention(
        id="fire_break",
        name="Fire Break Construction",
        type="infrastructure",
        cost=2_000,
        max_units=5,
        effectiveness={"fire": 0.22, "drought": 0.00, "vegetation": 0.04},
    ),
    Intervention(
        id="water_truck",
        name="Waterhole Maintenance",
        type="water",
        cost=800,
        max_units=8,
        effectiveness={"fire": 0.01, "drought": 0.18, "vegetation": 0.08},
    ),
    Intervention(
        id="borehole",
        name="Borehole / Well Repair",
        type="water",
        cost=3_000,
        max_units=3,
        effectiveness={"fire": 0.00, "drought": 0.28, "vegetation": 0.12},
    ),
    Intervention(
        id="revegetation",
        name="Revegetation Plot",
        type="vegetation",
        cost=1_500,
        max_units=6,
        effectiveness={"fire": 0.01, "drought": 0.04, "vegetation": 0.22},
    ),
    Intervention(
        id="community",
        name="Community Liaison",
        type="community",
        cost=600,
        max_units=5,
        effectiveness={"fire": 0.06, "drought": 0.06, "vegetation": 0.04},
    ),
    Intervention(
        id="aerial_survey",
        name="Aerial / Drone Survey",
        type="survey",
        cost=4_000,
        max_units=2,
        effectiveness={"fire": 0.08, "drought": 0.03, "vegetation": 0.07},
    ),
]

CATALOG_BY_ID: dict[str, Intervention] = {inv.id: inv for inv in CATALOG}
