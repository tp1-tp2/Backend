#!/usr/bin/env python
"""E5 — Streaming: raw PCM vs. compressed formats.

For each E1 manifest clip, streams it twice over WebSocket to asr-service (via
the gateway or monolith-baseline): once as raw PCM 16-bit 16kHz (today's
config), once encoded as Opus (or MP3). Measures WER/CER, transmit+transcribe
latency, and bytes transmitted for both — this is the script that empirically
tests README.md's currently-unsubstantiated claim that compression induces
hallucination (see services/asr-service/app/services/codec_service.py, Phase 4).

Usage:
    python run_pcm_vs_compressed.py --manifest ../e1_dataset_characterization/manifest.csv \
        --base-url http://localhost:8000 --encoding opus --repeats 10 --out ../results/e5_raw.csv
"""
import argparse
import csv
import sys
from pathlib import Path

import jiwer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.asr_client import ensure_user, stream_encoded, stream_pcm, unique_test_email  # noqa: E402
from common.manifest import load  # noqa: E402
from common.text_norm import normalize  # noqa: E402

FIELDNAMES = [
    "audio_path", "repeat_index", "condition", "wer", "cer",
    "transmit_latency_s", "bytes_sent", "text",
]


def _score(reference: str, hypothesis: str) -> tuple[float, float]:
    ref, hyp = normalize(reference), normalize(hypothesis)
    if not ref:
        return float("nan"), float("nan")
    return jiwer.wer(ref, hyp), jiwer.cer(ref, hyp)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--encoding", choices=["opus", "mp3"], default="opus")
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--out", required=True)
    parser.add_argument("--email", default=None)
    parser.add_argument("--password", default="ExperimentPass123!")
    args = parser.parse_args()

    rows = load(args.manifest)
    email = args.email or unique_test_email("e5")
    token = ensure_user(args.base_url, email, args.password)
    print(f"Authenticated as {email} against {args.base_url}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()

        for row in rows:
            for repeat_index in range(args.repeats):
                for condition, stream_fn in [
                    ("pcm", lambda: stream_pcm(args.base_url, token, row.audio_path)),
                    (args.encoding, lambda: stream_encoded(args.base_url, token, row.audio_path, args.encoding)),
                ]:
                    result = stream_fn()
                    wer, cer = _score(row.reference_text, result.get("text", ""))
                    writer.writerow({
                        "audio_path": row.audio_path,
                        "repeat_index": repeat_index,
                        "condition": condition,
                        "wer": wer,
                        "cer": cer,
                        "transmit_latency_s": result.get("transmit_latency_s"),
                        "bytes_sent": result.get("bytes_sent"),
                        "text": result.get("text", ""),
                    })
                    f.flush()
                    print(
                        f"[{Path(row.audio_path).name} #{repeat_index} {condition}] "
                        f"WER={wer:.3f} CER={cer:.3f} bytes={result.get('bytes_sent')} "
                        f"latency={result.get('transmit_latency_s'):.2f}s"
                    )

    print(f"\nRaw results written to {args.out}")


if __name__ == "__main__":
    main()
