import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from app.api.dependencies import get_current_user, get_http_client
from app.core.config import settings
from app.core.exceptions import GatewayTimeoutError, ServiceUnavailableError

router = APIRouter(tags=["users"])


def _fwd(resp: httpx.Response) -> Response:
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json"),
    )


@router.get("/api/v1/users/profile")
async def get_profile(
    http: httpx.AsyncClient = Depends(get_http_client),
    user: dict = Depends(get_current_user),
):
    try:
        resp = await http.get(
            f"{settings.user_service_url}/api/v1/users/profile",
            headers={"X-User-Id": user["user_id"]},
        )
        return _fwd(resp)
    except httpx.TimeoutException as exc:
        raise GatewayTimeoutError() from exc
    except httpx.ConnectError as exc:
        raise ServiceUnavailableError("user-service") from exc


@router.put("/api/v1/users/profile")
async def update_profile(
    request: Request,
    http: httpx.AsyncClient = Depends(get_http_client),
    user: dict = Depends(get_current_user),
):
    try:
        body = await request.json()
        resp = await http.put(
            f"{settings.user_service_url}/api/v1/users/profile",
            json=body,
            headers={"X-User-Id": user["user_id"]},
        )
        return _fwd(resp)
    except httpx.TimeoutException as exc:
        raise GatewayTimeoutError() from exc
    except httpx.ConnectError as exc:
        raise ServiceUnavailableError("user-service") from exc
