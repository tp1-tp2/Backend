#!/usr/bin/env python
"""E9 — Does the runtime adaptation mechanism actually adapt? (criterion C2.3)

v1 evidence: zero decisions in four E4 rounds, because the policy watched
CPU% while saturation appeared as queueing. v2 adapts on queue depth. This
experiment drives a controlled load profile straight at asr-service and
records, every second, what the mechanism sees and decides:

    idle (--idle-s) -> burst (--burst-s at --burst-concurrency) -> idle (--cooldown-s)

Measured:
- number of APPLIED decisions (changed=True), by axis (device / compute / batch)
- reaction time: burst start -> first applied decision
- reversion: whether it returns to the low-load state after the burst
- effect: throughput and latency before vs. after the first decision

Scenarios worth running (docs/10-experimentos-v2.md):
  A. GPU, adaptive: fp32/batch 8 at rest -> fp16 / batch 16 under the burst
  B. CPU only (FORCE_DEVICE=cpu): fp32 -> int8 under the burst
  C. CPU->GPU migration (RQ1): start with DEVICE=cpu on the GPU host,
     ADAPTIVE_MODE=true; the policy should migrate to cuda within ~15 s

Usage:
    python observe.py --label gpu-adaptive --audio clip.wav --burst-concurrency 24
"""
import argparse
import asyncio
import csv
import json
import time
import uuid
import wave
from pathlib import Path

import httpx


def _duration(path: str) -> float:
    try:
        with wave.open(path, "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except Exception:
        return 0.0


async def _poller(client, base, stop, timeline, t0):
    while not stop.is_set():
        try:
            st = (await client.get(f"{base}/status/adaptation", timeout=5)).json()
            cur = st.get("current", {})
            timeline.append({
                "t": round(time.time() - t0, 2),
                "device": cur.get("device"), "compute_type": cur.get("compute_type"),
                "batch_size": cur.get("batch_size"), "queue_depth": st.get("queue_depth"),
                "in_flight": st.get("in_flight_inferences"),
            })
        except Exception:
            pass
        await asyncio.sleep(1.0)


async def _load(client, base, audio, concurrency, until, results, t0):
    data = Path(audio).read_bytes()
    dur = _duration(audio)

    async def worker():
        while time.time() < until:
            s = time.perf_counter()
            try:
                r = await client.post(
                    f"{base}/internal/asr/transcribe",
                    files={"file": ("clip.wav", data, "audio/wav")},
                    data={"user_id": "e9", "audio_id": str(uuid.uuid4()),
                          "audio_filename": "clip.wav", "audio_duration": str(dur)},
                    timeout=600,
                )
                ok = r.status_code == 200
                body = r.json() if ok else {}
            except Exception:
                ok, body = False, {}
            results.append({
                "t_end": round(time.time() - t0, 2), "latency_s": round(time.perf_counter() - s, 3),
                "ok": ok, "device": body.get("device_used"), "compute_type": body.get("compute_type"),
            })

    await asyncio.gather(*[worker() for _ in range(concurrency)])


async def run(args):
    out_dir = Path(args.results_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    timeline, results = [], []
    stop = asyncio.Event()
    async with httpx.AsyncClient(limits=httpx.Limits(max_connections=args.burst_concurrency + 8)) as client:
        before = (await client.get(f"{args.base_url}/status/adaptation")).json()
        n_hist_before = len(before.get("recent_decisions", []))
        t0 = time.time()
        poller = asyncio.create_task(_poller(client, args.base_url, stop, timeline, t0))

        await asyncio.sleep(args.idle_s)
        burst_start = time.time() - t0
        await _load(client, args.base_url, args.audio, args.burst_concurrency,
                    time.time() + args.burst_s, results, t0)
        burst_end = time.time() - t0
        await asyncio.sleep(args.cooldown_s)
        stop.set()
        await poller
        after = (await client.get(f"{args.base_url}/status/adaptation")).json()

    decisions = after.get("recent_decisions", [])[n_hist_before:]
    applied = [d for d in decisions if d.get("changed")]

    def _rel(ts_iso):
        from datetime import datetime

        return round(datetime.fromisoformat(ts_iso).timestamp() - t0, 2)

    for d in decisions:
        d["t"] = _rel(d["timestamp"])
    first_applied = min((d["t"] for d in applied if d["t"] >= burst_start), default=None)
    axes = {
        "device": sum(1 for d in applied if d["previous_device"] != d["new_device"]),
        "compute_type": sum(1 for d in applied if d["previous_compute_type"] != d["new_compute_type"]),
        "batch_size": sum(1 for d in applied if d.get("previous_batch_size") != d.get("new_batch_size")),
    }
    final_state = timeline[-1] if timeline else {}
    start_state = timeline[0] if timeline else {}

    def _window_stats(lo, hi):
        sel = [r for r in results if lo <= r["t_end"] < hi]
        ok = [r for r in sel if r["ok"]]
        span = max(hi - lo, 1e-6)
        lat = sorted(r["latency_s"] for r in ok)
        return {"n": len(sel), "req_per_s": round(len(ok) / span, 3),
                "p50_s": lat[len(lat) // 2] if lat else None}

    summary = {
        "label": args.label,
        "burst": {"start_s": burst_start, "end_s": burst_end, "concurrency": args.burst_concurrency},
        "decisions_total": len(decisions),
        "decisions_applied": len(applied),
        "applied_by_axis": axes,
        "reaction_time_s": round(first_applied - burst_start, 2) if first_applied is not None else None,
        "state_at_start": start_state, "state_at_end": final_state,
        "reverted_after_burst": bool(start_state and final_state
                                     and start_state.get("compute_type") == final_state.get("compute_type")
                                     and start_state.get("batch_size") == final_state.get("batch_size")),
        "before_first_decision": _window_stats(burst_start, first_applied) if first_applied else None,
        "after_first_decision": _window_stats(first_applied, burst_end) if first_applied else None,
        "c2_3_met": len(applied) >= 1,
    }

    prefix = out_dir / f"e9_{args.label}"
    with open(prefix.with_suffix(".timeline.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(timeline[0].keys()) if timeline else ["t"])
        w.writeheader()
        w.writerows(timeline)
    prefix.with_suffix(".decisions.json").write_text(json.dumps(decisions, indent=2), encoding="utf-8")
    prefix.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--label", required=True)
    ap.add_argument("--base-url", default="http://127.0.0.1:8004")
    ap.add_argument("--audio", required=True)
    ap.add_argument("--idle-s", type=float, default=30)
    ap.add_argument("--burst-s", type=float, default=120)
    ap.add_argument("--cooldown-s", type=float, default=90)
    ap.add_argument("--burst-concurrency", type=int, default=24)
    ap.add_argument("--results-dir", default=str(Path(__file__).resolve().parents[1] / "results"))
    asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    main()
