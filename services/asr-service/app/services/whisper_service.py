import asyncio
import logging
import uuid
from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.core.exceptions import ModelUnavailableError, TranscriptionTimeoutError
from app.schemas.transcription import TranscribeResponse, WordConfidenceSchema

logger = logging.getLogger(__name__)

_model = None


def load_model():
    import whisper  # heavy import — kept local so tests can run without it
    global _model
    logger.info("Loading Whisper model '%s' on device '%s'", settings.whisper_model, settings.device)
    _model = whisper.load_model(settings.whisper_model, device=settings.device)
    logger.info("Whisper model loaded")
    return _model


def is_loaded() -> bool:
    return _model is not None


def _run_whisper(audio_path: str) -> dict:
    """Blocking call — must be run inside run_in_executor."""
    return _model.transcribe(
        audio_path,
        language=settings.whisper_language,
        word_timestamps=True,
        fp16=(settings.device == "cuda"),
    )


def _extract_words(segments: list) -> list[WordConfidenceSchema]:
    words = []
    seq = 0
    for segment in segments:
        for w in segment.get("words", []):
            words.append(
                WordConfidenceSchema(
                    word=w.get("word", "").strip(),
                    confidence=float(w.get("probability", 1.0)),
                    start_time=float(w.get("start", 0.0)),
                    end_time=float(w.get("end", 0.0)),
                    sequence_number=seq,
                )
            )
            seq += 1
    return words


async def transcribe(
    audio_path: str,
    user_id: str,
    audio_id: str,
    audio_filename: str,
    audio_duration: float,
) -> TranscribeResponse:
    if not is_loaded():
        raise ModelUnavailableError()

    loop = asyncio.get_event_loop()
    timeout = max(30.0, audio_duration * 5.0)
    t0 = datetime.now(timezone.utc)

    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, _run_whisper, audio_path),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        raise TranscriptionTimeoutError()

    processing_time = (datetime.now(timezone.utc) - t0).total_seconds()
    text = (result.get("text") or "").strip()
    words = _extract_words(result.get("segments", []))
    transcription_id = str(uuid.uuid4())

    # Persist via Transcription Manager (non-fatal on failure)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(
                f"{settings.transcription_manager_url}/internal/transcriptions",
                json={
                    "transcription_id": transcription_id,
                    "user_id": user_id,
                    "audio_id": audio_id,
                    "text": text,
                    "audio_filename": audio_filename,
                    "audio_duration": audio_duration,
                    "processing_time": processing_time,
                    "word_confidences": [w.model_dump() for w in words],
                },
            )
    except Exception as exc:
        logger.error("Transcription Manager persist failed for %s: %s", transcription_id, exc)

    return TranscribeResponse(
        transcription_id=transcription_id,
        text=text,
        confidence_scores=words,
        processing_time=processing_time,
    )
