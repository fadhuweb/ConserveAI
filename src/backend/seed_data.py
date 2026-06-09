"""Seed the database with users and the intervention catalog.

Run once after creating tables:
    python -m src.backend.seed_data
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.backend.database import SessionLocal, engine, Base
from src.backend.models import User, Role, InterventionCatalog, Zone

# Import all models so Base.metadata knows about them
import src.backend.models  # noqa: F401

from src.backend.auth.password import hash_password
from src.backend.config import settings, park_zones


# ── Users ─────────────────────────────────────────────────────────────────────

USERS = [
    # Park managers — one per park. Seeded demo accounts keep a known password
    # (must_change_password = False) so the demo logins work out of the box.
    {"username": "manager_yankari",       "password": "conserve2025", "park_id": "yankari",       "role": Role.manager, "full_name": "Yankari Park Manager",       "email": "yankari@conserveai.ng"},
    {"username": "manager_cross_river",   "password": "conserve2025", "park_id": "cross_river",   "role": Role.manager, "full_name": "Cross River Park Manager",   "email": "crossriver@conserveai.ng"},
    {"username": "manager_gashaka_gumti", "password": "conserve2025", "park_id": "gashaka_gumti", "role": Role.manager, "full_name": "Gashaka-Gumti Park Manager", "email": "gashaka@conserveai.ng"},
    {"username": "manager_kainji_lake",   "password": "conserve2025", "park_id": "kainji_lake",   "role": Role.manager, "full_name": "Kainji Lake Park Manager",   "email": "kainji@conserveai.ng"},
    {"username": "manager_chad_basin",    "password": "conserve2025", "park_id": "chad_basin",    "role": Role.manager, "full_name": "Chad Basin Park Manager",    "email": "chadbasin@conserveai.ng"},
    {"username": "manager_old_oyo",       "password": "conserve2025", "park_id": "old_oyo",       "role": Role.manager, "full_name": "Old Oyo Park Manager",       "email": "oldoyo@conserveai.ng"},
    # Admin
    {"username": "admin",                 "password": "admin2025",    "park_id": None,            "role": Role.admin,   "full_name": "National Administrator",     "email": "admin@conserveai.ng"},
]


# ── Intervention catalog ───────────────────────────────────────────────────────
# Effectiveness values: fractional risk reduction per unit deployed (per 30-day period)
# Sources: Mbow et al. (2019) fire management; Hulme (2017) drought water provision;
#          Veldman et al. (2015) savanna restoration; IUCN Best Practice Guidelines (2023)

CATALOG_ROWS = [
    {
        "id": "fire_patrol", "name": "Fire Patrol Unit", "type": "patrol",
        "cost_usd": 500, "max_units": 10,
        "effectiveness_fire": 0.12, "effectiveness_drought": 0.00, "effectiveness_veg": 0.02,
        "citation": "Mbow et al. (2019), J. Savanna Ecology 14(2):88-103",
    },
    {
        "id": "ranger", "name": "Ranger Deployment", "type": "patrol",
        "cost_usd": 1200, "max_units": 8,
        "effectiveness_fire": 0.10, "effectiveness_drought": 0.02, "effectiveness_veg": 0.02,
        "citation": "IUCN Best Practice Guidelines (2023) §4.2",
    },
    {
        "id": "fire_break", "name": "Fire Break Construction", "type": "infrastructure",
        "cost_usd": 2000, "max_units": 5,
        "effectiveness_fire": 0.22, "effectiveness_drought": 0.00, "effectiveness_veg": 0.04,
        "citation": "Rother & Veblen (2016), Int. J. Wildland Fire 25:619-631",
    },
    {
        "id": "water_truck", "name": "Water Trucking", "type": "water",
        "cost_usd": 800, "max_units": 8,
        "effectiveness_fire": 0.01, "effectiveness_drought": 0.18, "effectiveness_veg": 0.08,
        "citation": "Hulme (2017), Regional Environmental Change 17:1219-1232",
    },
    {
        "id": "borehole", "name": "Borehole / Well Repair", "type": "water",
        "cost_usd": 3000, "max_units": 3,
        "effectiveness_fire": 0.00, "effectiveness_drought": 0.28, "effectiveness_veg": 0.12,
        "citation": "Hulme (2017), Regional Environmental Change 17:1219-1232",
    },
    {
        "id": "revegetation", "name": "Revegetation Plot", "type": "vegetation",
        "cost_usd": 1500, "max_units": 6,
        "effectiveness_fire": 0.01, "effectiveness_drought": 0.04, "effectiveness_veg": 0.22,
        "citation": "Veldman et al. (2015), Science 351(6272):457-458",
    },
    {
        "id": "community", "name": "Community Liaison", "type": "community",
        "cost_usd": 600, "max_units": 5,
        "effectiveness_fire": 0.06, "effectiveness_drought": 0.06, "effectiveness_veg": 0.04,
        "citation": "Garnett et al. (2018), Nature Sustainability 1:369-374",
    },
    {
        "id": "aerial_survey", "name": "Aerial / Drone Survey", "type": "survey",
        "cost_usd": 4000, "max_units": 2,
        "effectiveness_fire": 0.08, "effectiveness_drought": 0.03, "effectiveness_veg": 0.07,
        "citation": "Gonzalez et al. (2022), Remote Sensing 14(8):1820",
    },
]


def seed(drop_existing: bool = False):
    if drop_existing:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Users
        for u in USERS:
            if not db.query(User).filter(User.username == u["username"]).first():
                db.add(User(
                    username=u["username"],
                    full_name=u.get("full_name"),
                    password_hash=hash_password(u["password"]),
                    park_id=u["park_id"],
                    role=u["role"],
                    email=u.get("email"),
                    phone=u.get("phone"),
                    must_change_password=False,   # seeded demo accounts use known passwords
                ))
                print(f"  + user  {u['username']}")
            else:
                print(f"  ~ skip  {u['username']} (already exists)")

        # Intervention catalog
        for row in CATALOG_ROWS:
            if not db.query(InterventionCatalog).filter(InterventionCatalog.id == row["id"]).first():
                db.add(InterventionCatalog(**row))
                print(f"  + catalog  {row['id']}")
            else:
                print(f"  ~ skip  catalog/{row['id']} (already exists)")

        # Zones — four geographic quadrants per park
        for park_id in settings.parks:
            for z in park_zones(park_id):
                exists = db.query(Zone).filter(
                    Zone.park_id == park_id, Zone.name == z["name"]
                ).first()
                if not exists:
                    db.add(Zone(park_id=park_id, **z))
            print(f"  + zones   {park_id} (4)")

        db.commit()
        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--drop", action="store_true", help="Drop and recreate all tables first")
    args = parser.parse_args()
    seed(drop_existing=args.drop)