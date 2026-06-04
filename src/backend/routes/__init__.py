from src.backend.routes.auth import router as auth_router
from src.backend.routes.forecasts import router as forecasts_router
from src.backend.routes.recommendations import router as recommendations_router

__all__ = ["auth_router", "forecasts_router", "recommendations_router"]