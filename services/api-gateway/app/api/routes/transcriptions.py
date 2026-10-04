import httpx
from fastapi import APIRouter, Body, Depends, File, Query, Request, UploadFile
from fastapi.responses import Response, StreamingResponse

from app.api.dependencies import get_current_user, get_http_client
from app.core.config import settings
from app.core.exceptions import GatewayTimeoutError, ServiceUnavailableError

router = APIRouter(tags=["transcriptions"])


_FORWARDED_HEADERS = {"content-disposition", "retry-after"}


def _fwd(resp: httpx.Response) -> Response:
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json"),
        headers={
            k: v
            for k, v in resp.headers.items()
            if k.lower() in _FORWARDED_HEADERS
        },
    )


@router.post("/api/v1/transcribe")
async def transcribe(
    file: UploadFile = File(...),
    http: httpx.AsyncClient = Depends(get_http_client),
    user: dict = Depends(get_current_user),
):
    try:
        content = await file.read()
        resp = await http.post(
            f"{settings.audio_processor_url}/internal/audio/process",
            files={"file": (file.filename, content, file.content_type)},
            data={"user_id": user["user_id"]},
            timeout=settings.transcribe_timeout,
        )
        return _fwd(resp)
    except httpx.TimeoutException as exc:
        raise GatewayTimeoutError() from exc
    except httpx.ConnectError as exc:
        raise ServiceUnavailableError("audio-processor") from exc


@router.get("/api/v1/transcriptions")
async def list_transcriptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    http: httpx.AsyncClient = Depends(get_http_client),
    user: dict = Depends(get_current_user),
):
    try:
        resp = await http.get(
            f"{settings.transcription_manager_url}/api/v1/transcriptions",
            params={"page": page, "page_size": page_size},
            headers={"X-User-Id": user["user_id"]},
        )
        return _fwd(resp)
    except httpx.TimeoutException as exc:
        raise GatewayTimeoutError() from exc
    except httpx.ConnectError as exc:
        raise ServiceUnavailableError("transcription-manager") from exc


@router.get("/api/v1/transcriptions/{transcription_id}")
async def get_transcription(
    transcription_id: str,
    http: httpx.AsyncClient = Depends(get_http_client),
    user: dict = Depends(get_current_user),
):
    try:
        resp = await http.get(
            f"{settings.transcription_manager_url}/api/v1/transcriptions/{transcription_id}",
            headers={"X-User-Id": user["user_id"]},
        )
        return _fwd(resp)
    except httpx.TimeoutException as exc:
        raise GatewayTimeoutError() from exc
    except httpx.ConnectError as exc:
        raise ServiceUnavailableError("transcription-manager") from exc


@router.patch("/api/v1/transcriptions/{transcription_id}")
async def rename_transcription(
    transcription_id: str,
    body: dict = Body(...),
    http: httpx.AsyncClient = Depends(get_http_client),
    user: dict = Depends(get_current_user),
):
    try:
        resp = await http.patch(
            f"{settings.transcription_manager_url}/api/v1/transcriptions/{transcription_id}",
            json=body,
            headers={"X-User-Id": user["user_id"]},
        )
        return _fwd(resp)
    except httpx.TimeoutException as exc:
        raise GatewayTimeoutError() from exc
    except httpx.ConnectError as exc:
        raise ServiceUnavailableError("transcription-manager") from exc


@router.delete("/api/v1/transcriptions/{transcription_id}")
async def delete_transcription(
    transcription_id: str,
    http: httpx.AsyncClient = Depends(get_http_client),
    user: dict = Depends(get_current_user),
):
    try:
        resp = await http.delete(
            f"{settings.transcription_manager_url}/api/v1/transcriptions/{transcription_id}",
            headers={"X-User-Id": user["user_id"]},
        )
        return _fwd(resp)
    except httpx.TimeoutException as exc:
        raise GatewayTimeoutError() from exc
    except httpx.ConnectError as exc:
        raise ServiceUnavailableError("transcription-manager") from exc


@router.get("/api/v1/transcriptions/{transcription_id}/download")
async def download_transcription(
    transcription_id: str,
    format: str = Query(...),
    http: httpx.AsyncClient = Depends(get_http_client),
    user: dict = Depends(get_current_user),
):
    try:
        resp = await http.get(
            f"{settings.transcription_manager_url}/api/v1/transcriptions/{transcription_id}/download",
            params={"format": format},
            headers={"X-User-Id": user["user_id"]},
        )
        headers = {}
        if "content-disposition" in resp.headers:
            headers["Content-Disposition"] = resp.headers["content-disposition"]
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            media_type=resp.headers.get("content-type"),
            headers=headers,
        )
    except httpx.TimeoutException as exc:
        raise GatewayTimeoutError() from exc
    except httpx.ConnectError as exc:
        raise ServiceUnavailableError("transcription-manager") from exc
