import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path

from app.core.config import settings
from app.core.exceptions import CorruptedFileError

logger = logging.getLogger(__name__)

_FFPROBE = "ffprobe"
_FFMPEG = "ffmpeg"


async def probe(file_path: str) -> dict:
    """Run ffprobe and return a dict with audio stream info."""
    cmd = [
        _FFPROBE,
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        file_path,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    except FileNotFoundError:
        raise CorruptedFileError()
    except asyncio.TimeoutError:
        raise CorruptedFileError()

    if proc.returncode != 0:
        logger.warning("ffprobe failed: %s", stderr.decode())
        raise CorruptedFileError()

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        raise CorruptedFileError()

    # Extract first audio stream
    audio_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
    if not audio_streams:
        raise CorruptedFileError()

    stream = audio_streams[0]
    fmt = data.get("format", {})

    return {
        "format": fmt.get("format_name", "unknown"),
        "duration": float(fmt.get("duration", stream.get("duration", 0))),
        "sample_rate": int(stream.get("sample_rate", 0)),
        "channels": int(stream.get("channels", 1)),
        "bit_rate": int(fmt.get("bit_rate", stream.get("bit_rate", 0))),
        "codec": stream.get("codec_name"),
    }


async def convert_to_wav(input_path: str, output_path: str) -> bool:
    """Convert any audio file to 16kHz mono PCM WAV via ffmpeg."""
    cmd = [
        _FFMPEG,
        "-y",
        "-i", input_path,
        "-ac", "1",
        "-ar", str(settings.target_sample_rate),
        "-vn",
        output_path,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
    except (FileNotFoundError, asyncio.TimeoutError) as exc:
        logger.error("ffmpeg convert failed: %s", exc)
        return False

    if proc.returncode != 0:
        logger.warning("ffmpeg stderr: %s", stderr.decode())
        return False

    return True


def make_output_path(audio_id: str) -> str:
    """Return a deterministic local path for the processed WAV file."""
    out_dir = Path(tempfile.gettempdir()) / "asr_audio"
    out_dir.mkdir(parents=True, exist_ok=True)
    return str(out_dir / f"{audio_id}.wav")
