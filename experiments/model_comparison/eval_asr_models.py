#!/usr/bin/env python
"""Runs one ASR model offline over a manifest and writes per-clip results
(hypothesis, WER, CER, processing time, RTF) — the same harness for every model,
so comparisons are paired over identical clips, audio preprocessing and text
normalization.

Models:
  whisper — replicates asr-service's production call exactly (whisper_service.py:
            WhisperTokenizer clean_up_tokenization_spaces=False, fp32, forced
            "spanish" language token, no_repeat_ngram_size=3, segment timestamps).
  xlsr    — a HuggingFace dir produced by convert_xlsr_fairseq_to_hf.py, greedy CTC.

Audio is loaded as mono float32 and resampled to 16 kHz (what audio-processor's
ffmpeg step guarantees in production). Threads default to 2 to mirror the
2-vCPU asr-service container on Azure, so RTF is comparable across models.

Usage:
    python eval_asr_models.py --model xlsr --model-path E:/asr-models/xls-r-cpt-qxp-silver-hf \
        --manifest ../e1_dataset_characterization/manifest_e5_sample.csv --out ../results/mc_xlsr_e5.csv
    # TSV manifests with path/sentence columns (e.g. QuechuaBase's OOD set):
    python eval_asr_models.py --model xlsr --model-path ... --manifest additional_data_qxp.tsv \
        --audio-dir .../wav --out ../results/mc_xlsr_ood.csv
"""
import argparse
import csv
import json
import sys
import time
from math import gcd
from pathlib import Path

import jiwer
import numpy as np
import soundfile as sf
import torch
from scipy.signal import resample_poly

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.text_norm import normalize  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from convert_xlsr_fairseq_to_hf import decode_ctc  # noqa: E402

SR = 16000
FIELDS = ["audio_path", "source", "duration_s", "reference", "hypothesis", "wer", "cer",
          "ref_words", "word_errors", "ref_chars", "char_errors", "proc_time_s", "rtf"]


def load_audio(path: str) -> np.ndarray:
    audio, sr = sf.read(path, dtype="float32", always_2d=True)
    audio = audio.mean(axis=1)
    if sr != SR:
        g = gcd(sr, SR)
        audio = resample_poly(audio, SR // g, sr // g).astype(np.float32)
    return audio


def read_manifest(path: str, audio_dir: str | None) -> list[dict]:
    delim = "\t" if path.endswith(".tsv") else ","
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=delim))
    out = []
    for r in rows:
        audio = r.get("audio_path") or r["path"]
        if audio_dir:
            audio = str(Path(audio_dir) / audio)
        out.append({
            "audio_path": audio,
            "reference": r.get("reference_text") or r.get("sentence") or "",
            "source": (r.get("source") or "").split(" (")[0],
        })
    return out


def build_whisper(model_path: str):
    from transformers import WhisperTokenizer, pipeline
    tok = WhisperTokenizer.from_pretrained(model_path, clean_up_tokenization_spaces=False)
    pipe = pipeline("automatic-speech-recognition", model=model_path, tokenizer=tok,
                    device=-1, torch_dtype=torch.float32)

    def transcribe(audio: np.ndarray) -> str:
        result = pipe({"array": audio, "sampling_rate": SR}, return_timestamps=True,
                      generate_kwargs={"language": "spanish", "task": "transcribe",
                                       "no_repeat_ngram_size": 3})
        return (result.get("text") or "").strip()
    return transcribe


def build_xlsr(model_path: str):
    from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForCTC
    model = Wav2Vec2ForCTC.from_pretrained(model_path).eval()
    fe = Wav2Vec2FeatureExtractor.from_pretrained(model_path)
    symbols = json.loads((Path(model_path) / "vocab_fairseq.json").read_text(encoding="utf-8"))

    def transcribe(audio: np.ndarray) -> str:
        inputs = fe(audio, sampling_rate=SR, return_tensors="pt")
        with torch.inference_mode():
            logits = model(inputs.input_values).logits[0]
        return decode_ctc(logits, symbols)
    return transcribe


def score(ref: str, hyp: str) -> dict:
    r, h = normalize(ref), normalize(hyp)
    ref_words, ref_chars = len(r.split()), len(r)
    if not r:
        return {"wer": float("nan"), "cer": float("nan"), "ref_words": 0, "word_errors": 0, "ref_chars": 0, "char_errors": 0}
    w = jiwer.process_words(r, h)
    c = jiwer.process_characters(r, h)
    word_errors = w.substitutions + w.deletions + w.insertions
    char_errors = c.substitutions + c.deletions + c.insertions
    return {"wer": word_errors / ref_words, "cer": char_errors / ref_chars, "ref_words": ref_words,
            "word_errors": word_errors, "ref_chars": ref_chars, "char_errors": char_errors}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", choices=["whisper", "xlsr"], required=True)
    ap.add_argument("--model-path", required=True, help="HF model id or local dir")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--audio-dir", default=None, help="prefix for relative paths (TSV manifests)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--threads", type=int, default=2)
    args = ap.parse_args()

    torch.set_num_threads(args.threads)
    rows = read_manifest(args.manifest, args.audio_dir)
    t0 = time.perf_counter()
    transcribe = build_whisper(args.model_path) if args.model == "whisper" else build_xlsr(args.model_path)
    print(f"Loaded {args.model} in {time.perf_counter() - t0:.1f}s | {len(rows)} clips | threads={args.threads}", flush=True)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for i, row in enumerate(rows, 1):
            audio = load_audio(row["audio_path"])
            duration = len(audio) / SR
            t = time.perf_counter()
            hyp = transcribe(audio)
            proc = time.perf_counter() - t
            s = score(row["reference"], hyp)
            writer.writerow({**row, "duration_s": round(duration, 3), "hypothesis": hyp, **s,
                             "proc_time_s": round(proc, 3), "rtf": round(proc / duration, 4)})
            f.flush()
            print(f"[{i}/{len(rows)}] WER={s['wer']:.3f} CER={s['cer']:.3f} RTF={proc / duration:.3f} {Path(row['audio_path']).name}", flush=True)
    print(f"Written {args.out}")


if __name__ == "__main__":
    main()
