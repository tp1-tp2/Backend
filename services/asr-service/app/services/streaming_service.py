import asyncio
import logging
import os
import struct
import tempfile
import uuid
from datetime import datetime, timezone

from app.core.config import settings
from app.core.exceptions import CapacityReachedError
from app.schemas.transcription import (
    FinalResultMessage,
    PartialResultMessage,
    StreamingSession,
)
from app.services import whisper_service

logger = logging.getLogger(__name__)

# 16-bit mono PCM: 2 bytes per sample, regardless of sample rate
_BYTES_PER_SAMPLE = 2


def _write_wav(path: str, pcm_data: bytes, sample_rate: int) -> None:
    """Write raw 16-bit mono PCM data as a minimal WAV file at the given sample rate."""
    num_channels = 1
    bits = 16
    byte_rate = sample_rate * num_channels * bits // 8
    block_align = num_channels * bits // 8
    data_len = len(pcm_data)

    with open(path, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_len))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<IHHIIHH", 16, 1, num_channels, sample_rate, byte_rate, block_align, bits))
        f.write(b"data")
        f.write(struct.pack("<I", data_len))
        f.write(pcm_data)


class ConnectionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, StreamingSession] = {}
        self._buffers: dict[str, bytearray] = {}
        self._partial_buffers: dict[str, bytearray] = {}
        self._partial_running: dict[str, bool] = {}
        self._lock = asyncio.Lock()

    @property
    def connection_count(self) -> int:
        return len(self._sessions)

    async def connect(self, user_id: str, sample_rate: int = 16000) -> str:
        async with self._lock:
            if self.connection_count >= settings.max_concurrent_connections:
                raise CapacityReachedError()
            session_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            self._sessions[session_id] = StreamingSession(
                session_id=session_id,
                user_id=user_id,
                started_at=now,
                last_activity_at=now,
                sample_rate=sample_rate,
            )
            self._buffers[session_id] = bytearray()
            self._partial_buffers[session_id] = bytearray()
            self._partial_running[session_id] = False
            return session_id

    async def disconnect(self, session_id: str) -> None:
        async with self._lock:
            self._sessions.pop(session_id, None)
            self._buffers.pop(session_id, None)
            self._partial_buffers.pop(session_id, None)
            self._partial_running.pop(session_id, None)

    def _bytes_per_second(self, session_id: str) -> int:
        session = self._sessions.get(session_id)
        sample_rate = session.sample_rate if session else 16000
        return sample_rate * _BYTES_PER_SAMPLE

    def append_chunk(self, session_id: str, data: bytes) -> None:
        bytes_per_second = self._bytes_per_second(session_id)
        if session_id in self._buffers:
            max_bytes = settings.audio_buffer_max_seconds * bytes_per_second
            buf = self._buffers[session_id]
            buf.extend(data)
            # Trim to max window — keep the most recent audio. This buffer feeds
            # finalize(), so it keeps the full session context.
            if len(buf) > max_bytes:
                del buf[: len(buf) - max_bytes]
        if session_id in self._partial_buffers:
            partial_max_bytes = settings.partial_window_seconds * bytes_per_second
            pbuf = self._partial_buffers[session_id]
            pbuf.extend(data)
            # Much shorter window — this is what get_partial() re-transcribes on
            # every tick, so keeping it small keeps partials near real-time.
            if len(pbuf) > partial_max_bytes:
                del pbuf[: len(pbuf) - partial_max_bytes]
        if session_id in self._sessions:
            self._sessions[session_id].last_activity_at = datetime.now(timezone.utc)

    async def get_partial(self, session_id: str) -> PartialResultMessage | None:
        if not whisper_service.is_loaded():
            return None
        # Skip if a previous partial inference is still running in the thread pool.
        # asyncio.wait_for cancels the coroutine but NOT the executor thread, so
        # multiple concurrent Whisper inferences would pile up and OOM the container.
        if self._partial_running.get(session_id, False):
            return None
        buf = bytes(self._partial_buffers.get(session_id, b""))
        if not buf:
            return None

        self._partial_running[session_id] = True
        tmp_path = tempfile.mktemp(suffix=".wav")
        try:
            sample_rate = self._sessions.get(session_id).sample_rate if self._sessions.get(session_id) else 16000
            _write_wav(tmp_path, buf, sample_rate)
            loop = asyncio.get_event_loop()
            audio_duration = len(buf) / self._bytes_per_second(session_id)
            timeout = max(60.0, audio_duration * 10.0)
            result = await asyncio.wait_for(
                loop.run_in_executor(None, whisper_service._run_whisper, tmp_path),
                timeout=timeout,
            )
            text = (result.get("text") or "").strip()
        except Exception as exc:
            logger.debug("Partial transcription skipped: %s", exc)
            return None
        finally:
            self._partial_running[session_id] = False
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

        return PartialResultMessage(
            type="partial", text=text, timestamp=datetime.now(timezone.utc)
        )

    async def finalize(
        self, session_id: str, user_id: str, audio_id: str = ""
    ) -> FinalResultMessage | None:
        # Wait for any in-flight partial inference to finish before running the
        # final inference — two concurrent Whisper threads would double memory usage.
        waited = 0
        while self._partial_running.get(session_id, False) and waited < 300:
            await asyncio.sleep(1)
            waited += 1
        if waited:
            logger.info("[STREAM] Waited %ds for partial inference to finish before finalize", waited)

        buf = bytes(self._buffers.get(session_id, b""))
        session = self._sessions.get(session_id)
        if not buf or not whisper_service.is_loaded():
            return None

        duration = (
            (datetime.now(timezone.utc) - session.started_at).total_seconds()
            if session
            else 60.0
        )

        tmp_path = tempfile.mktemp(suffix=".wav")
        try:
            _write_wav(tmp_path, buf, session.sample_rate if session else 16000)
            result = await whisper_service.transcribe(
                audio_path=tmp_path,
                user_id=user_id,
                audio_id=audio_id or str(uuid.uuid4()),
                audio_filename="stream.wav",
                audio_duration=duration,
            )
        except Exception as exc:
            logger.error("Stream finalization failed: %s", exc)
            return None
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

        return FinalResultMessage(
            type="final",
            transcription_id=result.transcription_id,
            text=result.text,
            confidence_scores=result.confidence_scores,
            duration=result.audio_duration,
            timestamp=datetime.now(timezone.utc),
        )


manager = ConnectionManager()
