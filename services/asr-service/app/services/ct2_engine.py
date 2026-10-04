"""CTranslate2 inference engine (faster-whisper) for the same fine-tuned model.

Why a second engine (docs/14-optimizacion-cpu.md): on the evaluation host
without an NVIDIA GPU, PyTorch's dynamic int8 quantization was measured 2x
SLOWER than fp32 (E8/E9 smoke tests), so the CPU path had no faster state to
adapt to. CTranslate2 runs the same Whisper weights (converted at image build
time, see Dockerfile) with an optimized CPU runtime and real int8 kernels, and
it can run several transcriptions in parallel (`num_workers`), which the
inference scheduler exposes as parallel "lanes".

Decoding is configured to match the transformers path (greedy, language token
"spanish", no_repeat_ngram_size=3, no previous-text conditioning, no
silence-based segment skipping) so the WER control in E8 compares engines, not
decoding strategies.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

# (device, platform compute_type) -> CTranslate2 compute_type
_CT2_TYPES = {
    ("cpu", "fp32"): "float32",
    ("cpu", "int8"): "int8",
    ("cuda", "fp32"): "float32",
    ("cuda", "fp16"): "float16",
    ("cuda", "int8"): "int8_float16",
}


def cpu_threads_per_lane(lanes: int, configured: int) -> int:
    if configured > 0:
        return configured
    return max(1, (os.cpu_count() or 1) // max(1, lanes))


class CT2Pipe:
    """Drop-in for the transformers pipeline object held in whisper_service._pipe."""

    engine = "ctranslate2"

    def __init__(self, model_dir: str, device: str, compute_type: str, lanes: int, cpu_threads: int):
        from faster_whisper import WhisperModel

        ct2_type = _CT2_TYPES.get((device, compute_type), "float32")
        threads = cpu_threads_per_lane(lanes, cpu_threads)
        logger.info(
            "Building CTranslate2 model from %s on device=%s compute_type=%s (lanes=%d, threads/lane=%d)",
            model_dir, device, ct2_type, lanes, threads,
        )
        self.model = WhisperModel(
            model_dir,
            device=device,
            compute_type=ct2_type,
            cpu_threads=threads,
            num_workers=max(1, lanes),
        )

        from faster_whisper.tokenizer import Tokenizer

        self._tok = Tokenizer(self.model.hf_tokenizer, True, task="transcribe", language="es")

    def transcribe(self, audio) -> dict:
        """Blocking; thread-safe across up to `lanes` concurrent callers."""
        if len(audio) <= _SHORT_FORM_SAMPLES:
            return self._short_form(audio)
        return self._long_form(audio)

    def _short_form(self, audio) -> dict:
        """One decoding pass over the single 30 s window, exactly like the
        transformers pipeline does for short-form audio. faster-whisper's
        transcribe() instead seeks to the last timestamp and decodes the tail
        of the window again, which on this model produced hallucinated
        continuations (E8 engine-parity check, docs/14)."""
        from faster_whisper.audio import pad_or_trim

        m, tok = self.model, self._tok
        features = pad_or_trim(m.feature_extractor(audio), 3000)  # 30 s of 10 ms frames
        result = m.model.generate(
            m.encode(features),
            [list(tok.sot_sequence)],  # timestamps on, as return_timestamps=True
            beam_size=1,
            no_repeat_ngram_size=3,
            max_length=448,
            suppress_blank=True,
            suppress_tokens=[-1],  # the generation_config set, stored in config.json
            max_initial_timestamp_index=50,  # 1.0 s, same as the HF generation_config
        )[0]
        tokens = result.sequences_ids[0]
        duration = len(audio) / 16000.0
        segments, current, start = [], [], 0.0
        for t in tokens:
            if t >= tok.timestamp_begin:
                ts = (t - tok.timestamp_begin) * 0.02
                if current:
                    segments.append((start, ts, tok.decode(current)))
                    current = []
                start = ts
            elif t < tok.eot:
                current.append(t)
        if current:
            segments.append((start, duration, tok.decode(current)))
        out = _assemble(segments)
        # Text from the whole token stream (as the pipeline decodes it), so a
        # segment boundary never inserts a space inside a word.
        out["text"] = tok.decode([t for t in tokens if t < tok.eot]).strip()
        return out

    def _long_form(self, audio) -> dict:
        segments, _info = self.model.transcribe(
            audio,
            language="es",
            task="transcribe",
            beam_size=1,
            best_of=1,
            temperature=0.0,
            no_repeat_ngram_size=3,
            condition_on_previous_text=False,
            # The transformers pipeline never drops a segment for looking like
            # silence; keep parity (and avoid empty transcriptions, C4.1).
            no_speech_threshold=None,
            log_prob_threshold=None,
            compression_ratio_threshold=None,
            vad_filter=False,
            without_timestamps=False,
        )
        # generator: decoding happens while iterating
        return _assemble((seg.start, seg.end, seg.text) for seg in segments)


_SHORT_FORM_SAMPLES = 30 * 16000


def _assemble(segments) -> dict:
    """(start, end, text) segments -> the {'text', 'segments'} shape of
    whisper_service._to_result (words spread evenly over their segment)."""
    texts, words = [], []
    for start, end, text in segments:
        seg_text = (text or "").strip()
        if not seg_text:
            continue
        texts.append(seg_text)
        seg_words = seg_text.split()
        span = (end - start) / len(seg_words) if end > start else 0.0
        for i, w in enumerate(seg_words):
            w_start = start + i * span
            words.append({
                "word": w,
                "probability": 1.0,  # parity with the transformers path
                "start": w_start,
                "end": w_start + span if span else end,
            })
    return {"text": " ".join(texts).strip(), "segments": [{"words": words}]}
