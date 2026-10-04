#!/usr/bin/env python
"""E8 — Inference throughput: device x precision x batch size x concurrency.

Answers the performance question the v1 protocol could not (no GPU): how much
inference throughput does the hardware + scheduler deliver, and at what
latency, as concurrency grows? It talks to asr-service DIRECTLY
(POST /internal/asr/transcribe, port 8004 in docker-compose) so gateway/auth/
ffmpeg do not confound the measurement — those are covered by E3/E4.

For each concurrency level c (closed loop: c requests always in flight) it
runs for --seconds-per-level and records every request. Between levels it
snapshots /status/scheduler to get the batch-size histogram actually achieved.

Run it once per configuration, restarting asr-service with the env vars that
define the configuration (see docs/10-experimentos-v2.md), e.g.:

    # baseline v1-equivalent: CPU, fp32, no batching
    FORCE_DEVICE=cpu FORCE_COMPUTE_TYPE=fp32 FORCE_BATCH_SIZE=1 ADAPTIVE_MODE=false \\
      docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d asr-service
    python bench.py --label cpu-fp32-b1 --audio clip.wav --levels 1 2 4 8 16

    FORCE_DEVICE=cuda FORCE_COMPUTE_TYPE=fp16 FORCE_BATCH_SIZE=8 ADAPTIVE_MODE=false ...
    python bench.py --label cuda-fp16-b8 --audio clip.wav --levels 1 2 4 8 16 32

With --manifest instead of --audio it cycles through real clips and keeps the
returned text, so report.py can confirm that a configuration does not change
WER (a CONTROL check that batching/fp16 are output-preserving — not a
recognition-quality evaluation).

Output: ../results/e8_<label>.csv (one row per request).
"""
import argparse
import asyncio
import csv
import itertools
import sys
import time
import uuid
import wave
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _duration(path: str) -> float:
    try:
        with wave.open(path, "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        return 0.0


async def _status(client: httpx.AsyncClient, base: str) -> dict:
    try:
        return (await client.get(f"{base}/status/scheduler", timeout=5)).json()
    except Exception:
        return {}


async def _one(client, base, clip, level, label, writer, lock):
    path, ref = clip
    data = Path(path).read_bytes()
    dur = _duration(path)
    t0 = time.perf_counter()
    status, text, device, compute, err = "", "", "", "", ""
    try:
        resp = await client.post(
            f"{base}/internal/asr/transcribe",
            files={"file": (Path(path).name, data, "audio/wav")},
            data={"user_id": "e8-bench", "audio_id": str(uuid.uuid4()),
                  "audio_filename": Path(path).name, "audio_duration": str(dur)},
            timeout=600,
        )
        status = resp.status_code
        if status == 200:
            body = resp.json()
            text = body.get("text", "")
            device, compute = body.get("device_used", ""), body.get("compute_type", "")
        else:
            err = resp.text[:120]
    except Exception as exc:
        err = type(exc).__name__
    latency = time.perf_counter() - t0
    async with lock:
        writer.writerow([label, level, round(time.time(), 3), path, round(dur, 3),
                         round(latency, 4), status, device, compute, text, ref, err])


async def run(args) -> None:
    if args.manifest:
        from common.manifest import load

        rows = load(args.manifest)[: args.max_clips]
        clips = [(r.audio_path, r.reference_text) for r in rows]
    else:
        clips = [(args.audio, "")]
    cycle = itertools.cycle(clips)

    out = Path(args.results_dir) / f"e8_{args.label}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    lock = asyncio.Lock()
    limits = httpx.Limits(max_connections=max(args.levels) + 8)
    async with httpx.AsyncClient(limits=limits) as client:
        before = await _status(client, args.base_url)
        print(f"[{args.label}] device={before.get('device')} compute={before.get('compute_type')}")
        # Warm-up (first CUDA call compiles kernels / allocates; not measured)
        warm = open(Path(args.results_dir) / "_e8_warmup.csv", "w", newline="")
        await asyncio.gather(*[
            _one(client, args.base_url, next(cycle), 0, "warmup", csv.writer(warm), lock)
            for _ in range(args.warmup)
        ])
        warm.close()

        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["label", "concurrency", "ts", "audio_path", "audio_s", "latency_s",
                        "status", "device_used", "compute_type", "text", "reference_text", "error"])
            batch_hist = {}
            for level in args.levels:
                snap0 = (await _status(client, args.base_url)).get("scheduler", {})
                deadline = time.perf_counter() + args.seconds_per_level

                async def worker():
                    while time.perf_counter() < deadline:
                        await _one(client, args.base_url, next(cycle), level, args.label, w, lock)

                await asyncio.gather(*[worker() for _ in range(level)])
                snap1 = (await _status(client, args.base_url)).get("scheduler", {})
                h0 = {int(k): v for k, v in (snap0.get("batch_size_histogram") or {}).items()}
                h1 = {int(k): v for k, v in (snap1.get("batch_size_histogram") or {}).items()}
                batch_hist[level] = {k: h1.get(k, 0) - h0.get(k, 0) for k in h1 if h1.get(k, 0) - h0.get(k, 0)}
                print(f"[{args.label}] concurrency={level} batches={batch_hist[level]}")
                f.flush()

    (Path(args.results_dir) / f"e8_{args.label}.batches.json").write_text(
        __import__("json").dumps({str(k): v for k, v in batch_hist.items()}, indent=2), encoding="utf-8"
    )
    print(f"Written {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--label", required=True)
    ap.add_argument("--base-url", default="http://localhost:8004")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--audio")
    src.add_argument("--manifest")
    ap.add_argument("--max-clips", type=int, default=200)
    ap.add_argument("--levels", type=int, nargs="+", default=[1, 2, 4, 8, 16, 32])
    ap.add_argument("--seconds-per-level", type=float, default=60)
    ap.add_argument("--warmup", type=int, default=3)
    ap.add_argument("--results-dir", default=str(Path(__file__).resolve().parents[1] / "results"))
    asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    main()
