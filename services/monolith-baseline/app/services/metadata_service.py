"""Ported verbatim from services/audio-processor/app/services/metadata_service.py."""
from app.core.exceptions import CorruptedFileError, DurationExceededError, InvalidSampleRateError
from app.schemas.audio import AudioMetadata


def parse(probe_result: dict) -> AudioMetadata:
    try:
        return AudioMetadata(
            format=probe_result["format"],
            duration=probe_result["duration"],
            sampleRate=probe_result["sample_rate"],
            bitRate=probe_result["bit_rate"],
            channels=probe_result["channels"],
            codec=probe_result.get("codec"),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise CorruptedFileError() from exc


def validate(metadata: AudioMetadata) -> None:
    if not (8000 <= metadata.sample_rate <= 48000):
        raise InvalidSampleRateError()
    if metadata.duration > 3600 or metadata.duration <= 0:
        raise DurationExceededError()
