"""Thin HTTP/WebSocket client against either the real stack's api-gateway
(default http://localhost:8000) or the monolith-baseline (http://localhost:8006)
— both expose the same relative paths (services/monolith-baseline/app/api/routes/
was deliberately built to mirror api-gateway's routes), so every experiment
script here just takes --base-url and works against whichever architecture.

No existing test in the repo mints a real usable JWT against a live stack
(services/api-gateway/tests/e2e/ mocks auth entirely) — this is genuinely new.
"""
import asyncio
import json
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional

import httpx
import websockets

_CHUNK_BYTES = 4096
_CHUNK_PACE_SECONDS = 0.05


def _ws_base_url(base_url: str) -> str:
    return base_url.replace("http://", "ws://").replace("https://", "wss://")


_ALREADY_REGISTERED_ERROR_CODES = {"VALIDATION_003", "USER_001"}  # user-service (real stack) vs. monolith-baseline


def register(base_url: str, email: str, password: str, full_name: str) -> None:
    """Idempotent-ish: "already registered" is treated as success. The real
    stack's user-service returns 400 + errorCode VALIDATION_003 for this (not
    409, as originally assumed here — caught by running this against a live
    stack); monolith-baseline's EmailAlreadyExistsError returns 409 + USER_001.
    Both are accepted.
    """
    resp = httpx.post(
        f"{base_url}/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
        timeout=30,
    )
    if resp.status_code in (200, 201):
        return
    if resp.status_code in (400, 409):
        error_code = (resp.json().get("detail") or {}).get("errorCode")
        if error_code in _ALREADY_REGISTERED_ERROR_CODES:
            return
    resp.raise_for_status()


def login(base_url: str, email: str, password: str) -> str:
    resp = httpx.post(f"{base_url}/api/v1/auth/login", json={"email": email, "password": password}, timeout=30)
    resp.raise_for_status()
    return resp.json()["token"]


def ensure_user(base_url: str, email: str, password: str, full_name: str = "Experiment User") -> str:
    register(base_url, email, password, full_name)
    return login(base_url, email, password)


def transcribe_file(base_url: str, token: str, audio_path: str, timeout: float = 300.0) -> dict:
    """POST /api/v1/transcribe, then normalize the result to always have
    text/processing_time/audio_duration/device_used/compute_type (+ wall_time_s,
    E2's RTF numerator).

    The two architectures answer this endpoint differently:
    - monolith-baseline (Phase 2) returns the full enriched shape directly
      (text, processing_time, device_used, compute_type all present).
    - the real stack's gateway proxies audio-processor's AudioUploadResponse
      instead (transcription_text, no processing_time/device_used/compute_type
      at all — those live in transcription-manager). Caught by actually running
      this against a live stack, not by reading the schemas — a GET to
      /api/v1/transcriptions/{id} is needed to fetch the enriched record.
    """
    path = Path(audio_path)
    t0 = time.perf_counter()
    with open(path, "rb") as f:
        resp = httpx.post(
            f"{base_url}/api/v1/transcribe",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (path.name, f, "application/octet-stream")},
            timeout=timeout,
        )
    wall_time_s = time.perf_counter() - t0
    resp.raise_for_status()
    data = resp.json()

    if "processing_time" not in data:
        transcription_id = data.get("transcription_id")
        if not transcription_id:
            raise RuntimeError(f"transcribe returned no transcription_id: {data}")
        # v2 persists the record in the background (off the response path), so
        # it can lag the response by a few ms — retry briefly on 404.
        for attempt in range(20):
            detail_resp = httpx.get(
                f"{base_url}/api/v1/transcriptions/{transcription_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30,
            )
            if detail_resp.status_code != 404:
                break
            time.sleep(0.1 * (attempt + 1))
        detail_resp.raise_for_status()
        data = detail_resp.json()

    data["wall_time_s"] = wall_time_s
    return data


def _encode_to(input_path: str, suffix: str) -> str:
    """ffmpeg-encode a WAV/whatever to .opus or .mp3, returns the temp path."""
    out_path = tempfile.mktemp(suffix=f".{suffix}")
    codec = {"opus": ["-c:a", "libopus"], "mp3": ["-c:a", "libmp3lame"]}[suffix]
    cmd = ["ffmpeg", "-y", "-i", input_path, *codec, out_path]
    subprocess.run(cmd, capture_output=True, check=True, timeout=60)
    return out_path


