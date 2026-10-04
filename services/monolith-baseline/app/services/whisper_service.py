"""Ported from services/asr-service/app/services/whisper_service.py, WITHOUT
device_manager.py — the model loads once with settings.device (fixed for the
whole process) and never migrates. This is the deliberate contrast E3 measures
against asr-service's adaptive mechanism: same inference code path, no runtime
adaptation coupled to it.
"""
import asyncio
import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.core.exceptions import ModelUnavailableError, TranscriptionTimeoutError
from app.schemas.transcription import WordConfidenceSchema

logger = logging.getLogger(__name__)

_pipe = None


def load_model():
    global _pipe
    if settings.engine == "ctranslate2":
        from app.services.ct2_engine import CT2Pipe

        _pipe = CT2Pipe(
            settings.ct2_model_dir, settings.device, settings.compute_type,
            lanes=settings.inference_lanes, cpu_threads=settings.ct2_cpu_threads,
        )
        logger.info("CTranslate2 model loaded (fixed device=%s)", settings.device)
        return _pipe

    import logging as _logging

    from transformers import WhisperTokenizer, pipeline

    _logging.getLogger("transformers").setLevel(_logging.ERROR)
    device_index = 0 if settings.device == "cuda" else -1
    logger.info("Loading model '%s' on FIXED device '%s' (no adaptation)", settings.model_id, settings.device)
    tokenizer = WhisperTokenizer.from_pretrained(settings.model_id, clean_up_tokenization_spaces=False)
    _pipe = pipeline(
        "automatic-speech-recognition",
        model=settings.model_id,
        tokenizer=tokenizer,
        device=device_index,
    )
    logger.info("Model loaded successfully (fixed device=%s)", settings.device)
    return _pipe


def is_loaded() -> bool:
    return _pipe is not None


def _run_whisper(audio_path: str) -> dict:
    import soundfile as sf

    audio_array, sample_rate = sf.read(audio_path, dtype="float32")
    if getattr(_pipe, "engine", None) == "ctranslate2":
        if audio_array.ndim > 1:
            audio_array = audio_array.mean(axis=1)
        return _pipe.transcribe(audio_array)  # ffmpeg already wrote 16 kHz mono
    result = _pipe(
        {"array": audio_array, "sampling_rate": sample_rate},
        return_timestamps=True,
        generate_kwargs={
            "language": "spanish",
            "task": "transcribe",
            "no_repeat_ngram_size": 3,
        },
    )
    text = (result.get("text") or "").strip()
    chunks = result.get("chunks", [])

    words = []
    for chunk in chunks:
        ts = chunk.get("timestamp") or (0.0, 0.0)
        start = ts[0] if ts[0] is not None else 0.0
        end = ts[1] if ts[1] is not None else start
        chunk_words = (chunk.get("text") or "").strip().split()
        if not chunk_words:
            continue
        span = (end - start) / len(chunk_words) if end > start else 0.0
        for i, w in enumerate(chunk_words):
            w_start = start + i * span
            w_end = w_start + span if span else end
            words.append({"word": w, "probability": 1.0, "start": w_start, "end": w_end})

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


async def transcribe(audio_path: str, audio_duration: float) -> dict:
    """Returns {text, words, processing_time} — the caller (pipeline_service)
    persists directly, no cross-service POST needed in a single process.
    """
    if not is_loaded():
        raise ModelUnavailableError()

    loop = asyncio.get_event_loop()
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

    return {"text": text, "words": words, "processing_time": processing_time}
