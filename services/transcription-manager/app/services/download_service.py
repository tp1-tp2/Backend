import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AccessDeniedError, TranscriptionNotFoundError, UnsupportedFormatError
from app.db.repositories import TranscriptionRepository, WordConfidenceRepository
from app.models.transcription import Transcription, WordConfidence

_SUPPORTED = {"txt", "json", "srt"}


def _srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def generate_txt(t: Transcription) -> str:
    lines = [
        "ASR Platform - Quechua Transcription",
        "=" * 37,
        f"Audio file:  {t.audio_filename}",
        f"Duration:    {float(t.audio_duration):.1f}s",
        f"Generated:   {datetime.now(timezone.utc).isoformat()}",
        f"User:        {t.user_id}",
        "",
        "TRANSCRIPTION:",
        "-" * 14,
        t.text or "(no transcription)",
    ]
    return "\n".join(lines)


def generate_json(t: Transcription, words: list[WordConfidence]) -> str:
    payload = {
        "userId": t.user_id,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "audioFilename": t.audio_filename,
        "audioDuration": float(t.audio_duration),
        "transcriptionText": t.text,
        "confidenceScores": [
            {
                "word": w.word,
                "confidence": float(w.confidence),
                "startTime": float(w.start_time),
                "endTime": float(w.end_time),
                "sequenceNumber": w.sequence_number,
            }
            for w in sorted(words, key=lambda x: x.sequence_number)
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def generate_srt(words: list[WordConfidence]) -> str:
    if not words:
        return "1\n00:00:00,000 --> 00:00:01,000\n(no transcription)\n"

    lines = []
    for i, w in enumerate(sorted(words, key=lambda x: x.sequence_number), start=1):
        start = _srt_time(float(w.start_time))
        end = _srt_time(float(w.end_time))
        lines.append(f"{i}\n{start} --> {end}\n{w.word}\n")
    return "\n".join(lines)


class DownloadService:
    def __init__(self, session: AsyncSession) -> None:
        self._trans = TranscriptionRepository(session)
        self._words = WordConfidenceRepository(session)

    async def get_file(
        self, transcription_id: str, user_id: str, fmt: str
    ) -> tuple[bytes, str, str]:
        fmt = fmt.lower()
        if fmt not in _SUPPORTED:
            raise UnsupportedFormatError()

        t = await self._trans.get_by_id(transcription_id)
        if not t:
            raise TranscriptionNotFoundError()
        if t.user_id != user_id:
            raise AccessDeniedError()

        words = await self._words.get_by_transcription(transcription_id)
        stem = t.audio_filename.rsplit(".", 1)[0] if "." in t.audio_filename else t.audio_filename

        if fmt == "txt":
            content = generate_txt(t).encode("utf-8")
            media_type = "text/plain; charset=utf-8"
            filename = f"{stem}.txt"
        elif fmt == "json":
            content = generate_json(t, words).encode("utf-8")
            media_type = "application/json"
            filename = f"{stem}.json"
        else:  # srt
            content = generate_srt(words).encode("utf-8")
            media_type = "text/srt; charset=utf-8"
            filename = f"{stem}.srt"

        return content, media_type, filename
