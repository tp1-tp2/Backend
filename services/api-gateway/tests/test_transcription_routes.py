import io
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.api.dependencies import get_current_user, get_http_client
from app.main import app
from fastapi.testclient import TestClient


def _authenticated_user():
    return {"user_id": "uid-1", "email": "user@example.com", "token": "tok"}


def _mock_http(body: bytes = b'{"ok":true}', status: int = 200, ct: str = "application/json"):
    http = AsyncMock(spec=httpx.AsyncClient)
    resp = MagicMock()
    resp.status_code = status
    resp.content = body
    resp.headers = {"content-type": ct}
    http.post.return_value = resp
    http.get.return_value = resp
    return http


@pytest.fixture
def client():
    http = _mock_http()
    app.dependency_overrides[get_http_client] = lambda: http
    app.dependency_overrides[get_current_user] = lambda: _authenticated_user()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c, http
    app.dependency_overrides.clear()


def test_transcribe_upload(client):
    c, http = client
    audio = io.BytesIO(b"fake wav content")
    resp = c.post(
        "/api/v1/transcribe",
        files={"file": ("test.wav", audio, "audio/wav")},
    )
    assert resp.status_code == 200
    http.post.assert_called_once()
    call_kwargs = http.post.call_args
    assert "audio-processor" in call_kwargs.args[0]


def test_list_transcriptions(client):
    c, http = client
    resp = c.get("/api/v1/transcriptions?page=1&page_size=10")
    assert resp.status_code == 200
    http.get.assert_called_once()
    assert "transcription-manager" in http.get.call_args.args[0]


def test_get_transcription_detail(client):
    c, http = client
    resp = c.get("/api/v1/transcriptions/tid-abc")
    assert resp.status_code == 200
    assert "tid-abc" in http.get.call_args.args[0]


def test_download_transcription(client):
    c, http = client
    http.get.return_value.content = b"1\n00:00:00,000 --> 00:00:01,000\nHello\n"
    http.get.return_value.headers = {
        "content-type": "text/srt",
        "content-disposition": 'attachment; filename="audio.srt"',
    }
    resp = c.get("/api/v1/transcriptions/tid-abc/download?format=srt")
    assert resp.status_code == 200


def test_transcription_routes_require_auth():
    with TestClient(app, raise_server_exceptions=False) as c:
        assert c.get("/api/v1/transcriptions").status_code == 403
        assert c.get("/api/v1/transcriptions/tid").status_code == 403