async def _stream_and_wait(
    ws_url: str, chunks: list[bytes], response_timeout: float
) -> tuple[dict, float, int]:
    t0 = time.perf_counter()
    bytes_sent = 0
    final_message: Optional[dict] = None

    async with websockets.connect(ws_url, max_size=None) as ws:
        for chunk in chunks:
            await ws.send(chunk)
            bytes_sent += len(chunk)
            await asyncio.sleep(_CHUNK_PACE_SECONDS)
        await ws.send("stop")

        deadline = time.perf_counter() + response_timeout
        while time.perf_counter() < deadline:
            remaining = deadline - time.perf_counter()
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
            except asyncio.TimeoutError:
                break
            message = json.loads(raw)
            if message.get("type") == "final":
                final_message = message
                break

    if final_message is None:
        raise TimeoutError(f"No final result received within {response_timeout}s")

    latency_s = time.perf_counter() - t0
    return final_message, latency_s, bytes_sent


def stream_pcm(base_url: str, token: str, audio_path: str, sample_rate: int = 16000, timeout: float = 300.0) -> dict:
    """Streams a clip as raw 16-bit mono PCM at `sample_rate` (resampling via
    ffmpeg first — manifest clips may be any format/rate). Returns the final
    message plus transmit_latency_s and bytes_sent for E5's comparison table.
    """
    wav_path = tempfile.mktemp(suffix=".wav")
    subprocess.run(
        ["ffmpeg", "-y", "-i", audio_path, "-ac", "1", "-ar", str(sample_rate), "-f", "s16le", wav_path],
        capture_output=True,
        check=True,
        timeout=60,
    )
    raw_pcm = Path(wav_path).read_bytes()
    Path(wav_path).unlink(missing_ok=True)

    chunks = [raw_pcm[i : i + _CHUNK_BYTES] for i in range(0, len(raw_pcm), _CHUNK_BYTES)]
    ws_url = f"{_ws_base_url(base_url)}/ws/stream?token={token}&sample_rate={sample_rate}&encoding=pcm"

    final_message, latency_s, bytes_sent = asyncio.run(_stream_and_wait(ws_url, chunks, timeout))
    return {**final_message, "transmit_latency_s": latency_s, "bytes_sent": bytes_sent}


def stream_encoded(base_url: str, token: str, audio_path: str, encoding: str, timeout: float = 300.0) -> dict:
    """Streams a clip pre-encoded to Opus or MP3 — the E5 comparison arm
    against stream_pcm(). See services/asr-service/app/services/codec_service.py
    for the server-side decode this exercises.
    """
    if encoding not in ("opus", "mp3"):
        raise ValueError("encoding must be 'opus' or 'mp3'")

    encoded_path = _encode_to(audio_path, encoding)
    try:
        compressed_bytes = Path(encoded_path).read_bytes()
    finally:
        Path(encoded_path).unlink(missing_ok=True)

    chunks = [compressed_bytes[i : i + _CHUNK_BYTES] for i in range(0, len(compressed_bytes), _CHUNK_BYTES)]
    ws_url = f"{_ws_base_url(base_url)}/ws/stream?token={token}&sample_rate=16000&encoding={encoding}"

    final_message, latency_s, bytes_sent = asyncio.run(_stream_and_wait(ws_url, chunks, timeout))
    return {**final_message, "transmit_latency_s": latency_s, "bytes_sent": bytes_sent}


def get_adaptation_status(asr_base_url: str) -> dict:
    """Direct call to asr-service's own /status/adaptation (not proxied through
    the gateway) — used by E2/E3 to confirm which device/compute_type served a
    batch of requests when not relying on per-response device_used stamping.
    """
    resp = httpx.get(f"{asr_base_url}/status/adaptation", timeout=10)
    resp.raise_for_status()
    return resp.json()


def unique_test_email(prefix: str = "exp") -> str:
    # example.com (RFC 2606) — not .local, which pydantic[email] rejects as a
    # reserved/special-use TLD (caught by running this against a live stack).
    return f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"
