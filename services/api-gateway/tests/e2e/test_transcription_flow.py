"""
11.6 E2E: Audio transcription flow (E2-HU01, E2-HU02)

Covers:
- Upload valid WAV file → 200 with transcription text
- Upload unsupported format → 400
- Upload file > 50 MB → 413
- Upload corrupted file → 400
"""
import io

from .conftest import mock_resp

_AUTH_HEADER = {"Authorization": "Bearer e2e-jwt-token"}


def _wav_bytes() -> bytes:
    """Minimal valid RIFF/WAV header (44 bytes)."""
    return (
        b"RIFF$\x00\x00\x00WAVEfmt "
        b"\x10\x00\x00\x00\x01\x00\x01\x00"  # PCM, 1 channel
        b"\x80>\x00\x00\x00}\x00\x00"        # 16000 Hz sample rate
        b"\x02\x00\x10\x00"                  # block align, 16-bit
        b"data\x00\x00\x00\x00"              # data chunk (empty)
    )


def test_upload_valid_wav_returns_transcription(auth_client):
    """POST /api/v1/transcribe with valid WAV → 200 with transcription fields."""
    c, http = auth_client
    result = {
        "audio_id": "aud-001",
        "filename": "speech.wav",
        "duration_seconds": 4.5,
        "transcription_id": "tr-001",
        "transcription_text": "Ñuqam llamk'ani",
    }
    http.post.return_value = mock_resp(result, status=200)

    resp = c.post(
        "/api/v1/transcribe",
        files={"file": ("speech.wav", io.BytesIO(_wav_bytes()), "audio/wav")},
        headers=_AUTH_HEADER,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert "audio_id" in data
    assert data["transcription_text"] == "Ñuqam llamk'ani"
    http.post.assert_called_once()
    call_url = http.post.call_args.args[0]
    assert "audio-processor" in call_url


def test_upload_unsupported_format_returns_400(auth_client):
    """Uploading a PDF (unsupported) → 400 from audio-processor."""
    c, http = auth_client
    http.post.return_value = mock_resp(
        {"detail": "Unsupported file format: pdf"}, status=400
    )

    resp = c.post(
        "/api/v1/transcribe",
        files={"file": ("report.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
        headers=_AUTH_HEADER,
    )

    assert resp.status_code == 400


def test_upload_oversized_file_returns_413(auth_client):
    """File exceeding 50 MB limit → 413 from audio-processor."""
    c, http = auth_client
    http.post.return_value = mock_resp(
        {"detail": "File exceeds maximum allowed size of 50 MB"}, status=413
    )

    # Actual bytes sent are small — the status comes from the mocked downstream
    resp = c.post(
        "/api/v1/transcribe",
        files={"file": ("huge.wav", io.BytesIO(b"\x00" * 64), "audio/wav")},
        headers=_AUTH_HEADER,
    )

    assert resp.status_code == 413


def test_upload_corrupted_file_returns_400(auth_client):
    """Corrupted audio that ffprobe cannot parse → 400 from audio-processor."""
    c, http = auth_client
    http.post.return_value = mock_resp(
        {"detail": "Corrupted or unreadable audio file"}, status=400
    )

    resp = c.post(
        "/api/v1/transcribe",
        files={"file": ("broken.wav", io.BytesIO(b"this is not audio"), "audio/wav")},
        headers=_AUTH_HEADER,
    )

    assert resp.status_code == 400
