"""
11.4 E2E: Logout and session termination (E1-HU05)

Covers:
- Logout → 204
- Use blocklisted token on protected endpoint → 401
- Double logout → 204 both times (idempotent)
"""
from .conftest import mock_resp

_AUTH_HEADER = {"Authorization": "Bearer e2e-jwt-token"}


def test_logout_returns_204(auth_client):
    """POST /api/v1/auth/logout with valid JWT → 204 No Content."""
    c, http = auth_client
    # blocklist-token endpoint returns 200; gateway converts to 204
    http.post.return_value = mock_resp({}, status=200)

    resp = c.post("/api/v1/auth/logout", headers=_AUTH_HEADER)

    assert resp.status_code == 204
    http.post.assert_called_once()  # blocklist-token was called


def test_blocklisted_token_on_protected_endpoint_returns_401(anon_client):
    """After logout the same token is in the blocklist → auth-service returns
    valid=False → gateway raises AuthenticationError (401)."""
    c, http = anon_client
    # validate-token returns valid=False (token was blocklisted)
    http.post.return_value = mock_resp({"valid": False}, status=200)

    resp = c.get("/api/v1/users/profile", headers=_AUTH_HEADER)

    assert resp.status_code == 401


def test_double_logout_is_idempotent(auth_client):
    """Logging out twice returns 204 both times (auth-service is idempotent)."""
    c, http = auth_client
    http.post.return_value = mock_resp({}, status=200)

    resp1 = c.post("/api/v1/auth/logout", headers=_AUTH_HEADER)
    resp2 = c.post("/api/v1/auth/logout", headers=_AUTH_HEADER)

    assert resp1.status_code == 204
    assert resp2.status_code == 204
    assert http.post.call_count == 2
