from app.api.routes.auth import router as auth_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.streaming import router as streaming_router
from app.api.routes.transcriptions import router as transcriptions_router
from app.api.routes.users import router as users_router

__all__ = [
    "auth_router",
    "users_router",
    "dashboard_router",
    "transcriptions_router",
    "streaming_router",
    "jobs_router",
]
