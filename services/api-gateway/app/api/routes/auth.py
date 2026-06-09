import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app.api.dependencies import get_current_user, get_http_client
from app.core.config import settings
from app.core.exceptions import GatewayTimeoutError, ServiceUnavailableError

router = APIRouter(tags=["auth"])


def _fwd(resp: httpx.Response) -> Response:
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json"),
    )


async def _post(http: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
    try:
        return await http.post(url, **kwargs)
    except httpx.TimeoutException as exc:
        raise GatewayTimeoutError() from exc
    except httpx.ConnectError as exc:
        raise ServiceUnavailableError("upstream") from exc


@router.post("/api/v1/auth/register", status_code=201)
async def register(
    request: Request,
    http: httpx.AsyncClient = Depends(get_http_client),
):
    body = await request.json()
    resp = await _post(http, f"{settings.user_service_url}/api/v1/auth/register", json=body)
    return _fwd(resp)


@router.post("/api/v1/auth/login")
async def login(
    request: Request,
    http: httpx.AsyncClient = Depends(get_http_client),
):
    body = await request.json()
    resp = await _post(http, f"{settings.auth_service_url}/api/v1/auth/login", json=body)
    return _fwd(resp)


@router.post("/api/v1/auth/logout", status_code=204)
async def logout(
    http: httpx.AsyncClient = Depends(get_http_client),
    user: dict = Depends(get_current_user),
):
    from datetime import datetime, timezone, timedelta
    # Blocklist the token — expires_at set to now+24h as a safe upper bound
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    await _post(
        http,
        f"{settings.auth_service_url}/internal/auth/blocklist-token",
        json={"token": user["token"], "expires_at": expires_at},
    )


@router.post("/api/v1/auth/password-recovery", status_code=204)
async def password_recovery(
    request: Request,
    http: httpx.AsyncClient = Depends(get_http_client),
):
    body = await request.json()
    await _post(http, f"{settings.auth_service_url}/api/v1/auth/password-recovery", json=body)


@router.post("/api/v1/auth/password-reset", status_code=204)
async def password_reset(
    request: Request,
    http: httpx.AsyncClient = Depends(get_http_client),
):
    body = await request.json()
    await _post(http, f"{settings.auth_service_url}/api/v1/auth/password-reset", json=body)
