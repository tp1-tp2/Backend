from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.api.dependencies import get_current_user, get_http_client
from app.main import app
from fastapi.testclient import TestClient


def _mock_http_200(body: dict | None = None):
    http = AsyncMock(spec=httpx.AsyncClient)
    resp = MagicMock()
    resp.status_code = 200
    resp.content = b'{"token":"jwt123","expires_in":86400}'
    resp.headers = {"content-type": "application/json"}
    resp.json.return_value = body or {}
    http.post.return_value = resp
    http.get.return_value = resp
    return http


def _authenticated_user():
    return {"user_id": "uid-1", "email": "user@example.com", "token": "tok"}


@pytest.fixture
def client_no_auth():
    """Client with mocked http but no JWT override."""
    http = _mock_http_200()
    app.dependency_overrides[get_http_client] = lambda: http
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_auth():
    """Client with both mocked http and authenticated user."""
    http = _mock_http_200()
    app.dependency_overrides[get_http_client] = lambda: http
    app.dependency_overrides[get_current_user] = lambda: _authenticated_user()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


def test_login_proxied(client_no_auth):
    resp = client_no_auth.post(
        "/api/v1/auth/login", json={"email": "u@e.com", "password": "pass1234"}
    )
    assert resp.status_code == 200


def test_register_proxied(client_no_auth):
    resp = client_no_auth.post(
        "/api/v1/auth/register",
        json={"email": "u@e.com", "password": "pass1234", "full_name": "User"},
    )
    # Downstream mock returns 200; gateway forwards whatever it gets
    assert resp.status_code in (200, 201)


def test_logout_requires_auth(client_no_auth):
    resp = client_no_auth.post("/api/v1/auth/logout")
    assert resp.status_code == 403  # missing bearer token → 403 from HTTPBearer


def test_logout_authenticated(client_auth):
    resp = client_auth.post("/api/v1/auth/logout")
    assert resp.status_code in (200, 204)


def test_password_recovery_proxied(client_no_auth):
    resp = client_no_auth.post(
        "/api/v1/auth/password-recovery", json={"email": "u@e.com"}
    )
    assert resp.status_code in (200, 204)


def test_password_reset_proxied(client_no_auth):
    resp = client_no_auth.post(
        "/api/v1/auth/password-reset",
        json={"token": "tok", "new_password": "newpass1234"},
    )
    assert resp.status_code in (200, 204)
