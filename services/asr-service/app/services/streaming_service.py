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


def _write_wav(path: str, pcm_data: bytes) -> None:
    """Write raw 16kHz 16-bit mono PCM data as a minimal WAV file."""
    sample_rate = 16000
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
        self._lock = asyncio.Lock()

    @property
    def connection_count(self) -> int:
        return len(self._sessions)

    async def connect(self, user_id: str) -> str:
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
            )
            self._buffers[session_id] = bytearray()
            return session_id

    async def disconnect(self, session_id: str) -> None:
        async with self._lock:
            self._sessions.pop(session_id, None)
            self._buffers.pop(session_id, None)

    def append_chunk(self, session_id: str, data: bytes) -> None:
        if session_id in self._buffers:
            self._buffers[session_id].extend(data)
        if session_id in self._sessions:
            self._sessions[session_id].last_activity_at = datetime.now(timezone.utc)

    async def get_partial(self, session_id: str) -> PartialResultMessage | None:
        if not whisper_service.is_loaded():
            return None
        buf = bytes(self._buffers.get(session_id, b""))
        if not buf:
            return None

        tmp_path = tempfile.mktemp(suffix=".wav")
        try:
            _write_wav(tmp_path, buf)
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, whisper_service._run_whisper, tmp_path),
                timeout=10.0,
            )
            text = (result.get("text") or "").strip()
        except Exception as exc:
            logger.debug("Partial transcription skipped: %s", exc)
            return None
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

        return PartialResultMessage(
            type="partial", text=text, timestamp=datetime.now(timezone.utc)
        )

    async def finalize(
        self, session_id: str, user_id: str, audio_id: str = ""
    ) -> FinalResultMessage | None:
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
            _write_wav(tmp_path, buf)
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
            timestamp=datetime.now(timezone.utc),
        )


manager = ConnectionManager()
