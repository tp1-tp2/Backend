#!/usr/bin/env python
"""E6 — Fault injection.

During a moderate stable load (run e4_load_test/locustfile.py separately at
50-100 concurrent users first, per the protocol), this script:
  1. fires a steady stream of background requests against --target-url
  2. after --warmup-s, runs `docker stop <container>` on the named container
  3. samples /health on every URL in --monitor-health (the target AND its
     neighbors, to check whether the failure propagates or stays isolated)
     every second, until recovery or --max-wait-s elapses
  4. writes every request/health sample to CSV with a summary printed at the end

Repeat once per critical service (asr-service, auth-service,
transcription-manager — run separately, one container per run per the
protocol), and once against monolith-baseline (--target-url http://localhost:8006,
--container monolith-baseline) as the E3 fault-isolation comparison point —
there, the whole process should go down since everything shares one container.

Usage:
    python inject.py --container asr-service --target-url http://localhost:8000 \
        --monitor-health http://localhost:8000/health http://localhost:8001/health \
        --warmup-s 30 --max-wait-s 120 --out ../results/e6_asr_service.csv
"""
import argparse
import csv
import json
import subprocess
import threading
import time
from pathlib import Path

import httpx


def _check_health(url: str, timeout: float = 2.0) -> tuple[bool, int | None]:
    try:
        r = httpx.get(url, timeout=timeout)
        return r.status_code == 200, r.status_code
    except Exception:
        return False, None


def _background_requests(target_url: str, stop_event: threading.Event, out: list, interval: float = 1.0) -> None:
    while not stop_event.is_set():
        t0 = time.time()
        try:
            r = httpx.get(f"{target_url}/health", timeout=5.0)
            success, code = r.status_code == 200, r.status_code
        except Exception:
            success, code = False, None
        out.append({"timestamp": t0, "kind": "request", "url": target_url, "success": success, "status_code": code})
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--container", required=True, help="docker-compose service/container name to stop")
    parser.add_argument("--target-url", required=True, help="Base URL to fire background requests against")
    parser.add_argument("--monitor-health", nargs="+", required=True, help="Health-check URLs to watch (target + neighbors)")
    parser.add_argument("--warmup-s", type=float, default=30.0)
    parser.add_argument("--max-wait-s", type=float, default=180.0)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    samples: list[dict] = []
    stop_event = threading.Event()
    bg_thread = threading.Thread(
        target=_background_requests, args=(args.target_url, stop_event, samples), daemon=True
    )
    bg_thread.start()

    print(f"Warming up for {args.warmup_s}s before stopping '{args.container}'...")
    time.sleep(args.warmup_s)

    stop_time = time.time()
    print(f"[{stop_time:.0f}] docker stop {args.container}")
    subprocess.run(["docker", "stop", args.container], capture_output=True, check=True)

    detection_time = None
    recovery_time = None
    propagation = {url: False for url in args.monitor_health}
    deadline = stop_time + args.max_wait_s

    while time.time() < deadline:
        now = time.time()
        target_down = False
        for url in args.monitor_health:
            healthy, code = _check_health(url)
            samples.append({"timestamp": now, "kind": "health", "url": url, "success": healthy, "status_code": code})
            if not healthy:
                if url.startswith(args.target_url) or args.container in url:
                    target_down = True
                    if detection_time is None:
                        detection_time = now
                else:
                    propagation[url] = True

        if detection_time is not None and target_down is False and recovery_time is None:
            recovery_time = now
            print(f"[{now:.0f}] Recovery detected (target healthy again)")
            break

        time.sleep(1.0)

    stop_event.set()
    bg_thread.join(timeout=5)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "kind", "url", "success", "status_code"])
        writer.writeheader()
        writer.writerows(samples)

    requests_during_outage = [s for s in samples if s["kind"] == "request" and s["timestamp"] >= stop_time]
    lost = [s for s in requests_during_outage if not s["success"]]
    pct_lost = (len(lost) / len(requests_during_outage) * 100) if requests_during_outage else 0.0

    print("\n--- E6 Summary ---")
    print(f"Container stopped: {args.container} at t={stop_time:.0f}")
    print(f"Detection time: {detection_time - stop_time:.1f}s" if detection_time else "Detection time: never detected as down (?)")
    print(f"Recovery time: {recovery_time - stop_time:.1f}s since stop" if recovery_time else f"Recovery time: NOT recovered within {args.max_wait_s}s (container likely needs manual `docker start {args.container}`)")
    print(f"Requests lost during outage: {len(lost)}/{len(requests_during_outage)} ({pct_lost:.1f}%)")
    print(f"Propagation to other services: {propagation}")
    print(f"Raw samples written to {args.out}")

    if recovery_time is None:
        print(f"\nContainer was not observed to auto-restart. If your restart policy expects manual "
              f"recovery, run: docker start {args.container}")

    summary_path = Path(args.out).with_suffix(".summary.json")
    summary_path.write_text(json.dumps({
        "container": args.container,
        "target_url": args.target_url,
        "stop_time": stop_time,
        "detection_time_s": (detection_time - stop_time) if detection_time else None,
        "recovery_time_s": (recovery_time - stop_time) if recovery_time else None,
        "requests_during_outage": len(requests_during_outage),
        "requests_lost": len(lost),
        "pct_lost": pct_lost,
        "propagation": propagation,
    }, indent=2), encoding="utf-8")
    print(f"Summary written to {summary_path}")


if __name__ == "__main__":
    main()
