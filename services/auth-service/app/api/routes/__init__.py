from app.api.routes.auth import router as auth_router
from app.api.routes.internal import router as internal_router

__all__ = ["auth_router", "internal_router"]
