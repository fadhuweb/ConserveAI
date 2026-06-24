"""FastAPI application entry point.

Start locally:
    uvicorn src.backend.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.backend.config import settings
from src.backend.routes.auth import router as auth_router
from src.backend.routes.forecasts import router as forecasts_router
from src.backend.routes.recommendations import router as recommendations_router
from src.backend.routes.jobs import router as jobs_router
from src.backend.jobs.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # In production the external GitHub Actions cron triggers POST /jobs/run-daily-forecast
    # instead of the in-process scheduler (which can't fire on a scaled-to-zero container).
    if settings.environment != "production":
        start_scheduler()
    logger.info("ConserveAI backend starting  (env=%s)", settings.environment)
    yield
    if settings.environment != "production":
        stop_scheduler()
    logger.info("ConserveAI backend shut down.")


tags_metadata = [
    {"name": "auth", "description": "Login / logout. Login returns a JWT in an httpOnly cookie used by all other endpoints."},
    {"name": "forecasts", "description": "Park metadata, zones, the intervention catalog, and daily 30-day threat forecasts (park-scoped)."},
    {"name": "recommendations", "description": "Budget-constrained ILP intervention recommender with zone-level allocation and sensitivity analysis."},
    {"name": "system", "description": "Health check."},
]

app = FastAPI(
    title="ConserveAI API",
    description=(
        "Multi-threat probabilistic forecasting and budget-constrained intervention "
        "recommendation for six Nigerian national parks.\n\n"
        "**How to try this API**\n"
        "1. Call `POST /auth/login` with a demo account below — the JWT is stored as an httpOnly cookie automatically.\n"
        "2. Then call any forecast or recommendation endpoint.\n\n"
        "**Demo accounts**\n"
        "| Username | Password | Role | Scope |\n"
        "|----------|----------|------|-------|\n"
        "| `manager_yankari` | `conserve2025` | manager | Yankari only |\n"
        "| `admin` | `admin2025` | admin | all parks + national overview |\n\n"
        "Other park managers follow the pattern `manager_<park>` "
        "(cross_river, gashaka_gumti, kainji_lake, chad_basin, old_oyo)."
    ),
    version="1.0.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)

# Allow local dev origins plus the deployed frontend (FRONTEND_URL → the Vercel app).
_cors_origins = ["http://localhost:3000", "http://localhost:5173"]
if settings.frontend_url and settings.frontend_url not in _cors_origins:
    _cors_origins.append(settings.frontend_url.rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(forecasts_router)
app.include_router(recommendations_router)
app.include_router(jobs_router)


@app.get("/health", tags=["system"], summary="Service + database health check")
def health():
    from src.backend.database import SessionLocal
    db = SessionLocal()
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "unreachable"
    finally:
        db.close()
    return {"status": "ok" if db_status == "ok" else "degraded",
            "database": db_status,
            "version": "1.0.0"}