"""
11.1 E2E: Registration and login flow (E1-HU01, E1-HU02)

Covers:
- Register new user → 201 with userId
- Register same email → 400 duplicate
- Login with registered credentials → JWT token
- Login with wrong password → 401
- Verify JWT can access protected endpoint
"""
from .conftest import mock_resp

_REGISTERED_USER = {
    "user_id": "uid-reg-001",
    "email": "inti@quechua.org",
    "full_name": "Inti Huanca",
    "created_at": "2024-01-01T00:00:00Z",
}
_JWT_PAYLOAD = {
    "token": "jwt.e2e.abc",
    "token_type": "bearer",
    "expires_in": 86400,
}
_VALID_TOKEN_RESP = {
    "valid": True,
    "user_id": "uid-reg-001",
    "email": "inti@quechua.org",
}


def test_register_new_user_returns_201(anon_client):
    """POST /api/v1/auth/register with valid payload → 201 with user_id."""
    c, http = anon_client
    http.post.return_value = mock_resp(_REGISTERED_USER, status=201)

    resp = c.post(
        "/api/v1/auth/register",
        json={"email": "inti@quechua.org", "password": "SecurePass1!", "full_name": "Inti Huanca"},
    )

    assert resp.status_code == 201
    assert resp.json()["user_id"] == "uid-reg-001"
    http.post.assert_called_once()


def test_register_duplicate_email_returns_400(anon_client):
    """Registering with an already-used email → 400 from user-service."""
    c, http = anon_client
    http.post.return_value = mock_resp(
        {"detail": "Email already registered"}, status=400
    )

    resp = c.post(
        "/api/v1/auth/register",
        json={"email": "inti@quechua.org", "password": "SecurePass1!", "full_name": "Inti Huanca"},
    )

    assert resp.status_code == 400


def test_login_with_valid_credentials_returns_jwt(anon_client):
    """POST /api/v1/auth/login with correct credentials → JWT token in response."""
    c, http = anon_client
    http.post.return_value = mock_resp(_JWT_PAYLOAD, status=200)

    resp = c.post(
        "/api/v1/auth/login",
        json={"email": "inti@quechua.org", "password": "SecurePass1!"},
    )

    assert resp.status_code == 200
    assert "token" in resp.json()


def test_login_wrong_password_returns_401(anon_client):
    """Login with incorrect password → 401 from auth-service."""
    c, http = anon_client
    http.post.return_value = mock_resp(
        {"detail": "Invalid credentials"}, status=401
    )

    resp = c.post(
        "/api/v1/auth/login",
        json={"email": "inti@quechua.org", "password": "wrongpassword"},
    )

    assert resp.status_code == 401


def test_jwt_accesses_protected_profile_endpoint(anon_client):
    """JWT obtained from login can access a protected endpoint (GET /users/profile)."""
    c, http = anon_client
    profile_data = {
        "user_id": "uid-reg-001",
        "email": "inti@quechua.org",
        "full_name": "Inti Huanca",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    }
    # validate-token: POST call inside get_current_user
    http.post.return_value = mock_resp(_VALID_TOKEN_RESP, status=200)
    # user profile: GET call inside the route handler
    http.get.return_value = mock_resp(profile_data, status=200)

    resp = c.get(
        "/api/v1/users/profile",
        headers={"Authorization": "Bearer jwt.e2e.abc"},
    )

    assert resp.status_code == 200
    assert resp.json()["email"] == "inti@quechua.org"
    http.post.assert_called_once()  # validate-token was called
    http.get.assert_called_once()   # profile was fetched
