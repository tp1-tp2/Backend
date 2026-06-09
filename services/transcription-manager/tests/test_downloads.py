import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AccessDeniedError, TranscriptionNotFoundError, UnsupportedFormatError
from app.models.transcription import Transcription, WordConfidence
from app.services.download_service import (
    DownloadService,
    generate_json,
    generate_srt,
    generate_txt,
)


def _trans(user_id: str = "uid-1") -> MagicMock:
    t = MagicMock(spec=Transcription)
    t.transcription_id = "tid-1"
    t.user_id = user_id
    t.audio_id = "aid-1"
    t.text = "Imaynallan kashanki"
    t.audio_filename = "quechua.wav"
    t.audio_duration = 5.0
    t.processing_time = 1.0
    t.created_at = datetime.now(timezone.utc)
    t.word_confidences = []
    return t


def _word(seq: int, word: str, start: float, end: float, conf: float = 0.9) -> MagicMock:
    w = MagicMock(spec=WordConfidence)
    w.word = word
    w.confidence = conf
    w.start_time = start
    w.end_time = end
    w.sequence_number = seq
    return w


def _make_service() -> DownloadService:
    svc = DownloadService(MagicMock())
    svc._trans = AsyncMock()
    svc._words = AsyncMock()
    return svc


# ---------- generate_txt ----------

def test_generate_txt_has_required_sections():
    content = generate_txt(_trans())
    assert "ASR Platform" in content
    assert "quechua.wav" in content
    assert "Imaynallan kashanki" in content
    assert "TRANSCRIPTION:" in content


# ---------- generate_json ----------

def test_generate_json_camel_case_keys():
    words = [_word(0, "Imaynallan", 0.0, 0.5), _word(1, "kashanki", 0.6, 1.2)]
    data = json.loads(generate_json(_trans(), words))
    assert "userId" in data
    assert "audioFilename" in data
    assert "transcriptionText" in data
    assert "confidenceScores" in data
    assert data["confidenceScores"][0]["word"] == "Imaynallan"
    assert "startTime" in data["confidenceScores"][0]


def test_generate_json_empty_words():
    data = json.loads(generate_json(_trans(), []))
    assert data["confidenceScores"] == []


# ---------- generate_srt ----------

def test_generate_srt_valid_format():
    words = [_word(0, "Imaynallan", 0.0, 0.5), _word(1, "kashanki", 0.6, 1.2)]
    srt = generate_srt(words)
    assert "00:00:00,000 --> 00:00:00,500" in srt
    assert "Imaynallan" in srt
    assert "00:00:00,600 --> 00:00:01,200" in srt


def test_generate_srt_empty_words_returns_placeholder():
    srt = generate_srt([])
    assert "(no transcription)" in srt


# ---------- DownloadService.get_file ----------

async def test_get_file_txt():
    svc = _make_service()
    svc._trans.get_by_id.return_value = _trans()
    svc._words.get_by_transcription.return_value = []

    content, media_type, filename = await svc.get_file("tid-1", "uid-1", "txt")

    assert filename == "quechua.txt"
    assert "text/plain" in media_type
    assert b"TRANSCRIPTION:" in content


async def test_get_file_json():
    svc = _make_service()
    svc._trans.get_by_id.return_value = _trans()
    svc._words.get_by_transcription.return_value = []

    content, media_type, filename = await svc.get_file("tid-1", "uid-1", "json")

    assert filename == "quechua.json"
    assert media_type == "application/json"
    data = json.loads(content)
    assert "transcriptionText" in data


async def test_get_file_srt():
    svc = _make_service()
    svc._trans.get_by_id.return_value = _trans()
    svc._words.get_by_transcription.return_value = []

    content, media_type, filename = await svc.get_file("tid-1", "uid-1", "srt")

    assert filename == "quechua.srt"
    assert "srt" in media_type


async def test_get_file_invalid_format_raises():
    svc = _make_service()
    with pytest.raises(UnsupportedFormatError):
        await svc.get_file("tid-1", "uid-1", "pdf")


async def test_get_file_not_found_raises():
    svc = _make_service()
    svc._trans.get_by_id.return_value = None
    with pytest.raises(TranscriptionNotFoundError):
        await svc.get_file("nonexistent", "uid-1", "txt")


async def test_get_file_wrong_user_raises_403():
    svc = _make_service()
    svc._trans.get_by_id.return_value = _trans(user_id="uid-owner")
    with pytest.raises(AccessDeniedError):
        await svc.get_file("tid-1", "uid-other", "txt")
