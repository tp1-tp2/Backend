#!/usr/bin/env python
"""E4 report — reads Locust's own --csv output (`<prefix>_stats_history.csv`)
plus docker_stats_sampler.py's CSV, and produces the latency/throughput table
per ramp step + a saturation-point CANDIDATE.

The saturation point heuristic here (first step where failure rate > 0, or p95
latency jumps >2x versus the running baseline) is a starting point, not a
verdict — the protocol explicitly asks for interpretation of what counts as
"degradation," which is a judgment call for the write-up, not something this
script settles on its own.

Usage:
    python report.py --locust-history ../results/e4_run_stats_history.csv \
        --docker-stats ../results/e4_docker_stats.csv --step-duration 180 \
        --out ../results/e4_report.md
"""
import argparse
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--locust-history", required=True)
    parser.add_argument("--docker-stats", default=None)
    parser.add_argument("--step-duration", type=float, default=180.0)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    df = pd.read_csv(args.locust_history)
    df.columns = [c.strip() for c in df.columns]
    t0 = df["Timestamp"].iloc[0]
    df["elapsed_s"] = df["Timestamp"] - t0
    df["step_index"] = (df["elapsed_s"] // args.step_duration).astype(int)

    lines = ["# E4 — Scalability Report", "", "| Step | Users | Requests/s | p50 (ms) | p95 (ms) | p99 (ms) | Error rate |", "|---|---|---|---|---|---|---|"]

    saturation_step = None
    prev_p95 = None
    # Error rate and throughput use the *cumulative* "Total Request/Failure
    # Count" columns, diffed against the previous step's cumulative value —
    # not the instantaneous "Requests/s"/"Failures/s" of whichever row
    # happens to be last inside the window. Those are a single 1s sample, so
    # a burst of failures mid-step (e.g. from a `docker stop` or a transient
    # gateway timeout) can land on a quiet second and get reported as 0%
    # even though real failures occurred somewhere in that 180s window.
    prev_cum_req, prev_cum_fail = 0, 0
    for step, group in df.groupby("step_index"):
        users = int(group["User Count"].iloc[-1])
        p50, p95, p99 = group["50%"].iloc[-1], group["95%"].iloc[-1], group["99%"].iloc[-1]
        cum_req = int(group["Total Request Count"].iloc[-1])
        cum_fail = int(group["Total Failure Count"].iloc[-1])
        step_elapsed_s = group["elapsed_s"].iloc[-1] - group["elapsed_s"].iloc[0]
        step_elapsed_s = step_elapsed_s if step_elapsed_s > 0 else args.step_duration

        delta_req = cum_req - prev_cum_req
        delta_fail = cum_fail - prev_cum_fail
        rps = delta_req / step_elapsed_s
        error_rate = delta_fail / delta_req if delta_req else 0.0
        prev_cum_req, prev_cum_fail = cum_req, cum_fail

        lines.append(f"| {step} | {users} | {rps:.1f} | {p50:.0f} | {p95:.0f} | {p99:.0f} | {error_rate:.1%} |")

        if saturation_step is None:
            if error_rate > 0:
                saturation_step = (step, users, "error rate > 0%")
            elif prev_p95 is not None and p95 > 2 * prev_p95:
                saturation_step = (step, users, f"p95 latency jumped {p95/prev_p95:.1f}x vs previous step")
        prev_p95 = p95

    lines.append("")
    if saturation_step:
        step, users, reason = saturation_step
        lines.append(f"## Saturation point (candidate)\n\nStep {step} (~{users} concurrent users): {reason}. "
                      f"**Review manually before citing in the paper** — this is a heuristic, not a verdict.")
    else:
        lines.append("## Saturation point\n\nNo saturation detected within the tested range — consider extending the ramp.")

    if args.docker_stats and Path(args.docker_stats).exists():
        ds = pd.read_csv(args.docker_stats)
        ds["cpu_percent"] = pd.to_numeric(ds["cpu_percent"], errors="coerce")
        lines.append("\n## CPU% by container (avg over the whole run)\n")
        lines.append(ds.groupby("container")["cpu_percent"].mean().round(1).to_markdown())

    output = "\n".join(lines)
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Written to {args.out}")
    else:
        print(output)


if __name__ == "__main__":
    main()
