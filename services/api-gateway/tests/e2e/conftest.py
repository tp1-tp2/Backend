"""
Shared fixtures and helpers for E2E / integration tests.

All E2E tests run against the API Gateway app with downstream services mocked
via httpx.AsyncClient dependency override.  No real network or DB connections
are made — the tests verify that the gateway routes, transforms, and guards
requests correctly end-to-end.
"""
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.dependencies import get_current_user, get_http_client
from app.core.config import settings
from app.main import app

# Default authenticated user injected when using the `auth_client` fixture
E2E_USER = {
    "user_id": "e2e-uid-001",
    "email": "test@quechua.org",
    "token": "e2e-jwt-token",
}


def mock_resp(body, status: int = 200, content_type: str = "application/json",
              extra_headers: dict | None = None) -> MagicMock:
    """Build a mock httpx.Response for any downstream call."""
    m = MagicMock()
    m.status_code = status
    if isinstance(body, bytes):
        m.content = body
        m.json.side_effect = ValueError("binary payload")
    elif isinstance(body, (dict, list)):
        m.content = json.dumps(body).encode()
        m.json.return_value = body
    else:
        m.content = str(body).encode()
        m.json.side_effect = ValueError("raw string payload")
    m.headers = {"content-type": content_type, **(extra_headers or {})}
    return m


@pytest.fixture
def http() -> AsyncMock:
    """Bare AsyncMock — configure .post/.get/.put return values per test."""
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def anon_client(http):
    """TestClient without any auth override.  Bearer tokens are still validated
    by the real get_current_user dependency (which uses the mocked http)."""
    app.dependency_overrides[get_http_client] = lambda: http
    # These flows assert the round-trip to auth-service, i.e. the original
    # "remote" validation mode (local mode is covered in test_jwt_middleware.py).
    with patch.object(settings, "auth_mode", "remote"):
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c, http
    app.dependency_overrides.clear()


@pytest.fixture
def auth_client(http):
    """TestClient with get_current_user bypassed — pre-authenticated as E2E_USER."""
    app.dependency_overrides[get_http_client] = lambda: http
    app.dependency_overrides[get_current_user] = lambda: dict(E2E_USER)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c, http
    app.dependency_overrides.clear()
