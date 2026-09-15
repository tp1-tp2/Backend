#!/usr/bin/env python
"""Samples `docker stats` for the given containers every --interval seconds
and writes CPU%/memory to CSV — run this alongside locustfile.py (E4's
protocol text names "Azure Container Apps metrics or docker stats" as the
CPU/RAM source; this covers the local docker-compose case. For a live Azure
run, pull the equivalent from `az monitor metrics list` instead — not
scripted here, it needs a subscription and has real query cost).

Usage:
    python docker_stats_sampler.py --containers asr-service api-gateway audio-processor \
        --interval 5 --out ../results/e4_docker_stats.csv
    # Ctrl+C to stop, or --duration 1200 to auto-stop after N seconds.
"""
import argparse
import csv
import subprocess
import time
from pathlib import Path


def _sample(containers: list[str]) -> list[dict]:
    out = subprocess.run(
        ["docker", "stats", "--no-stream", "--format",
         "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}}", *containers],
        capture_output=True, text=True, timeout=15,
    )
    rows = []
    ts = time.time()
    for line in out.stdout.strip().splitlines():
        parts = line.split(",")
        if len(parts) != 4:
            continue
        name, cpu_perc, mem_usage, mem_perc = parts
        rows.append({
            "timestamp": ts,
            "container": name,
            "cpu_percent": cpu_perc.rstrip("%"),
            "mem_usage": mem_usage,
            "mem_percent": mem_perc.rstrip("%"),
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--containers", nargs="+", required=True)
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--duration", type=float, default=None, help="Seconds; omit to run until Ctrl+C")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    start = time.time()
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["timestamp", "container", "cpu_percent", "mem_usage", "mem_percent"])
        writer.writeheader()
        try:
            while args.duration is None or (time.time() - start) < args.duration:
                for row in _sample(args.containers):
                    writer.writerow(row)
                f.flush()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            pass

    print(f"Stopped. Samples written to {args.out}")


if __name__ == "__main__":
    main()
