import json

from app.core.exceptions import CorruptedFileError, InvalidSampleRateError, DurationExceededError
from app.schemas.audio import AudioMetadata


def parse(probe_result: dict) -> AudioMetadata:
    """Convert raw ffprobe dict → AudioMetadata with validation."""
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
    """Raise the appropriate HTTP error if metadata is out of range."""
    if not (8000 <= metadata.sample_rate <= 48000):
        raise InvalidSampleRateError()
    if metadata.duration > 3600 or metadata.duration <= 0:
        raise DurationExceededError()


def format_json(metadata: AudioMetadata) -> str:
    """Serialize metadata to JSON using camelCase field aliases."""
    return metadata.model_dump_json(by_alias=True)
