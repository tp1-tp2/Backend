from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ModelUnavailableError, TranscriptionTimeoutError
from app.schemas.transcription import TranscribeResponse
from app.services import whisper_service


def _mock_result(text: str = "Imaynallan kashanki") -> dict:
    return {
        "text": text,
        "segments": [
            {
                "words": [
                    {"word": "Imaynallan", "probability": 0.95, "start": 0.0, "end": 0.5},
                    {"word": "kashanki", "probability": 0.88, "start": 0.6, "end": 1.2},
                ]
            }
        ],
    }


async def test_transcribe_raises_when_model_not_loaded():
    with patch.object(whisper_service, "_model", None):
        with pytest.raises(ModelUnavailableError):
            await whisper_service.transcribe(
                audio_path="/tmp/audio.wav",
                user_id="uid-1",
                audio_id="aid-1",
                audio_filename="test.wav",
                audio_duration=2.0,
            )


async def test_transcribe_returns_response():
    with (
        patch.object(whisper_service, "_model", MagicMock()),
        patch.object(whisper_service, "_run_whisper", return_value=_mock_result()),
        patch("app.services.whisper_service.httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=MagicMock(status_code=201))
        mock_client_cls.return_value = mock_client

        result = await whisper_service.transcribe(
            audio_path="/tmp/audio.wav",
            user_id="uid-1",
            audio_id="aid-1",
            audio_filename="test.wav",
            audio_duration=2.0,
        )

    assert isinstance(result, TranscribeResponse)
    assert result.text == "Imaynallan kashanki"
    assert len(result.confidence_scores) == 2
    assert result.processing_time >= 0


async def test_transcribe_empty_audio_returns_empty_text():
    empty_result = {"text": "", "segments": []}
    with (
        patch.object(whisper_service, "_model", MagicMock()),
        patch.object(whisper_service, "_run_whisper", return_value=empty_result),
        patch("app.services.whisper_service.httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=MagicMock(status_code=201))
        mock_client_cls.return_value = mock_client

        result = await whisper_service.transcribe(
            audio_path="/tmp/empty.wav",
            user_id="uid-1",
            audio_id="aid-2",
            audio_filename="empty.wav",
            audio_duration=0.5,
        )

    assert result.text == ""
    assert result.confidence_scores == []


async def test_transcribe_timeout_raises():
    import asyncio

    async def _slow(*args, **kwargs):
        await asyncio.sleep(999)

    with (
        patch.object(whisper_service, "_model", MagicMock()),
        patch(
            "asyncio.get_event_loop",
            return_value=MagicMock(
                run_in_executor=lambda *a, **k: asyncio.sleep(999)
            ),
        ),
        patch("asyncio.wait_for", side_effect=asyncio.TimeoutError),
    ):
        with pytest.raises(TranscriptionTimeoutError):
            await whisper_service.transcribe(
                audio_path="/tmp/audio.wav",
                user_id="uid-1",
                audio_id="aid-3",
                audio_filename="test.wav",
                audio_duration=10.0,
            )


def test_extract_words_maps_probability_to_confidence():
    segments = [
        {
            "words": [
                {"word": " Allianchu", "probability": 0.75, "start": 0.0, "end": 0.4},
                {"word": " Rimani", "probability": 0.90, "start": 0.5, "end": 0.9},
            ]
        }
    ]
    words = whisper_service._extract_words(segments)
    assert len(words) == 2
    assert words[0].word == "Allianchu"
    assert words[0].confidence == 0.75
    assert words[0].sequence_number == 0
    assert words[1].sequence_number == 1


def test_extract_words_empty_segments():
    assert whisper_service._extract_words([]) == []
