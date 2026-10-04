from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import jwt
import pytest

from app.api.dependencies import get_current_user
from app.core import token_validator
from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    ServiceUnavailableError,
    UpstreamOverloadedError,
)


def _mock_http(valid: bool = True, status: int = 200, connect_error: bool = False):
    http = AsyncMock(spec=httpx.AsyncClient)
    if connect_error:
        http.post.side_effect = httpx.ConnectError("refused")
        return http
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = {
        "valid": valid,
        "user_id": "uid-1",
        "email": "user@example.com",
    }
    http.post.return_value = resp
    return http


def _credentials(token: str = "tok"):
    cred = MagicMock()
    cred.credentials = token
    return cred


def _signed(secret: str | None = None, expires_in: timedelta = timedelta(hours=1)) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "user_id": "uid-1",
            "email": "user@example.com",
            "iat": int(now.timestamp()),
            "exp": int((now + expires_in).timestamp()),
        },
        secret or settings.jwt_secret_key,
        algorithm="HS256",
    )


@pytest.fixture
def remote_mode():
    with patch.object(settings, "auth_mode", "remote"):
        yield


@pytest.fixture
def local_mode():
    with patch.object(settings, "auth_mode", "local"):
        yield


# --- remote mode (original design: round-trip to auth-service) ---


async def test_valid_token_returns_user_context(remote_mode):
    result = await get_current_user(_credentials("good_token"), _mock_http(valid=True))
    assert result["user_id"] == "uid-1"
    assert result["email"] == "user@example.com"
    assert result["token"] == "good_token"


async def test_invalid_token_raises_401(remote_mode):
    with pytest.raises(AuthenticationError):
        await get_current_user(_credentials(), _mock_http(valid=False))


async def test_auth_service_5xx_raises_503_not_401(remote_mode):
    # Regression: an overloaded auth-service used to surface as 401, masking
    # the real E4 round-3 bottleneck behind "bad credentials".
    with pytest.raises(UpstreamOverloadedError) as exc_info:
        await get_current_user(_credentials(), _mock_http(valid=True, status=500))
    assert exc_info.value.status_code == 503
    assert "Retry-After" in exc_info.value.headers


async def test_auth_service_unreachable_raises_502(remote_mode):
    with pytest.raises(ServiceUnavailableError):
        await get_current_user(_credentials(), _mock_http(connect_error=True))


async def test_auth_service_timeout_raises_502(remote_mode):
    http = AsyncMock(spec=httpx.AsyncClient)
    http.post.side_effect = httpx.TimeoutException("timeout")
    with pytest.raises(ServiceUnavailableError):
        await get_current_user(_credentials(), http)


# --- local mode (default: signature verified in the gateway) ---


async def test_local_valid_token_never_calls_auth_service(local_mode):
    http = _mock_http(connect_error=True)  # auth-service "down"
    result = await get_current_user(_credentials(_signed()), http)
    assert result["user_id"] == "uid-1"
    http.post.assert_not_called()


async def test_local_wrong_signature_raises_401(local_mode):
    with pytest.raises(AuthenticationError):
        await get_current_user(_credentials(_signed(secret="x" * 40)), _mock_http())


async def test_local_expired_token_raises_401(local_mode):
    with pytest.raises(AuthenticationError):
        await get_current_user(
            _credentials(_signed(expires_in=timedelta(seconds=-5))), _mock_http()
        )


async def test_local_revoked_token_raises_401(local_mode):
    store = AsyncMock()
    store.exists.return_value = 1
    with patch.object(token_validator, "get_redis", return_value=store):
        with pytest.raises(AuthenticationError):
            await get_current_user(_credentials(_signed()), _mock_http())


async def test_local_revocation_store_down_fails_open_by_default(local_mode):
    store = AsyncMock()
    store.exists.side_effect = ConnectionError("redis down")
    with patch.object(token_validator, "get_redis", return_value=store):
        result = await get_current_user(_credentials(_signed()), _mock_http())
    assert result["user_id"] == "uid-1"


async def test_local_revocation_store_down_fails_closed_when_configured(local_mode):
    store = AsyncMock()
    store.exists.side_effect = ConnectionError("redis down")
    with (
        patch.object(token_validator, "get_redis", return_value=store),
        patch.object(settings, "revocation_fail_open", False),
    ):
        with pytest.raises(UpstreamOverloadedError):
            await get_current_user(_credentials(_signed()), _mock_http())
