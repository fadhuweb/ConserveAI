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
from src.backend.jobs.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    logger.info("ConserveAI backend starting  (env=%s)", settings.environment)
    yield
    stop_scheduler()
    logger.info("ConserveAI backend shut down.")


app = FastAPI(
    title="ConserveAI API",
    description="Wildlife threat forecasting and intervention recommendation for Nigerian national parks.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(forecasts_router)
app.include_router(recommendations_router)


@app.get("/health")
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