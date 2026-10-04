from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import UploadFile

from app.core.exceptions import (
    CorruptedFileError,
    DurationExceededError,
    FileSizeExceededError,
    InvalidSampleRateError,
    UnsupportedFormatError,
)
from app.services.audio_service import AudioService
from app.services.metadata_service import parse, validate
from app.schemas.audio import AudioMetadata


# ---------- helpers ----------

def _asr_response(status: int = 200, body: dict | None = None, headers: dict | None = None):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = body if body is not None else {"transcription_id": "tid-1", "text": "ari"}
    resp.headers = headers or {}
    return resp


def _make_service(asr_resp=None) -> AudioService:
    http = AsyncMock(spec=httpx.AsyncClient)
    http.post.return_value = asr_resp or _asr_response()
    svc = AudioService(MagicMock(), http)
    svc._audio_repo = AsyncMock()
    return svc


def _ffmpeg_ok():
    """Patch the ffmpeg/filesystem side so process_upload reaches the ASR call."""
    from contextlib import ExitStack

    stack = ExitStack()
    stack.enter_context(patch("app.services.audio_service.ffmpeg_service.probe", AsyncMock(return_value=_good_probe())))
    stack.enter_context(patch("app.services.audio_service.ffmpeg_service.convert_to_wav", AsyncMock(return_value=True)))
    stack.enter_context(patch("app.services.audio_service.ffmpeg_service.make_output_path", return_value="/tmp/out.wav"))
    stack.enter_context(patch("app.services.audio_service._read_bytes", return_value=b"RIFF"))
    return stack


def _upload(filename: str = "audio.wav", size: int = 1024) -> UploadFile:
    file = MagicMock(spec=UploadFile)
    file.filename = filename
    file.read = AsyncMock(return_value=b"x" * size)
    return file


def _good_probe() -> dict:
    return {
        "format": "wav",
        "duration": 10.0,
        "sample_rate": 16000,
        "channels": 1,
        "bit_rate": 256000,
        "codec": "pcm_s16le",
    }


# ---------- extension validation ----------

async def test_unsupported_extension_raises():
    svc = _make_service()
    with pytest.raises(UnsupportedFormatError):
        await svc.process_upload(_upload("audio.exe"), "uid-1")


@pytest.mark.parametrize("ext", ["wav", "mp3", "flac", "ogg", "m4a"])
async def test_supported_extensions_pass(ext):
    svc = _make_service()
    with _ffmpeg_ok():
        result = await svc.process_upload(_upload(f"audio.{ext}"), "uid-1")
    assert result.audio_id
    assert result.transcription_id == "tid-1"


# ---------- size validation ----------

async def test_empty_file_raises():
    svc = _make_service()
    with pytest.raises(CorruptedFileError):
        await svc.process_upload(_upload(size=0), "uid-1")


async def test_oversized_file_raises():
    svc = _make_service()
    big = _upload(size=52_428_801)  # 50 MB + 1 byte
    with pytest.raises(FileSizeExceededError):
        await svc.process_upload(big, "uid-1")


# ---------- metadata validation ----------

def test_parse_valid_probe():
    meta = parse(_good_probe())
    assert meta.sample_rate == 16000
    assert meta.duration == 10.0
    assert meta.channels == 1


def test_parse_missing_key_raises():
    with pytest.raises(CorruptedFileError):
        parse({"format": "wav"})  # missing required keys


def test_validate_sample_rate_too_low():
    meta = parse({**_good_probe(), "sample_rate": 4000})
    with pytest.raises(InvalidSampleRateError):
        validate(meta)


def test_validate_sample_rate_too_high():
    meta = parse({**_good_probe(), "sample_rate": 96000})
    with pytest.raises(InvalidSampleRateError):
        validate(meta)


def test_validate_duration_exceeded():
    meta = parse({**_good_probe(), "duration": 3601.0})
    with pytest.raises(DurationExceededError):
        validate(meta)


def test_validate_zero_duration_raises():
    meta = parse({**_good_probe(), "duration": 0.0})
    with pytest.raises(DurationExceededError):
        validate(meta)


def test_validate_good_metadata_passes():
    meta = parse(_good_probe())
    validate(meta)  # must not raise


# ---------- ffmpeg convert failure ----------

async def test_convert_failure_raises():
    svc = _make_service()
    with (
        patch("app.services.audio_service.ffmpeg_service.probe", AsyncMock(return_value=_good_probe())),
        patch("app.services.audio_service.ffmpeg_service.convert_to_wav", AsyncMock(return_value=False)),
        patch("app.services.audio_service.ffmpeg_service.make_output_path", return_value="/tmp/out.wav"),
    ):
        with pytest.raises(CorruptedFileError):
            await svc.process_upload(_upload(), "uid-1")


# ---------- ASR failure propagation (regression: used to return 200 + null) ----------

async def test_asr_overloaded_propagates_503_with_retry_after():
    from fastapi import HTTPException

    svc = _make_service(
        _asr_response(503, {"detail": {"errorCode": "ASR_003", "message": "full"}}, {"retry-after": "5"})
    )
    with _ffmpeg_ok():
        with pytest.raises(HTTPException) as exc_info:
            await svc.process_upload(_upload(), "uid-1")
    assert exc_info.value.status_code == 503
    assert exc_info.value.headers == {"Retry-After": "5"}


async def test_asr_unreachable_raises_503_after_retries():
    from app.core.exceptions import AsrUnavailableError

    svc = _make_service()
    svc._http.post.side_effect = httpx.ConnectError("refused")
    with _ffmpeg_ok(), patch("app.services.audio_service.asyncio.sleep", AsyncMock()):
        with pytest.raises(AsrUnavailableError):
            await svc.process_upload(_upload(), "uid-1")
    assert svc._http.post.call_count == 3  # 1 try + 2 connect retries


async def test_asr_timeout_raises_504():
    from app.core.exceptions import AsrTimeoutError

    svc = _make_service()
    svc._http.post.side_effect = httpx.ReadTimeout("slow")
    with _ffmpeg_ok():
        with pytest.raises(AsrTimeoutError):
            await svc.process_upload(_upload(), "uid-1")
    assert svc._http.post.call_count == 1  # timeouts are NOT retried (work may be in progress)
