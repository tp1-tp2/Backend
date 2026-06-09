from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.api.dependencies import get_current_user, get_http_client
from app.main import app
from fastapi.testclient import TestClient


def _authenticated_user():
    return {"user_id": "uid-1", "email": "user@example.com", "token": "tok"}


def _http_with_responses(profile: dict | None, summary: dict | None, health: str = "healthy"):
    http = AsyncMock(spec=httpx.AsyncClient)

    async def _get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200 if (profile or summary or True) else 500
        if "/internal/users/" in url:
            resp.json.return_value = profile or {}
            resp.status_code = 200 if profile else 404
        elif "/internal/transcriptions/summary" in url:
            resp.json.return_value = summary or {}
            resp.status_code = 200 if summary else 404
        elif "/health" in url:
            resp.json.return_value = {"status": health}
            resp.status_code = 200
        return resp

    http.get.side_effect = _get
    return http


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = lambda: _authenticated_user()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


def test_dashboard_successful_aggregation(client):
    profile = {"user_id": "uid-1", "email": "user@example.com", "full_name": "Test"}
    summary = {"total": 5, "latest_at": "2024-01-01T00:00:00Z"}
    http = _http_with_responses(profile, summary)
    app.dependency_overrides[get_http_client] = lambda: http

    resp = client.get("/api/v1/dashboard")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["user"]["user_id"] == "uid-1"
    assert data["transcription_summary"]["total"] == 5
    assert data["services"]["auth"] == "healthy"

    app.dependency_overrides.pop(get_http_client, None)


def test_dashboard_partial_failure_returns_available_data(client):
    http = _http_with_responses(profile=None, summary={"total": 3, "latest_at": None})
    app.dependency_overrides[get_http_client] = lambda: http

    resp = client.get("/api/v1/dashboard")

    assert resp.status_code == 200
    data = resp.json()["data"]
    # Fallback user with just user_id and email from JWT context
    assert "user_id" in data["user"]
    assert data["transcription_summary"]["total"] == 3

    app.dependency_overrides.pop(get_http_client, None)


def test_dashboard_requires_auth():
    with TestClient(app, raise_server_exceptions=False) as c:
        resp = c.get("/api/v1/dashboard")
    assert resp.status_code == 403
