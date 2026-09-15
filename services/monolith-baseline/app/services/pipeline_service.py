"""Orchestrates upload -> validate -> convert -> transcribe -> persist as
direct in-process function calls. This replaces the 3 HTTP hops the real stack
makes (audio-processor -> asr-service -> transcription-manager) with plain
Python calls in the same request handler — the exact "no separation of
responsibilities" contrast E3 measures against the microservices architecture.
"""
import logging
import tempfile
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import CorruptedFileError, FileSizeExceededError, UnsupportedFormatError
from app.models.audio import AudioFile
from app.models.transcription import Transcription, WordConfidence
from app.schemas.transcription import TranscriptionResponse, WordConfidenceSchema
from app.services import ffmpeg_service, metadata_service, whisper_service

logger = logging.getLogger(__name__)

_ALLOWED = set(settings.allowed_formats)


async def process_upload(session: AsyncSession, file: UploadFile, user_id: str) -> TranscriptionResponse:
    ext = Path(file.filename or "").suffix.lstrip(".").lower()
    if ext not in _ALLOWED:
        raise UnsupportedFormatError()

    content = await file.read()
    if len(content) == 0:
        raise CorruptedFileError()
    if len(content) > settings.max_file_size_bytes:
        raise FileSizeExceededError()

    with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        probe_result = await ffmpeg_service.probe(tmp_path)
        metadata = metadata_service.parse(probe_result)
        metadata_service.validate(metadata)

        audio_id = str(uuid.uuid4())
        out_path = ffmpeg_service.make_output_path(audio_id)
        ok = await ffmpeg_service.convert_to_wav(tmp_path, out_path)
        if not ok:
            raise CorruptedFileError()
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    now = datetime.now(timezone.utc)
    session.add(
        AudioFile(
            audio_id=audio_id,
            user_id=user_id,
            filename=file.filename or f"{audio_id}.{ext}",
            original_format=ext,
            file_size_bytes=len(content),
            duration_seconds=Decimal(str(round(metadata.duration, 2))),
            sample_rate=metadata.sample_rate,
            channels=metadata.channels,
            bit_rate=metadata.bit_rate,
            storage_path=out_path,
            processed_path=out_path,
            uploaded_at=now,
            processed_at=now,
        )
    )

    # Direct call — no HTTP round trip to a separate ASR service.
    result = await whisper_service.transcribe(audio_path=out_path, audio_duration=metadata.duration)

    transcription_id = str(uuid.uuid4())
    words: list[WordConfidenceSchema] = result["words"]
    transcription = Transcription(
        transcription_id=transcription_id,
        user_id=user_id,
        audio_id=audio_id,
        text=result["text"],
        audio_filename=file.filename or f"{audio_id}.{ext}",
        audio_duration=Decimal(str(round(metadata.duration, 2))),
        processing_time=Decimal(str(round(result["processing_time"], 2))),
        created_at=now,
        device_used=settings.device,
        compute_type="fp32",
    )
    transcription.word_confidences = [
        WordConfidence(
            word=w.word,
            confidence=Decimal(str(w.confidence)),
            start_time=Decimal(str(w.start_time)),
            end_time=Decimal(str(w.end_time)),
            sequence_number=w.sequence_number,
        )
        for w in words
    ]
    session.add(transcription)
    await session.commit()
    await session.refresh(transcription, attribute_names=["word_confidences"])

    return TranscriptionResponse(
        transcription_id=transcription_id,
        user_id=user_id,
        audio_id=audio_id,
        text=result["text"],
        audio_filename=transcription.audio_filename,
        audio_duration=float(transcription.audio_duration),
        processing_time=float(transcription.processing_time),
        created_at=now,
        confidence_scores=words,
        device_used=settings.device,
        compute_type="fp32",
    )
