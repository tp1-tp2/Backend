import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api.routes import (
    auth_router,
    dashboard_router,
    jobs_router,
    streaming_router,
    transcriptions_router,
    users_router,
)
from app.api.dependencies import build_http_client
from app.core import edge_admission
from app.core.redis_client import close_redis, get_redis
from app.core.config import settings
from app.core.response import error_response


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = build_http_client()
    yield
    await app.state.http.aclose()
    await close_redis()


app = FastAPI(
    title="ASR Platform - API Gateway",
    version=settings.version,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def edge_admission_middleware(request: Request, call_next):
    """Reject excess synchronous transcriptions at the edge, before the upload
    is read or forwarded (docs/16, E4 v2 finding)."""
    if request.method != "POST" or request.url.path != "/api/v1/transcribe" or not edge_admission.enabled():
        return await call_next(request)
    admitted, slot = await edge_admission.try_acquire()
    if not admitted:
        return error_response(
            "SYSTEM_003", "Transcription capacity reached, retry later", 503,
            headers={"Retry-After": str(settings.retry_after_seconds)},
        )
    try:
        return await call_next(request)
    finally:
        # Shielded: if the client disconnects, this task is cancelled and an
        # unshielded await here would be cancelled too, leaking the slot until
        # it goes stale (E4 v2: leaked slots throttled the next run's start).
        await asyncio.shield(edge_admission.release(slot))


app.include_router(auth_router)
app.include_router(users_router)
app.include_router(dashboard_router)
app.include_router(transcriptions_router)
app.include_router(streaming_router)
app.include_router(jobs_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    from fastapi import HTTPException

    if isinstance(exc, HTTPException):
        detail = exc.detail
        if isinstance(detail, dict):
            return error_response(
                error_code=detail.get("errorCode", "SYSTEM_001"),
                message=detail.get("message", str(exc)),
                status_code=exc.status_code,
                headers=exc.headers,
            )
        return error_response("SYSTEM_001", str(detail), exc.status_code, headers=exc.headers)

    return error_response("SYSTEM_001", "An unexpected error occurred", 500)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )
    schema.setdefault("components", {}).setdefault("securitySchemes", {})["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi  # type: ignore[method-assign]


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.service_name,
        "version": settings.version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {"dependencies": "healthy", "auth_mode": settings.auth_mode},
    }


@app.get("/ready")
async def readiness_check():
    """Readiness (vs. liveness /health): the gateway can serve traffic only if
    its own critical dependencies for the configured auth mode are reachable.
    In local auth mode with fail-open revocation, Redis being down does NOT
    make the gateway unready — that is the point of the design.
    """
    checks = {"auth_mode": settings.auth_mode}
    ready = True
    if settings.auth_mode == "local" and settings.redis_url:
        try:
            await get_redis().ping()
            checks["revocation_store"] = "up"
        except Exception:
            checks["revocation_store"] = "down"
            ready = settings.revocation_fail_open
    status_code = 200 if ready else 503
    return JSONResponse(status_code=status_code, content={"ready": ready, "checks": checks})
