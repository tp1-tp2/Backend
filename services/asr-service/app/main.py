import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import asdict

logging.basicConfig(level=logging.INFO)
logging.getLogger("app").setLevel(logging.DEBUG)
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.routes import internal_router, streaming_router
from app.core.config import settings
from app.services import whisper_service
from app.services.device_manager import manager as device_manager
from app.services.inference_scheduler import scheduler
from app.services.job_worker import worker as job_worker

logger = logging.getLogger(__name__)


def _initial_batch_size() -> int:
    if settings.force_batch_size:
        return settings.force_batch_size
    if whisper_service.get_current_device() == "cuda":
        return settings.batch_size_gpu
    return settings.batch_size_cpu


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, whisper_service.load_model)
    except Exception as exc:
        logger.error("Whisper model failed to load: %s", exc)
    whisper_service.init_http()
    scheduler.max_batch_size = _initial_batch_size()
    await scheduler.start()
    await device_manager.start()
    await job_worker.start()
    yield
    await job_worker.stop()
    await device_manager.stop()
    await scheduler.stop()
    await whisper_service.close_http()


app = FastAPI(title="ASR Platform - ASR Service", version=settings.version, lifespan=lifespan)

app.include_router(internal_router)
app.include_router(streaming_router)


@app.get("/health")
async def health_check():
    """Liveness: the process is up. Never depends on load, so an overloaded
    replica is not restarted for being busy (that is what /ready is for)."""
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


@app.get("/ready")
async def readiness_check():
    """Readiness: take this replica out of the load balancer while the model
    is not loaded or its inference queue is saturated, so new synchronous
    traffic goes to a sibling replica instead of being rejected here."""
    loaded = whisper_service.is_loaded()
    saturated = (
        scheduler.depth >= settings.max_queue_depth
        or scheduler.estimated_wait_s() > settings.admission_max_wait_seconds
    )
    ready = loaded and not saturated
    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "ready": ready,
            "checks": {
                "model_loaded": loaded,
                "queue_depth": scheduler.depth,
                "estimated_wait_s": round(scheduler.estimated_wait_s(), 3),
                "saturated": saturated,
            },
        },
    )


@app.get("/status/scheduler")
async def scheduler_status():
    """Evidence endpoint for E4/E8: queue depth, batching histogram, admission
    rejections, shed partials, job-worker counters."""
    return {
        "device": whisper_service.get_current_device(),
        "compute_type": whisper_service.get_current_compute_type(),
        "scheduler": scheduler.snapshot(),
        "job_worker": job_worker.snapshot(),
    }


@app.get("/status/adaptation")
async def adaptation_status():
    """Evidence endpoint for E9 (C2.3): current device/precision/batch size,
    the hardware+load snapshot behind that choice, and the recent adaptation
    decision history — so the runtime-adaptation mechanism is externally
    verifiable, not just trusted to exist in the code.
    """
    snapshot = device_manager.last_snapshot
    return {
        "adaptive_mode": settings.adaptive_mode,
        "forced": {
            "device": settings.force_device,
            "compute_type": settings.force_compute_type,
            "batch_size": settings.force_batch_size,
        },
        "current": {
            "device": whisper_service.get_current_device(),
            "compute_type": whisper_service.get_current_compute_type(),
            "batch_size": scheduler.max_batch_size,
        },
        "in_flight_inferences": device_manager.in_flight,
        "queue_depth": scheduler.depth,
        "rejected_states": device_manager.rejected_states,
        "model_s_per_clip_by_state": scheduler.snapshot()["model_s_per_clip_by_state"],
        "last_hardware_snapshot": asdict(snapshot) if snapshot else None,
        "recent_decisions": [asdict(d) for d in device_manager.history],
    }
