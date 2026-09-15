import asyncio
import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.core.config import settings
from app.core.exceptions import ModelUnavailableError, TranscriptionTimeoutError
from app.schemas.transcription import TranscribeResponse, WordConfidenceSchema

logger = logging.getLogger(__name__)

_pipe = None
_tokenizer = None
_current_device = settings.device
_current_compute_type = "fp32"
# Guards the _pipe/_current_* pointer swap only — never held during model
# construction, so a reload never blocks in-flight inference. See
# docs/01-adaptive-mechanism.md for the build-then-swap rationale.
_swap_lock = threading.Lock()


def _device_index(device: str) -> int:
    return 0 if device == "cuda" else -1  # transformers: 0=first GPU, -1=CPU


def _build_pipe(device: str, compute_type: str):
    """Blocking. Builds a fresh pipeline for (device, compute_type). Does NOT
    touch the module globals — the caller swaps them in atomically.
    """
    import logging as _logging

    import torch
    from transformers import WhisperTokenizer, pipeline

    global _tokenizer
    # Suppress cosmetic BPE tokenization and logits processor warnings
    _logging.getLogger("transformers").setLevel(_logging.ERROR)

    if _tokenizer is None:
        _tokenizer = WhisperTokenizer.from_pretrained(
            settings.model_id, clean_up_tokenization_spaces=False
        )

    torch_dtype = torch.float16 if compute_type == "fp16" else torch.float32
    logger.info(
        "Building model '%s' on device=%s compute_type=%s", settings.model_id, device, compute_type
    )
    pipe = pipeline(
        "automatic-speech-recognition",
        model=settings.model_id,
        tokenizer=_tokenizer,
        device=_device_index(device),
        torch_dtype=torch_dtype,
    )

    if compute_type == "int8":
        if device != "cpu":
            logger.warning(
                "int8 dynamic quantization only applies on CPU, ignoring for device=%s", device
            )
        else:
            pipe.model = torch.quantization.quantize_dynamic(
                pipe.model, {torch.nn.Linear}, dtype=torch.qint8
            )

    return pipe


def load_model(device: Optional[str] = None, compute_type: Optional[str] = None):
    """Load the model for the first time. Called once at process startup from
    main.py's lifespan. Subsequent runtime swaps go through reload_model(),
    called by device_manager.DeviceManager — not this function.
    """
    global _pipe, _current_device, _current_compute_type
    device = device or settings.device
    compute_type = compute_type or (settings.force_compute_type or "fp32")
    pipe = _build_pipe(device, compute_type)
    with _swap_lock:
        _pipe = pipe
        _current_device = device
        _current_compute_type = compute_type
    logger.info("Model loaded successfully (device=%s, compute_type=%s)", device, compute_type)
    return pipe


def reload_model(device: str, compute_type: str) -> None:
    """Build a new pipeline off the request hot path, then atomically swap it
    in. Blocking — call via run_in_executor. Any in-flight _run_whisper() call
    keeps using the pipe reference it already captured, unaffected by the swap.
    """
    global _pipe, _current_device, _current_compute_type
    new_pipe = _build_pipe(device, compute_type)
    with _swap_lock:
        old_pipe = _pipe
        _pipe = new_pipe
        _current_device = device
        _current_compute_type = compute_type
    del old_pipe
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass
    logger.info("Model swapped to device=%s compute_type=%s", device, compute_type)


def is_loaded() -> bool:
    return _pipe is not None


def get_current_device() -> str:
    return _current_device


def get_current_compute_type() -> str:
    return _current_compute_type


def _run_whisper(audio_path: str) -> dict:
    """Blocking call — must be run inside run_in_executor.

    Returns a dict with 'text' and 'segments' keys to stay compatible
    with streaming_service.py and _extract_words().
    """
    import soundfile as sf

    with _swap_lock:
        pipe = _pipe  # snapshot the current pipe; unaffected by a concurrent reload

    audio_array, sample_rate = sf.read(audio_path, dtype="float32")
    # return_timestamps=True gives segment-level timestamps from the generated
    # special tokens directly. return_timestamps="word" forces transformers to
    # additionally compute and keep cross-attention weights for every layer to
    # run DTW alignment, which spikes RAM by several GB even on short clips —
    # that was the cause of the asr-service OOM kills (exit code 137).
    # The fine-tuned checkpoint's generation_config defaults to "spanish" (Quechua
    # text was trained under the Spanish language token, there's no dedicated
    # Quechua token in Whisper's vocabulary). Without forcing it explicitly here,
    # the pipeline runs language auto-detection, which hallucinates into unrelated
    # languages (observed: Japanese) on ambiguous/quiet audio.
    result = pipe(
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
            words.append({
                "word": w,
                "probability": 1.0,  # transformers pipeline does not expose per-word confidence
                "start": w_start,
                "end": w_end,
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

    from app.services.device_manager import manager as device_manager

    loop = asyncio.get_event_loop()
    # CPU inference with transformers can take 60-180s on first call (warm-up).
    # Keep well below the audio-processor's 300s caller timeout.
    timeout = max(250.0, audio_duration * 15.0)
    t0 = datetime.now(timezone.utc)

    device_manager.inference_started()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, _run_whisper, audio_path),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        raise TranscriptionTimeoutError()
    finally:
        device_manager.inference_finished()

    # Stamp with whatever actually ran this inference (grabbed after it ran, so
    # it reflects the real pipe used, not a stale pre-call read).
    device_used = get_current_device()
    compute_type = get_current_compute_type()

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
                    # NOTE: this key previously said "word_confidences", which does not
                    # match CreateTranscriptionRequest.confidence_scores in
                    # transcription-manager — pydantic silently dropped it, so per-word
                    # confidences were never actually persisted. Fixed here.
                    "confidence_scores": [w.model_dump() for w in words],
                    "device_used": device_used,
                    "compute_type": compute_type,
                },
            )
    except Exception as exc:
        logger.error("Transcription Manager persist failed for %s: %s", transcription_id, exc)

    return TranscribeResponse(
        transcription_id=transcription_id,
        text=text,
        confidence_scores=words,
        processing_time=processing_time,
        audio_duration=audio_duration,
        device_used=device_used,
        compute_type=compute_type,
    )
