from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI

from app.api.routes import internal_router
import httpx

from app.core.config import settings
from app.services import job_queue


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient(
        timeout=30.0, limits=httpx.Limits(max_connections=200, max_keepalive_connections=50)
    )
    yield
    await app.state.http.aclose()
    await job_queue.close()


app = FastAPI(title="ASR Platform - Audio Processor", version=settings.version, lifespan=lifespan)

app.include_router(internal_router)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {"database": "healthy", "ffmpeg": "healthy"},
    }
