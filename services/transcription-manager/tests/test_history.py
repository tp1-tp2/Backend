from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import InvalidPageSizeError
from app.models.transcription import Transcription
from app.schemas.transcription import TranscriptionListResponse
from app.services.transcription_service import TranscriptionService


def _make_service() -> TranscriptionService:
    svc = TranscriptionService(MagicMock())
    svc._trans = AsyncMock()
    svc._words = AsyncMock()
    return svc


def _trans(i: int = 1) -> MagicMock:
    t = MagicMock(spec=Transcription)
    t.transcription_id = f"tid-{i}"
    t.text = f"Transcription {i}"
    t.audio_filename = f"audio_{i}.wav"
    t.audio_duration = 10.0
    t.processing_time = 2.0
    t.created_at = datetime.now(timezone.utc)
    t.word_confidences = []
    return t


async def test_list_returns_paginated_response():
    svc = _make_service()
    svc._trans.get_by_user.return_value = [_trans(1), _trans(2)]
    svc._trans.count_by_user.return_value = 5

    result = await svc.list_by_user("uid-1", page=1, page_size=2)

    assert isinstance(result, TranscriptionListResponse)
    assert len(result.transcriptions) == 2
    assert result.pagination.total_items == 5
    assert result.pagination.total_pages == 3
    assert result.pagination.current_page == 1


async def test_list_empty_returns_200_with_empty_list():
    svc = _make_service()
    svc._trans.get_by_user.return_value = []
    svc._trans.count_by_user.return_value = 0

    result = await svc.list_by_user("uid-1", page=1, page_size=20)

    assert result.transcriptions == []
    assert result.pagination.total_items == 0
    assert result.pagination.total_pages == 1


async def test_list_page_2_passes_correct_offset():
    svc = _make_service()
    svc._trans.get_by_user.return_value = []
    svc._trans.count_by_user.return_value = 50

    await svc.list_by_user("uid-1", page=3, page_size=10)

    svc._trans.get_by_user.assert_called_once_with("uid-1", limit=10, offset=20)


async def test_list_invalid_page_size_zero_raises():
    svc = _make_service()
    with pytest.raises(InvalidPageSizeError):
        await svc.list_by_user("uid-1", page=1, page_size=0)


async def test_list_invalid_page_size_over_limit_raises():
    svc = _make_service()
    with pytest.raises(InvalidPageSizeError):
        await svc.list_by_user("uid-1", page=1, page_size=101)
