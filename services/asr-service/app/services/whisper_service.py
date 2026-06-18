import asyncio
import logging
import uuid
from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.core.exceptions import ModelUnavailableError, TranscriptionTimeoutError
from app.schemas.transcription import TranscribeResponse, WordConfidenceSchema

logger = logging.getLogger(__name__)

_pipe = None


def load_model():
    """Load the fine-tuned Quechua Whisper model via transformers pipeline."""
    import logging as _logging
    from transformers import pipeline, WhisperTokenizer
    global _pipe
    # Suppress cosmetic BPE tokenization and logits processor warnings
    _logging.getLogger("transformers").setLevel(_logging.ERROR)
    device = 0 if settings.device == "cuda" else -1  # transformers: 0=first GPU, -1=CPU
    logger.info("Loading model '%s' on device '%s'", settings.model_id, settings.device)
    tokenizer = WhisperTokenizer.from_pretrained(
        settings.model_id, clean_up_tokenization_spaces=False
    )
    _pipe = pipeline(
        "automatic-speech-recognition",
        model=settings.model_id,
        tokenizer=tokenizer,
        return_timestamps="word",
        device=device,
    )
    logger.info("Model loaded successfully")
    return _pipe


def is_loaded() -> bool:
    return _pipe is not None


def _run_whisper(audio_path: str) -> dict:
    """Blocking call — must be run inside run_in_executor.

    Returns a dict with 'text' and 'segments' keys to stay compatible
    with streaming_service.py and _extract_words().
    """
    import soundfile as sf
    audio_array, sample_rate = sf.read(audio_path, dtype="float32")
    # Pipeline accepts {"array": np.ndarray, "sampling_rate": int} — no ffmpeg needed
    result = _pipe({"array": audio_array, "sampling_rate": sample_rate}, return_timestamps="word")
    text = (result.get("text") or "").strip()
    chunks = result.get("chunks", [])

    words = []
    for chunk in chunks:
        ts = chunk.get("timestamp") or (0.0, 0.0)
        start = ts[0] if ts[0] is not None else 0.0
        end = ts[1] if ts[1] is not None else start
        words.append({
            "word": (chunk.get("text") or "").strip(),
            "probability": 1.0,  # transformers pipeline does not expose per-word confidence
            "start": start,
            "end": end,
        })

    return {"text": text, "segments": [{"words": words}]}


def _extract_words(segments: list) -> list[WordConfidenceSchema]:
    words = []
    seq = 0
    for segment in segments:
        for w in segment.get("words", []):
            word_text = w.get("word", "").strip()
            if not word_text:
                continue
            words.append(
                WordConfidenceSchema(
                    word=word_text,
                    confidence=float(w.get("probability", 1.0)),
                    start_time=float(w.get("start", 0.0)),
                    end_time=float(w.get("end", 0.0)),
                    sequence_number=seq,
                )
            )
            seq += 1
    return words


async def transcribe(
    audio_path: str,
    user_id: str,
    audio_id: str,
    audio_filename: str,
    audio_duration: float,
) -> TranscribeResponse:
    if not is_loaded():
        raise ModelUnavailableError()

    loop = asyncio.get_event_loop()
    # CPU inference with transformers can take 60-180s on first call (warm-up).
    # Keep well below the audio-processor's 300s caller timeout.
    timeout = max(250.0, audio_duration * 15.0)
    t0 = datetime.now(timezone.utc)

    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, _run_whisper, audio_path),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        raise TranscriptionTimeoutError()

    processing_time = (datetime.now(timezone.utc) - t0).total_seconds()
    text = (result.get("text") or "").strip()
    words = _extract_words(result.get("segments", []))
    transcription_id = str(uuid.uuid4())

    # Persist via Transcription Manager (non-fatal on failure)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            await client.post(
                f"{settings.transcription_manager_url}/internal/transcriptions",
                json={
                    "transcription_id": transcription_id,
                    "user_id": user_id,
                    "audio_id": audio_id,
                    "text": text,
                    "audio_filename": audio_filename,
                    "audio_duration": audio_duration,
                    "processing_time": processing_time,
                    "word_confidences": [w.model_dump() for w in words],
                },
            )
    except Exception as exc:
        logger.error("Transcription Manager persist failed for %s: %s", transcription_id, exc)

    return TranscribeResponse(
        transcription_id=transcription_id,
        text=text,
        confidence_scores=words,
        processing_time=processing_time,
    )
