#!/usr/bin/env python
"""E8 control — engine parity: transformers vs CTranslate2 on the same clips.

Runs INSIDE the asr-service image (both engines and the converted model are
baked in), single-threaded caller, one clip at a time, so it isolates the
per-clip model cost of each engine/precision and checks that switching engine
does not change recognition (WER/CER against the reference, and against the
transformers output itself).

    docker run --rm -v <corpus>:/corpus -v <experiments>:/exp backend-asr-service \\
        python /exp/e8_inference_throughput/engine_parity.py \\
        --manifest /exp/e1_dataset_characterization/manifest_e5_sample.csv \\
        --path-map "E:\\IWSLT2026_Quechua_data=/corpus" --out /exp/results/e8_engine_parity.csv
"""
import argparse
import csv
import os
import sys
import time

sys.path.insert(0, "/app")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CONFIGS = [
    ("transformers", "fp32"),
    ("transformers", "int8"),
    ("ctranslate2", "fp32"),
    ("ctranslate2", "int8"),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--path-map", default="", help="WINPREFIX=/mount to rewrite manifest paths")
    ap.add_argument("--out", required=True)
    ap.add_argument("--configs", nargs="*", default=None, help="engine:compute, e.g. ctranslate2:int8")
    a = ap.parse_args()

    import jiwer

    from app.core.config import settings
    from app.services import whisper_service
    from common.text_norm import normalize

    src, _, dst = a.path_map.partition("=")
    rows = list(csv.DictReader(open(a.manifest, encoding="utf-8")))
    for r in rows:
        p = r["audio_path"]
        if src and p.startswith(src):
            p = dst + p[len(src):].replace("\\", "/")
        r["audio_path"] = p

    configs = CONFIGS if not a.configs else [tuple(c.split(":")) for c in a.configs]
    out = []
    for engine, compute in configs:
        settings.engine = engine
        settings.inference_lanes = 1
        whisper_service.load_model("cpu", compute)
        whisper_service._run_whisper(rows[0]["audio_path"])  # warm-up
        for r in rows:
            audio, sr = whisper_service._load_audio(r["audio_path"])
            dur = len(audio) / sr
            t0 = time.perf_counter()
            res = whisper_service._run_whisper(r["audio_path"])
            dt = time.perf_counter() - t0
            ref, hyp = normalize(r["reference_text"]), normalize(res["text"])
            out.append({
                "engine": engine, "compute_type": compute, "audio_path": r["audio_path"],
                "duration_s": round(dur, 3), "proc_s": round(dt, 4), "rtf": round(dt / dur, 4),
                "wer": round(jiwer.wer(ref, hyp), 4) if ref else "",
                "cer": round(jiwer.cer(ref, hyp), 4) if ref else "",
                "hypothesis": res["text"],
            })
        print(f"{engine}/{compute}: done", flush=True)

    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
