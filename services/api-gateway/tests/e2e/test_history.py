"""
11.8 E2E: Transcription history (E2-HU05)

Covers:
- GET /transcriptions with no results → 200 empty list
- GET /transcriptions with results → paginated list
- GET /transcriptions/{id} for own transcription → full detail
- GET /transcriptions/{id} for another user's transcription → 403
"""
from .conftest import mock_resp

_AUTH_HEADER = {"Authorization": "Bearer e2e-jwt-token"}


def _tr(i: int) -> dict:
    return {
        "transcription_id": f"tr-{i:03d}",
        "user_id": "e2e-uid-001",
        "audio_id": f"aud-{i:03d}",
        "text": f"Quechua sample text {i}",
        "audio_filename": f"audio_{i}.wav",
        "audio_duration": 5.0 + i,
        "processing_time": 1.2,
        "created_at": f"2024-01-{i:02d}T12:00:00Z",
        "confidence_scores": [],
    }


def test_transcriptions_empty_list_returns_200(auth_client):
    """GET /api/v1/transcriptions when user has no transcriptions → 200 empty list."""
    c, http = auth_client
    http.get.return_value = mock_resp(
        {"transcriptions": [], "total": 0, "page": 1, "page_size": 20},
        status=200,
    )

    resp = c.get("/api/v1/transcriptions", headers=_AUTH_HEADER)

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["transcriptions"] == []


def test_transcriptions_returns_paginated_list(auth_client):
    """GET /api/v1/transcriptions with results → list ordered by date desc."""
    c, http = auth_client
    items = [_tr(i) for i in range(1, 4)]
    http.get.return_value = mock_resp(
        {"transcriptions": items, "total": 3, "page": 1, "page_size": 20},
        status=200,
    )

    resp = c.get(
        "/api/v1/transcriptions?page=1&page_size=20", headers=_AUTH_HEADER
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 3
    assert len(body["transcriptions"]) == 3
    assert body["transcriptions"][0]["transcription_id"] == "tr-001"


def test_transcription_detail_own_returns_200(auth_client):
    """GET /api/v1/transcriptions/{id} for own transcription → full detail."""
    c, http = auth_client
    detail = _tr(1)
    detail["confidence_scores"] = [
        {"word": "Ñuqa", "confidence": 0.95, "start_time": 0.0, "end_time": 0.4,
         "sequence_number": 1}
    ]
    http.get.return_value = mock_resp(detail, status=200)

    resp = c.get("/api/v1/transcriptions/tr-001", headers=_AUTH_HEADER)

    assert resp.status_code == 200
    data = resp.json()
    assert data["transcription_id"] == "tr-001"
    assert len(data["confidence_scores"]) == 1


def test_transcription_detail_other_user_returns_403(auth_client):
    """GET /api/v1/transcriptions/{id} for another user's transcription → 403."""
    c, http = auth_client
    http.get.return_value = mock_resp(
        {"detail": "Access denied to this resource"}, status=403
    )

    resp = c.get("/api/v1/transcriptions/tr-other-user", headers=_AUTH_HEADER)

    assert resp.status_code == 403
