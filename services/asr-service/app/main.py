import asyncio
import logging
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logging.getLogger("app").setLevel(logging.DEBUG)
from datetime import datetime, timezone

from fastapi import FastAPI

from app.api.routes import internal_router, streaming_router
from app.core.config import settings
from app.services import whisper_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, whisper_service.load_model)
    except Exception as exc:
        logger.error("Whisper model failed to load: %s", exc)
    yield


app = FastAPI(title="ASR Platform - ASR Service", version=settings.version, lifespan=lifespan)

app.include_router(internal_router)
app.include_router(streaming_router)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {"whisper_model": "loaded" if whisper_service.is_loaded() else "not_loaded"},
    }
