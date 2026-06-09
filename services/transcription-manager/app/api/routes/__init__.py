from app.api.routes.internal import router as internal_router
from app.api.routes.transcriptions import router as transcriptions_router

__all__ = ["transcriptions_router", "internal_router"]
