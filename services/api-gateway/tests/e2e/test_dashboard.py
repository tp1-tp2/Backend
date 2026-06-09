"""
11.5 E2E: Dashboard (E1-HU06)

Covers:
- GET /dashboard with valid JWT → aggregated profile + services + transcription summary
- GET /dashboard without auth → 403
"""
from .conftest import mock_resp

_AUTH_HEADER = {"Authorization": "Bearer e2e-jwt-token"}

_PROFILE = {"user_id": "e2e-uid-001", "email": "test@quechua.org", "full_name": "Test User"}
_SUMMARY = {"total": 5, "latest_at": "2024-01-10T12:00:00Z"}
_HEALTH = {"status": "healthy"}


def test_dashboard_returns_aggregated_data(auth_client):
    """GET /api/v1/dashboard → 200 with user, transcription_summary, services."""
    c, http = auth_client

    async def _get(url, **kwargs):
        if "internal/users" in url:
            return mock_resp(_PROFILE, status=200)
        if "internal/transcriptions/summary" in url:
            return mock_resp(_SUMMARY, status=200)
        if "/health" in url:
            return mock_resp(_HEALTH, status=200)
        return mock_resp({}, status=200)

    http.get.side_effect = _get

    resp = c.get("/api/v1/dashboard", headers=_AUTH_HEADER)

    assert resp.status_code == 200
    body = resp.json()
    data = body["data"]

    # User profile aggregated
    assert data["user"]["user_id"] == "e2e-uid-001"
    # Transcription summary aggregated
    assert data["transcription_summary"]["total"] == 5
    # Service health statuses present
    assert "auth" in data["services"]
    assert "asr" in data["services"]
    assert "audio-processor" in data["services"]
    assert "transcription-manager" in data["services"]
    assert data["services"]["auth"] == "healthy"


def test_dashboard_partial_failure_returns_available_data(auth_client):
    """Dashboard gracefully handles downstream failures — returns available data."""
    c, http = auth_client

    async def _get(url, **kwargs):
        # Profile service is down — raises connection error
        if "internal/users" in url:
            import httpx as _httpx
            raise _httpx.ConnectError("user-service down")
        if "internal/transcriptions/summary" in url:
            return mock_resp(_SUMMARY, status=200)
        if "/health" in url:
            return mock_resp(_HEALTH, status=200)
        return mock_resp({}, status=200)

    http.get.side_effect = _get

    resp = c.get("/api/v1/dashboard", headers=_AUTH_HEADER)

    # Dashboard always returns 200 even on partial failure
    assert resp.status_code == 200
    data = resp.json()["data"]
    # Fallback: user_id and email from JWT context
    assert "user_id" in data["user"]
    # Summary still available
    assert data["transcription_summary"]["total"] == 5


def test_dashboard_requires_authentication():
    """GET /dashboard without Authorization header → 403."""
    from app.main import app
    from fastapi.testclient import TestClient

    with TestClient(app, raise_server_exceptions=False) as c:
        resp = c.get("/api/v1/dashboard")

    assert resp.status_code == 403
