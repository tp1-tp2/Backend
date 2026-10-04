import asyncio
import logging
import tempfile
import uuid
from decimal import Decimal
from pathlib import Path

import httpx
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AsrUnavailableError,
    AsrTimeoutError,
    CorruptedFileError,
    FileSizeExceededError,
    UnsupportedFormatError,
)
from app.db.repositories import AudioRepository
from app.schemas.audio import AudioMetadata, AudioUploadResponse, JobAcceptedResponse
from app.services import ffmpeg_service, job_queue, metadata_service

logger = logging.getLogger(__name__)

_ALLOWED = set(settings.allowed_formats)


def _read_bytes(path: str) -> bytes:
    return Path(path).read_bytes()


class AudioService:
    def __init__(self, session: AsyncSession, http_client: httpx.AsyncClient) -> None:
        self._audio_repo = AudioRepository(session)
        self._http = http_client

    async def _ingest(
        self, file: UploadFile, user_id: str
    ) -> tuple[str, str, AudioMetadata, str]:
        """Validate, convert to 16 kHz mono WAV and register the audio file.
        Shared by the synchronous and the asynchronous (job) paths.
        Returns (audio_id, wav_path, metadata, display_filename)."""
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

        filename = file.filename or f"{audio_id}.{ext}"
        # 6. Persist audio file record
        await self._audio_repo.create(
            audio_id=audio_id,
            user_id=user_id,
            filename=filename,
            original_format=ext,
            file_size_bytes=len(content),
            duration_seconds=Decimal(str(round(metadata.duration, 2))),
            sample_rate=metadata.sample_rate,
            channels=metadata.channels,
            bit_rate=metadata.bit_rate,
            storage_path=out_path,
        )
        await self._audio_repo.mark_processed(audio_id, out_path)
        return audio_id, out_path, metadata, filename

    async def _post_to_asr(self, wav_bytes: bytes, form: dict) -> httpx.Response:
        """POST to asr-service. Retries ONLY connection failures (the request
        never reached a replica, so a retry cannot duplicate work) — e.g. a
        replica restarting or being replaced by the autoscaler."""
        delay = 0.25
        for attempt in range(settings.asr_connect_retries + 1):
            try:
                return await self._http.post(
                    f"{settings.asr_service_url}/internal/asr/transcribe",
                    files={"file": (f"{form['audio_id']}.wav", wav_bytes, "audio/wav")},
                    data=form,
                    timeout=settings.asr_timeout_seconds,
                )
            except httpx.ConnectError:
                if attempt >= settings.asr_connect_retries:
                    raise
                await asyncio.sleep(delay)
                delay *= 2
        raise AssertionError("unreachable")

    async def process_upload(
        self, file: UploadFile, user_id: str
    ) -> AudioUploadResponse:
        audio_id, out_path, metadata, filename = await self._ingest(file, user_id)

        # 7. Forward to ASR Service. Failures are PROPAGATED to the caller.
        # Previously any ASR error was swallowed and the client got a 200 with
        # transcription_id=null, which load tests counted as a success — that
        # inflated E6's success rate while asr-service was down.
        wav_bytes = _read_bytes(out_path)
        try:
            resp = await self._post_to_asr(
                wav_bytes,
                {
                    "user_id": user_id,
                    "audio_id": audio_id,
                    "audio_filename": filename,
                    "audio_duration": str(float(metadata.duration)),
                },
            )
        except httpx.TimeoutException as exc:
            logger.error("ASR timeout for audio_id=%s", audio_id)
            raise AsrTimeoutError() from exc
        except httpx.HTTPError as exc:
            logger.error("ASR service unreachable for audio_id=%s: %s", audio_id, exc)
            raise AsrUnavailableError() from exc

        if resp.status_code != 200:
            try:
                detail = resp.json().get("detail")
            except Exception:
                detail = None
            headers = {"Retry-After": resp.headers["retry-after"]} if "retry-after" in resp.headers else None
            raise HTTPException(
                status_code=resp.status_code,
                detail=detail or {"errorCode": "ASR_000", "message": "ASR service error"},
                headers=headers,
            )

        data = resp.json()
        return AudioUploadResponse(
            audio_id=audio_id,
            processed_path=out_path,
            metadata=metadata,
            transcription_id=data.get("transcription_id"),
            transcription_text=data.get("text"),
        )

    async def submit_job(self, file: UploadFile, user_id: str) -> JobAcceptedResponse:
        """Asynchronous path: validate + convert, then enqueue for the ASR
        workers and return immediately (202). See services/job_queue.py."""
        # Admission control BEFORE the ffmpeg work: reject fast if the backlog
        # is already beyond what the workers can drain in reasonable time.
        backlog = await job_queue.ensure_capacity()
        audio_id, out_path, metadata, filename = await self._ingest(file, user_id)
        job_id = await job_queue.enqueue(
            user_id=user_id,
            audio_id=audio_id,
            audio_filename=filename,
            audio_duration=float(metadata.duration),
            wav_bytes=_read_bytes(out_path),
        )
        return JobAcceptedResponse(
            job_id=job_id,
            audio_id=audio_id,
            status="queued",
            status_url=f"/api/v1/jobs/{job_id}",
            queue_backlog=backlog,
        )
