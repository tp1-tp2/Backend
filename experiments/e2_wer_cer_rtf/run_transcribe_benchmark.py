#!/usr/bin/env python
"""E2 — ASR accuracy: WER / CER / RTF.

For each manifest clip x --repeats: calls POST /api/v1/transcribe, computes
WER/CER (jiwer) against the normalized reference text, and RTF = wall_time_s /
audio_duration. Every response is already stamped with device_used/compute_type
by asr-service (Phase 1) — no need to track which device served a request
manually, just read it back.

To get a clean single-device sample set, restart asr-service with
FORCE_DEVICE=cpu (or cuda) before running this — see docker-compose.yml's
FORCE_DEVICE env var. The script records whatever the server reports either way.

Usage:
    python run_transcribe_benchmark.py --manifest ../e1_dataset_characterization/manifest.csv \
        --base-url http://localhost:8000 --repeats 10 --out ../results/e2_raw.csv
"""
import argparse
import csv
import sys
import time
from pathlib import Path

import jiwer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.asr_client import ensure_user, transcribe_file, unique_test_email  # noqa: E402
from common.manifest import load  # noqa: E402
from common.text_norm import normalize  # noqa: E402

FIELDNAMES = [
    "audio_path", "source", "repeat_index", "wer", "cer", "rtf", "processing_time_s",
    "wall_time_s", "audio_duration_s", "device_used", "compute_type", "text",
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--repeats", type=int, default=10, help="E7 requires >=10 independent runs")
    parser.add_argument("--out", required=True)
    parser.add_argument("--email", default=None, help="Reuse an existing test account instead of creating one")
    parser.add_argument("--password", default="ExperimentPass123!")
    args = parser.parse_args()

    rows = load(args.manifest)
    email = args.email or unique_test_email("e2")
    token = ensure_user(args.base_url, email, args.password)
    print(f"Authenticated as {email} against {args.base_url}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()

        for row in rows:
            for repeat_index in range(args.repeats):
                t0 = time.perf_counter()
                result = transcribe_file(args.base_url, token, row.audio_path)
                elapsed = time.perf_counter() - t0

                hypothesis = normalize(result.get("text", ""))
                reference = normalize(row.reference_text)
                wer = jiwer.wer(reference, hypothesis) if reference else float("nan")
                cer = jiwer.cer(reference, hypothesis) if reference else float("nan")
                audio_duration = result.get("audio_duration", 0.0) or 1e-9
                rtf = result.get("processing_time", elapsed) / audio_duration

                writer.writerow({
                    "audio_path": row.audio_path,
                    "source": row.source,
                    "repeat_index": repeat_index,
                    "wer": wer,
                    "cer": cer,
                    "rtf": rtf,
                    "processing_time_s": result.get("processing_time"),
                    "wall_time_s": result.get("wall_time_s"),
                    "audio_duration_s": result.get("audio_duration"),
                    "device_used": result.get("device_used"),
                    "compute_type": result.get("compute_type"),
                    "text": result.get("text", ""),
                })
                f.flush()
                print(
                    f"[{Path(row.audio_path).name} #{repeat_index}] "
                    f"WER={wer:.3f} CER={cer:.3f} RTF={rtf:.3f} "
                    f"device={result.get('device_used')}/{result.get('compute_type')}"
                )

    print(f"\nRaw results written to {args.out} — run report.py to get the aggregated E7-compliant table.")


if __name__ == "__main__":
    main()
