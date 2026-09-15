import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import asdict

logging.basicConfig(level=logging.INFO)
logging.getLogger("app").setLevel(logging.DEBUG)
from datetime import datetime, timezone

from fastapi import FastAPI

from app.api.routes import internal_router, streaming_router
from app.core.config import settings
from app.services import whisper_service
from app.services.device_manager import manager as device_manager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, whisper_service.load_model)
    except Exception as exc:
        logger.error("Whisper model failed to load: %s", exc)
    await device_manager.start()
    yield
    await device_manager.stop()


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
        "checks": {
            "whisper_model": "loaded" if whisper_service.is_loaded() else "not_loaded",
            "device": whisper_service.get_current_device(),
            "compute_type": whisper_service.get_current_compute_type(),
        },
    }


@app.get("/status/adaptation")
async def adaptation_status():
    """Evidence endpoint for E2/E3: current device/precision, the hardware
    snapshot behind that choice, and the recent adaptation decision history —
    so the runtime-adaptation mechanism is externally verifiable, not just
    trusted to exist in the code.
    """
    snapshot = device_manager.last_snapshot
    return {
        "adaptive_mode": settings.adaptive_mode,
        "forced": {
            "device": settings.force_device,
            "compute_type": settings.force_compute_type,
        },
        "current": {
            "device": whisper_service.get_current_device(),
            "compute_type": whisper_service.get_current_compute_type(),
        },
        "in_flight_inferences": device_manager.in_flight,
        "last_hardware_snapshot": asdict(snapshot) if snapshot else None,
        "recent_decisions": [asdict(d) for d in device_manager.history],
    }
