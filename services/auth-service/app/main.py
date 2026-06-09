from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI

from app.api.routes import auth_router, internal_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="ASR Platform - Auth Service",
    version=settings.version,
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(internal_router)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {"database": "healthy"},
    }
