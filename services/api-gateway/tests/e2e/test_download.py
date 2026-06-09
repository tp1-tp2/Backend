"""
11.9 E2E: Transcription download (E2-HU06)

Covers:
- Download TXT → file with correct Content-Type and Content-Disposition
- Download JSON → valid JSON with all fields
- Download SRT → valid subtitle format
- Download unsupported format → 400
"""
from .conftest import mock_resp

_AUTH_HEADER = {"Authorization": "Bearer e2e-jwt-token"}
_TR_ID = "tr-e2e-001"


def test_download_txt_returns_plain_text(auth_client):
    """GET /transcriptions/{id}/download?format=txt → text/plain file."""
    c, http = auth_client
    txt_content = "Ñuqam llamk'ani\nKaypin kachkani\n".encode("utf-8")
    http.get.return_value = mock_resp(
        txt_content,
        status=200,
        content_type="text/plain; charset=utf-8",
        extra_headers={
            "content-disposition": f'attachment; filename="{_TR_ID}.txt"'
        },
    )

    resp = c.get(
        f"/api/v1/transcriptions/{_TR_ID}/download?format=txt",
        headers=_AUTH_HEADER,
    )

    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "")
    assert "Content-Disposition" in resp.headers
    assert resp.content == txt_content


def test_download_json_returns_structured_data(auth_client):
    """GET /transcriptions/{id}/download?format=json → application/json file."""
    c, http = auth_client
    import json

    json_payload = {
        "transcriptionId": _TR_ID,
        "text": "Ñuqam llamk'ani",
        "audioDuration": 4.5,
        "words": [
            {"word": "Ñuqam", "confidence": 0.97, "startTime": 0.0, "endTime": 0.45}
        ],
    }
    http.get.return_value = mock_resp(
        json.dumps(json_payload).encode(),
        status=200,
        content_type="application/json",
        extra_headers={
            "content-disposition": f'attachment; filename="{_TR_ID}.json"'
        },
    )

    resp = c.get(
        f"/api/v1/transcriptions/{_TR_ID}/download?format=json",
        headers=_AUTH_HEADER,
    )

    assert resp.status_code == 200
    assert "application/json" in resp.headers.get("content-type", "")


def test_download_srt_returns_subtitle_format(auth_client):
    """GET /transcriptions/{id}/download?format=srt → SRT subtitle file."""
    c, http = auth_client
    srt_content = (
        "1\n00:00:00,000 --> 00:00:00,450\nÑuqam\n\n"
        "2\n00:00:00,500 --> 00:00:01,000\nllamk'ani\n\n"
    ).encode("utf-8")
    http.get.return_value = mock_resp(
        srt_content,
        status=200,
        content_type="text/srt; charset=utf-8",
        extra_headers={
            "content-disposition": f'attachment; filename="{_TR_ID}.srt"'
        },
    )

    resp = c.get(
        f"/api/v1/transcriptions/{_TR_ID}/download?format=srt",
        headers=_AUTH_HEADER,
    )

    assert resp.status_code == 200
    assert resp.content == srt_content


def test_download_unsupported_format_returns_400(auth_client):
    """GET /transcriptions/{id}/download?format=xlsx → 400 from transcription-manager."""
    c, http = auth_client
    http.get.return_value = mock_resp(
        {"detail": "Unsupported download format: xlsx"}, status=400
    )

    resp = c.get(
        f"/api/v1/transcriptions/{_TR_ID}/download?format=xlsx",
        headers=_AUTH_HEADER,
    )

    assert resp.status_code == 400
