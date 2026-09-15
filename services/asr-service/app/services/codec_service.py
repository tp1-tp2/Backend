"""Decodes compressed streamed audio (Opus/MP3) to WAV before it reaches
Whisper. Modeled directly on
services/audio-processor/app/services/ffmpeg_service.py::convert_to_wav() —
same subprocess ffmpeg pattern, just named for its role here (streaming codec
decode, not upload conversion).

Only used by the E5 experimental path (services/asr-service/app/services/streaming_service.py
finalize(), when encoding != "pcm"). Raw PCM streaming (the default, and the
only path used by the real frontend) never touches this module.
"""
import asyncio
import logging

logger = logging.getLogger(__name__)

_FFMPEG = "ffmpeg"


async def decode_to_wav(input_path: str, output_path: str) -> bool:
    """Decode a compressed audio file (Opus, MP3, ...) to 16-bit mono WAV at
    the given path via ffmpeg. Returns False on any failure — caller decides
    how to surface that (this mirrors convert_to_wav()'s contract exactly).
    """
    cmd = [_FFMPEG, "-y", "-i", input_path, "-ac", "1", "-vn", output_path]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
    except (FileNotFoundError, asyncio.TimeoutError) as exc:
        logger.error("ffmpeg codec decode failed: %s", exc)
        return False

    if proc.returncode != 0:
        logger.warning("ffmpeg stderr (codec decode): %s", stderr.decode())
        return False

    return True
