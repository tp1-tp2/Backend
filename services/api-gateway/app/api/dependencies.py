import httpx
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core import token_validator
from app.core.config import settings

security = HTTPBearer()


def build_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=settings.request_timeout,
        limits=httpx.Limits(
            max_connections=settings.http_max_connections,
            max_keepalive_connections=settings.http_max_keepalive,
        ),
    )


async def get_http_client(request: Request) -> httpx.AsyncClient:
    # Shared keep-alive pool created in main.py's lifespan. Previously a new
    # AsyncClient (and TCP handshake) was built per request, per hop.
    shared = getattr(request.app.state, "http", None)
    if shared is not None:
        yield shared
        return
    async with build_http_client() as client:
        yield client


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    http: httpx.AsyncClient = Depends(get_http_client),
) -> dict:
    user = await token_validator.validate(credentials.credentials, http)
    return user.as_dict()
