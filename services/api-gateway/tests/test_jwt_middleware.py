from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.api.dependencies import get_current_user
from app.core.exceptions import AuthenticationError, ServiceUnavailableError


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


async def test_valid_token_returns_user_context():
    result = await get_current_user(_credentials("good_token"), _mock_http(valid=True))
    assert result["user_id"] == "uid-1"
    assert result["email"] == "user@example.com"
    assert result["token"] == "good_token"


async def test_invalid_token_raises_401():
    with pytest.raises(AuthenticationError):
        await get_current_user(_credentials(), _mock_http(valid=False))


async def test_auth_service_returns_non_200_raises_401():
    with pytest.raises(AuthenticationError):
        await get_current_user(_credentials(), _mock_http(valid=True, status=500))


async def test_auth_service_unreachable_raises_502():
    with pytest.raises(ServiceUnavailableError):
        await get_current_user(_credentials(), _mock_http(connect_error=True))


async def test_auth_service_timeout_raises_502():
    http = AsyncMock(spec=httpx.AsyncClient)
    http.post.side_effect = httpx.TimeoutException("timeout")
    with pytest.raises(ServiceUnavailableError):
        await get_current_user(_credentials(), http)
