from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import TokenInvalidError
from app.core.security import generate_jwt, hash_token
from app.services.auth_service import AuthService


def _make_service():
    svc = AuthService(MagicMock())
    svc._credentials = AsyncMock()
    svc._blocklist = AsyncMock()
    svc._recovery = AsyncMock()
    return svc


async def test_logout_adds_token_hash_to_blocklist():
    svc = _make_service()
    token = generate_jwt("user-1", "user@example.com")

    await svc.logout(token)

    svc._blocklist.add.assert_called_once()
    call_args = svc._blocklist.add.call_args
    assert call_args.args[0] == hash_token(token)
    assert call_args.args[1] == "user-1"


async def test_logout_with_invalid_token_raises():
    svc = _make_service()

    with pytest.raises(TokenInvalidError):
        await svc.logout("not.a.real.token")


async def test_validate_token_valid_and_not_blocklisted():
    svc = _make_service()
    svc._blocklist.exists.return_value = False
    token = generate_jwt("user-2", "other@example.com")

    result = await svc.validate_token(token)

    assert result.valid is True
    assert result.user_id == "user-2"
    assert result.email == "other@example.com"


async def test_validate_token_blocklisted_returns_invalid():
    svc = _make_service()
    svc._blocklist.exists.return_value = True
    token = generate_jwt("user-2", "other@example.com")

    result = await svc.validate_token(token)

    assert result.valid is False
    assert result.user_id == ""


async def test_validate_token_malformed_returns_invalid():
    svc = _make_service()

    result = await svc.validate_token("garbage.token")

    assert result.valid is False


async def test_double_logout_second_call_still_blocklists():
    """Second logout is idempotent — hash is stored again (upsert behaviour from DB)."""
    svc = _make_service()
    token = generate_jwt("user-3", "x@example.com")

    await svc.logout(token)
    await svc.logout(token)

    assert svc._blocklist.add.call_count == 2
