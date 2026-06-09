"""
11.2 E2E: Profile management (E1-HU03)

Covers:
- GET /profile with valid JWT → returns user data
- PUT /profile with valid updates → persisted and returned
- PUT /profile invalid phone → 422
- PUT /profile underage DOB → 422
"""
from .conftest import mock_resp

_PROFILE = {
    "user_id": "e2e-uid-001",
    "email": "test@quechua.org",
    "full_name": "Test User",
    "phone_number": None,
    "date_of_birth": None,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z",
}

_AUTH_HEADER = {"Authorization": "Bearer e2e-jwt-token"}


def test_get_profile_returns_user_data(auth_client):
    """GET /api/v1/users/profile → 200 with complete user data."""
    c, http = auth_client
    http.get.return_value = mock_resp(_PROFILE, status=200)

    resp = c.get("/api/v1/users/profile", headers=_AUTH_HEADER)

    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == "e2e-uid-001"
    assert data["email"] == "test@quechua.org"


def test_update_profile_valid_changes(auth_client):
    """PUT /api/v1/users/profile with valid payload → 200 with updated data."""
    c, http = auth_client
    updated = {**_PROFILE, "full_name": "Updated Name", "phone_number": "+51987654321"}
    http.put.return_value = mock_resp(updated, status=200)

    resp = c.put(
        "/api/v1/users/profile",
        json={"full_name": "Updated Name", "phone_number": "+51987654321"},
        headers=_AUTH_HEADER,
    )

    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Updated Name"
    assert resp.json()["phone_number"] == "+51987654321"


def test_update_profile_invalid_phone_returns_422(auth_client):
    """PUT with non-E.164 phone number → 422 from user-service validation."""
    c, http = auth_client
    http.put.return_value = mock_resp(
        {"detail": "Phone must be in E.164 format"}, status=422
    )

    resp = c.put(
        "/api/v1/users/profile",
        json={"phone_number": "not-a-phone"},
        headers=_AUTH_HEADER,
    )

    assert resp.status_code == 422


def test_update_profile_underage_dob_returns_422(auth_client):
    """PUT with date_of_birth that would make user under 13 → 422."""
    c, http = auth_client
    http.put.return_value = mock_resp(
        {"detail": "User must be at least 13 years old"}, status=422
    )

    resp = c.put(
        "/api/v1/users/profile",
        json={"date_of_birth": "2020-06-01"},
        headers=_AUTH_HEADER,
    )

    assert resp.status_code == 422
