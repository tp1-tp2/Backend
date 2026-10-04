"""Asynchronous transcription API (scalability, docs/09-arquitectura-v2.md).

POST /api/v1/jobs   -> 202 Accepted + job_id. audio-processor validates and
                       converts the file, then enqueues it on a Redis Stream;
                       ASR workers consume it at the rate the hardware allows.
GET  /api/v1/jobs/{id} -> job status/result, read straight from the job store
                       (Redis) by the gateway — a CQRS-style read path, so
                       high-frequency polling never touches audio-processor
                       or asr-service.

The synchronous POST /api/v1/transcribe is kept unchanged so E3 stays
comparable and the existing frontend keeps working.
"""
import httpx
from fastapi import APIRouter, Depends, File, UploadFile

from app.api.dependencies import get_current_user, get_http_client
from app.api.routes.transcriptions import _fwd
from app.core.config import settings
from app.core.exceptions import (
    AuthorizationError,
    GatewayTimeoutError,
    ServiceUnavailableError,
    UpstreamOverloadedError,
)
from app.core.redis_client import get_redis
from fastapi import HTTPException

router = APIRouter(tags=["jobs"])

JOB_KEY_PREFIX = "job:"  # must match audio-processor/asr-service job_store


@router.post("/api/v1/jobs", status_code=202)
async def submit_job(
    file: UploadFile = File(...),
    http: httpx.AsyncClient = Depends(get_http_client),
    user: dict = Depends(get_current_user),
):
    try:
        content = await file.read()
        resp = await http.post(
            f"{settings.audio_processor_url}/internal/audio/jobs",
            files={"file": (file.filename, content, file.content_type)},
            data={"user_id": user["user_id"]},
            timeout=settings.request_timeout,
        )
        return _fwd(resp)
    except httpx.TimeoutException as exc:
        raise GatewayTimeoutError() from exc
    except httpx.ConnectError as exc:
        raise ServiceUnavailableError("audio-processor") from exc


@router.get("/api/v1/jobs/{job_id}")
async def get_job(job_id: str, user: dict = Depends(get_current_user)):
    store = get_redis()
    if store is None:
        raise ServiceUnavailableError("job-store")
    try:
        job = await store.hgetall(JOB_KEY_PREFIX + job_id)
    except Exception as exc:
        raise UpstreamOverloadedError("job-store") from exc
    if not job:
        raise HTTPException(
            status_code=404, detail={"errorCode": "JOB_001", "message": "Job not found"}
        )
    if job.get("user_id") != user["user_id"]:
        raise AuthorizationError()
    job.pop("user_id", None)
    return {"job_id": job_id, **job}
