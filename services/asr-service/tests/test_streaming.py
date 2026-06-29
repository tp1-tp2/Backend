from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import CapacityReachedError
from app.services.streaming_service import ConnectionManager, _write_wav
import tempfile, os


# ---------- ConnectionManager unit tests ----------

async def test_connect_returns_session_id():
    mgr = ConnectionManager()
    session_id = await mgr.connect("user-1")
    assert session_id
    assert mgr.connection_count == 1
    await mgr.disconnect(session_id)


async def test_disconnect_removes_session():
    mgr = ConnectionManager()
    sid = await mgr.connect("user-1")
    await mgr.disconnect(sid)
    assert mgr.connection_count == 0


async def test_capacity_limit_raises():
    mgr = ConnectionManager()
    with patch("app.services.streaming_service.settings") as mock_cfg:
        mock_cfg.max_concurrent_connections = 2
        await mgr.connect("user-1")
        await mgr.connect("user-2")
        with pytest.raises(CapacityReachedError):
            await mgr.connect("user-3")


async def test_append_chunk_accumulates():
    mgr = ConnectionManager()
    sid = await mgr.connect("user-1")
    mgr.append_chunk(sid, b"\x00\x01")
    mgr.append_chunk(sid, b"\x02\x03")
    assert bytes(mgr._buffers[sid]) == b"\x00\x01\x02\x03"
    await mgr.disconnect(sid)


async def test_append_chunk_unknown_session_ignored():
    mgr = ConnectionManager()
    mgr.append_chunk("nonexistent", b"\xff")  # must not raise


async def test_partial_buffer_trims_independently_of_full_buffer():
    mgr = ConnectionManager()
    sid = await mgr.connect("user-1", sample_rate=16000)
    with patch("app.services.streaming_service.settings") as mock_cfg:
        mock_cfg.audio_buffer_max_seconds = 600
        mock_cfg.partial_window_seconds = 1  # 1s = 32000 bytes at 16kHz/16-bit mono
        mgr.append_chunk(sid, b"\x00" * 40000)
    # Full buffer (used by finalize) keeps everything.
    assert len(mgr._buffers[sid]) == 40000
    # Partial buffer (used by get_partial) is trimmed to the short window.
    assert len(mgr._partial_buffers[sid]) == 32000
    await mgr.disconnect(sid)


async def test_get_partial_no_model_returns_none():
    mgr = ConnectionManager()
    sid = await mgr.connect("user-1")
    mgr.append_chunk(sid, b"\x00" * 1000)
    with patch("app.services.streaming_service.whisper_service.is_loaded", return_value=False):
        result = await mgr.get_partial(sid)
    assert result is None
    await mgr.disconnect(sid)


async def test_get_partial_empty_buffer_returns_none():
    mgr = ConnectionManager()
    sid = await mgr.connect("user-1")
    with patch("app.services.streaming_service.whisper_service.is_loaded", return_value=True):
        result = await mgr.get_partial(sid)
    assert result is None
    await mgr.disconnect(sid)


async def test_get_partial_with_model_returns_text():
    mgr = ConnectionManager()
    sid = await mgr.connect("user-1")
    mgr.append_chunk(sid, b"\x00" * 3200)  # ~100ms of silence at 16kHz 16-bit

    with (
        patch("app.services.streaming_service.whisper_service.is_loaded", return_value=True),
        patch("app.services.streaming_service.whisper_service._run_whisper", return_value={"text": "Ari", "segments": []}),
    ):
        result = await mgr.get_partial(sid)

    assert result is not None
    assert result.text == "Ari"
    assert result.type == "partial"
    await mgr.disconnect(sid)


# ---------- WAV helper ----------

def test_write_wav_produces_valid_header():
    pcm = b"\x00\x00" * 160  # 10ms of silence at 16kHz
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        _write_wav(tmp_path, pcm)
        with open(tmp_path, "rb") as f:
            header = f.read(44)
        assert header[:4] == b"RIFF"
        assert header[8:12] == b"WAVE"
        assert header[12:16] == b"fmt "
        assert header[36:40] == b"data"
    finally:
        os.unlink(tmp_path)
