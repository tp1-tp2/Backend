import httpx
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.exceptions import AuthenticationError, ServiceUnavailableError

security = HTTPBearer()


async def get_http_client() -> httpx.AsyncClient:
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        yield client


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    http: httpx.AsyncClient = Depends(get_http_client),
) -> dict:
    token = credentials.credentials
    try:
        resp = await http.post(
            f"{settings.auth_service_url}/internal/auth/validate-token",
            json={"token": token},
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("valid"):
                return {
                    "user_id": data["user_id"],
                    "email": data["email"],
                    "token": token,
                }
        raise AuthenticationError()
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        raise ServiceUnavailableError("auth-service") from exc
