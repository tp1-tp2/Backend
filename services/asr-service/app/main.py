from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI

from app.core.config import settings

_model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Model loading happens in task 6.1
    # import whisper
    # global _model
    # _model = whisper.load_model(settings.whisper_model, device=settings.device)
    yield
    _model = None


app = FastAPI(title="ASR Platform - ASR Service", version=settings.version, lifespan=lifespan)


@app.get("/health")
async def health_check():
    model_status = "loaded" if _model is not None else "not_loaded"
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {"whisper_model": model_status},
    }
