import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI

from app.api.routes import auth_router, transcriptions_router
from app.core.config import settings
from app.services import whisper_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, whisper_service.load_model)
    except Exception as exc:
        logger.error("Whisper model failed to load: %s", exc)
    yield
    # No adaptation monitor to stop — device is fixed for the process lifetime.


app = FastAPI(
    title="ASR Platform - Monolithic Baseline (E3 control)",
    version=settings.version,
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(transcriptions_router)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "whisper_model": "loaded" if whisper_service.is_loaded() else "not_loaded",
            "device": settings.device,
            "adaptive": False,
        },
    }
