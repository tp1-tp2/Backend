from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AccessDeniedError, TranscriptionNotFoundError
from app.models.transcription import Transcription
from app.schemas.transcription import TranscriptionResponse
from app.services.transcription_service import TranscriptionService


def _make_service() -> TranscriptionService:
    svc = TranscriptionService(MagicMock())
    svc._trans = AsyncMock()
    svc._words = AsyncMock()
    return svc


def _trans(user_id: str = "uid-1") -> MagicMock:
    t = MagicMock(spec=Transcription)
    t.transcription_id = "tid-abc"
    t.user_id = user_id
    t.audio_id = "aid-1"
    t.text = "Imaynallan kashanki"
    t.audio_filename = "test.wav"
    t.audio_duration = 5.0
    t.processing_time = 1.2
    t.created_at = datetime.now(timezone.utc)
    t.word_confidences = []
    return t


async def test_get_by_id_returns_response():
    svc = _make_service()
    svc._trans.get_by_id.return_value = _trans()

    result = await svc.get_by_id("tid-abc", "uid-1")

    assert isinstance(result, TranscriptionResponse)
    assert result.transcription_id == "tid-abc"
    assert result.text == "Imaynallan kashanki"


async def test_get_by_id_not_found_raises_404():
    svc = _make_service()
    svc._trans.get_by_id.return_value = None

    with pytest.raises(TranscriptionNotFoundError):
        await svc.get_by_id("nonexistent", "uid-1")


async def test_get_by_id_wrong_user_raises_403():
    svc = _make_service()
    svc._trans.get_by_id.return_value = _trans(user_id="uid-owner")

    with pytest.raises(AccessDeniedError):
        await svc.get_by_id("tid-abc", "uid-other")


async def test_get_summary_returns_totals():
    svc = _make_service()
    svc._trans.count_by_user.return_value = 7
    svc._trans.get_latest_date_by_user.return_value = datetime.now(timezone.utc)

    result = await svc.get_summary("uid-1")

    assert result.total == 7
    assert result.latest_at is not None


async def test_get_summary_empty_user():
    svc = _make_service()
    svc._trans.count_by_user.return_value = 0
    svc._trans.get_latest_date_by_user.return_value = None

    result = await svc.get_summary("uid-new")

    assert result.total == 0
    assert result.latest_at is None
