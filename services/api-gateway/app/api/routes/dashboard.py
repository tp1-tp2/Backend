import asyncio
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.dependencies import get_current_user, get_http_client
from app.core.config import settings

router = APIRouter(tags=["dashboard"])

_DASHBOARD_TIMEOUT = 0.5  # 500 ms


async def _safe_get(http: httpx.AsyncClient, url: str, **kwargs) -> dict | None:
    try:
        resp = await asyncio.wait_for(
            http.get(url, **kwargs), timeout=_DASHBOARD_TIMEOUT
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


async def _health(http: httpx.AsyncClient, url: str) -> str:
    try:
        resp = await asyncio.wait_for(http.get(f"{url}/health"), timeout=_DASHBOARD_TIMEOUT)
        if resp.status_code == 200:
            return resp.json().get("status", "unknown")
    except Exception:
        pass
    return "unavailable"


@router.get("/api/v1/dashboard")
async def dashboard(
    http: httpx.AsyncClient = Depends(get_http_client),
    user: dict = Depends(get_current_user),
):
    user_id = user["user_id"]

    profile_task = asyncio.create_task(
        _safe_get(http, f"{settings.user_service_url}/internal/users/{user_id}")
    )
    summary_task = asyncio.create_task(
        _safe_get(
            http,
            f"{settings.transcription_manager_url}/internal/transcriptions/summary",
            headers={"X-User-Id": user_id},
        )
    )
    auth_health_task = asyncio.create_task(_health(http, settings.auth_service_url))
    audio_health_task = asyncio.create_task(_health(http, settings.audio_processor_url))
    asr_health_task = asyncio.create_task(_health(http, settings.asr_service_url))
    trans_health_task = asyncio.create_task(_health(http, settings.transcription_manager_url))

    (
        profile,
        summary,
        auth_health,
        audio_health,
        asr_health,
        trans_health,
    ) = await asyncio.gather(
        profile_task,
        summary_task,
        auth_health_task,
        audio_health_task,
        asr_health_task,
        trans_health_task,
    )

    return JSONResponse(
        content={
            "status": "success",
            "data": {
                "user": profile or {"user_id": user_id, "email": user["email"]},
                "transcription_summary": summary or {"total": 0, "latest_at": None},
                "services": {
                    "auth": auth_health,
                    "audio-processor": audio_health,
                    "asr": asr_health,
                    "transcription-manager": trans_health,
                },
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
