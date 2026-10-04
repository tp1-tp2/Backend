"""Token validation strategies for the gateway.

Two modes, selectable via AUTH_MODE so experiments can compare them (ablation):

- "remote": the original design — every authenticated request makes a
  synchronous round-trip to auth-service (`POST /internal/auth/validate-token`),
  which also hits auth-db to check the blocklist. E6 showed this puts
  auth-service on the critical path of ALL traffic (65.3% of /transcribe failed
  while it was down) and E4 round 3 showed its saturation surfacing as 2652
  misleading 401s.

- "local" (default): the gateway verifies the HS256 signature/expiry itself
  with the shared secret, and checks revocation (logout/password reset) against
  a Redis set that auth-service mirrors on every blocklist write. auth-service
  is then only on the path of login/register, not of every transcription.

Revocation check trade-off (documented, configurable): if Redis is unreachable
the gateway either fails OPEN (accepts a validly-signed, unexpired token —
availability over strict revocation, default) or fails CLOSED (503). A revoked
token can therefore be accepted for the duration of a Redis outage when
REVOCATION_FAIL_OPEN=true; the token still expires at its `exp`.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

import httpx
import jwt

from app.core.config import settings
from app.core.redis_client import get_redis
from app.core.exceptions import (
    AuthenticationError,
    ServiceUnavailableError,
    UpstreamOverloadedError,
)

logger = logging.getLogger(__name__)

REVOKED_KEY_PREFIX = "revoked:"

@dataclass
class UserContext:
    user_id: str
    email: str
    token: str

    def as_dict(self) -> dict:
        return {"user_id": self.user_id, "email": self.email, "token": self.token}


def hash_token(token: str) -> str:
    # Must match auth-service's app.core.security.hash_token
    return hashlib.sha256(token.encode()).hexdigest()


async def _is_revoked(token: str) -> bool:
    client = get_redis()
    if client is None:
        return False
    try:
        return bool(await client.exists(REVOKED_KEY_PREFIX + hash_token(token)))
    except Exception as exc:
        if settings.revocation_fail_open:
            logger.warning("Revocation store unreachable, failing open: %s", exc)
            return False
        raise UpstreamOverloadedError("revocation-store") from exc


async def validate_local(token: str) -> UserContext:
    try:
        data = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id, email = data["user_id"], data["email"]
    except (jwt.InvalidTokenError, KeyError) as exc:
        raise AuthenticationError() from exc
    if await _is_revoked(token):
        raise AuthenticationError("Token has been revoked")
    return UserContext(user_id=user_id, email=email, token=token)


async def validate_remote(token: str, http: httpx.AsyncClient) -> UserContext:
    try:
        resp = await http.post(
            f"{settings.auth_service_url}/internal/auth/validate-token",
            json={"token": token},
            timeout=settings.auth_validate_timeout_seconds,
        )
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        raise ServiceUnavailableError("auth-service") from exc

    # Only a definitive answer from auth-service is a 401. A 5xx means "could
    # not decide" (overload, DB down) and must NOT be reported to the client as
    # bad credentials — that masking hid the real E4 round-3 bottleneck.
    if resp.status_code >= 500 or resp.status_code == 429:
        raise UpstreamOverloadedError("auth-service")
    if resp.status_code == 200:
        data = resp.json()
        if data.get("valid"):
            return UserContext(user_id=data["user_id"], email=data["email"], token=token)
    raise AuthenticationError()


async def validate(token: str, http: httpx.AsyncClient) -> UserContext:
    if settings.auth_mode == "remote":
        return await validate_remote(token, http)
    return await validate_local(token)
