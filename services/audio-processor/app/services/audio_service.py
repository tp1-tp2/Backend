import logging
import tempfile
import uuid
from decimal import Decimal
from pathlib import Path

import httpx
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    CorruptedFileError,
    FileSizeExceededError,
    UnsupportedFormatError,
)
from app.db.repositories import AudioRepository
from app.schemas.audio import AudioUploadResponse
from app.services import ffmpeg_service, metadata_service

logger = logging.getLogger(__name__)

_ALLOWED = set(settings.allowed_formats)


class AudioService:
    def __init__(self, session: AsyncSession, http_client: httpx.AsyncClient) -> None:
        self._audio_repo = AudioRepository(session)
        self._http = http_client

    async def process_upload(
        self, file: UploadFile, user_id: str
    ) -> AudioUploadResponse:
        # 1. Validate extension
        ext = Path(file.filename or "").suffix.lstrip(".").lower()
        if ext not in _ALLOWED:
            raise UnsupportedFormatError()

        # 2. Read into temp file + validate size
        content = await file.read()
        if len(content) == 0:
            raise CorruptedFileError()
        if len(content) > settings.max_file_size_bytes:
            raise FileSizeExceededError()

        # 3. Write to temp file for ffprobe
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # 4. Probe + validate metadata
            probe_result = await ffmpeg_service.probe(tmp_path)
            metadata = metadata_service.parse(probe_result)
            metadata_service.validate(metadata)

            # 5. Convert to 16kHz mono WAV
            audio_id = str(uuid.uuid4())
            out_path = ffmpeg_service.make_output_path(audio_id)
            ok = await ffmpeg_service.convert_to_wav(tmp_path, out_path)
            if not ok:
                raise CorruptedFileError()
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        # 6. Persist audio file record
        await self._audio_repo.create(
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
        )
        await self._audio_repo.mark_processed(audio_id, out_path)

        # 7. Forward to ASR Service
        transcription_id = None
        transcription_text = None
        try:
            wav_bytes = Path(out_path).read_bytes()
            resp = await self._http.post(
                f"{settings.asr_service_url}/internal/asr/transcribe",
                files={"file": (f"{audio_id}.wav", wav_bytes, "audio/wav")},
                data={
                    "user_id": user_id,
                    "audio_id": audio_id,
                    "audio_filename": file.filename or f"{audio_id}.{ext}",
                    "audio_duration": str(float(metadata.duration)),
                },
                timeout=300,  # Whisper can be slow
            )
            if resp.status_code == 200:
                data = resp.json()
                transcription_id = data.get("transcription_id")
                transcription_text = data.get("text")
        except Exception as exc:
            logger.error("ASR service call failed for audio_id=%s: %s", audio_id, exc)

        return AudioUploadResponse(
            audio_id=audio_id,
            processed_path=out_path,
            metadata=metadata,
            transcription_id=transcription_id,
            transcription_text=transcription_text,
        )
