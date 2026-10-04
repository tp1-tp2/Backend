#!/usr/bin/env python
"""E4 v2 report — SLO-based capacity + Little's-law bound, from the raw
per-request CSV written by locustfile.py (E4_RAW_CSV).

Why a new report (docs/10-experimentos-v2.md):
- "Sustained users" in v1 was the user count of the last step reached, which
  says nothing about whether those users were being SERVED. v2 defines
  capacity as the largest step that meets the SLO: p95 <= --slo-p95-s AND
  error rate <= --max-error. That is the number to compare across
  configurations (C2.1) and against the target (C2.2).
- Exact per-step percentiles from raw samples (not Locust's 10 s windows).
- Failures broken down by type: fast rejections (429/503 = admission control
  working) vs. timeouts (504/connection) vs. auth (401) vs. "200 without a
  transcription" — the failure MODE matters as much as the rate.
- Little's law (closed system, N users with think time Z):
      X = N / (R + Z)  =>  N_max = X_max * (R_slo + Z)
  where X_max is the highest measured throughput of successful requests.
  This is the analytic ceiling on concurrent users the hardware can serve
  within the SLO — it shows whether a target such as 1000 users (C2.2) is
  physically reachable with the measured service rate, independent of the
  architecture.

Usage:
    python slo_report.py --raw ../results/e4_async_raw.csv --name job_e2e \\
        --step-seconds 180 --slo-p95-s 10 --max-error 0.05 --think-time-s 2 \\
        --out ../results/e4_async_slo.md
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def _classify(row) -> str:
    if row["success"]:
        return "ok"
    status = str(row["status"]).split(".")[0]
    err = str(row["error"])
    if status in ("429", "503"):
        return "rejected (429/503)"
    if status == "504" or "timeout" in err.lower():
        return "timeout (504)"
    if status == "401":
        return "auth (401)"
    if "no transcription" in err:
        return "200 without transcription"
    if "job failed" in err:
        return "job failed"
    if status in ("", "0", "nan") or "connection" in err.lower():
        return "connection error"
    return f"HTTP {status}"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", required=True)
    ap.add_argument("--name", default=None,
                    help="Request name to analyse (default: /api/v1/transcribe if present, else job_e2e)")
    ap.add_argument("--step-seconds", type=float, default=180.0)
    ap.add_argument("--warmup-s", type=float, default=30.0,
                    help="Ignore the first N s of every step (users still spawning)")
    ap.add_argument("--slo-p95-s", type=float, default=10.0)
    ap.add_argument("--max-error", type=float, default=0.05)
    ap.add_argument("--think-time-s", type=float, default=2.0, help="Mean Locust wait_time")
    ap.add_argument("--audio-seconds", type=float, default=None,
                    help="Duration of the sample clip, to report audio-seconds/s")
    ap.add_argument("--label", default="")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    df = pd.read_csv(args.raw)
    names = set(df["name"].unique())
    name = args.name or ("/api/v1/transcribe" if "/api/v1/transcribe" in names else "job_e2e")
    df = df[df["name"] == name].copy()
    if df.empty:
        raise SystemExit(f"No rows named {name!r} in {args.raw} (have: {sorted(names)})")

    df["success"] = df["success"].astype(int).astype(bool)
    t0 = df["ts"].min()
    df["elapsed"] = df["ts"] - t0
    df["step"] = (df["elapsed"] // args.step_seconds).astype(int)
    df["in_step_s"] = df["elapsed"] - df["step"] * args.step_seconds
    df["kind"] = df.apply(_classify, axis=1)
    steady = df[df["in_step_s"] >= args.warmup_s]

    rows = []
    for step, g in steady.groupby("step"):
        window = args.step_seconds - args.warmup_s
        ok = g[g["success"]]
        lat_ok = ok["response_time_ms"] / 1000.0
        users = int(pd.to_numeric(g["users"], errors="coerce").max() or 0)
        err = 1.0 - len(ok) / len(g) if len(g) else 0.0
        p50, p95, p99 = (np.percentile(lat_ok, [50, 95, 99]) if len(ok) else (np.nan,) * 3)
        rows.append({
            "step": step, "users": users, "requests": len(g),
            "goodput_rps": len(ok) / window,
            "p50_s": p50, "p95_s": p95, "p99_s": p99,
            "error_rate": err,
            "meets_slo": bool(len(ok)) and p95 <= args.slo_p95_s and err <= args.max_error,
        })
    table = pd.DataFrame(rows)

    breakdown = (
        steady.groupby(["step", "kind"]).size().unstack(fill_value=0)
        if not steady.empty else pd.DataFrame()
    )

    meeting = table[table["meets_slo"]]
    capacity = int(meeting["users"].max()) if not meeting.empty else 0
    x_max = float(table["goodput_rps"].max()) if not table.empty else 0.0
    little_n = x_max * (args.slo_p95_s + args.think_time_s)

    out = [f"# E4 v2 — SLO capacity report {('— ' + args.label) if args.label else ''}".rstrip(), ""]
    out.append(f"- Source: `{args.raw}` — request `{name}`")
    out.append(f"- SLO: p95 <= {args.slo_p95_s:g} s and error rate <= {args.max_error:.0%} "
               f"(first {args.warmup_s:g} s of each {args.step_seconds:g} s step excluded)")
    out.append("")
    fmt = table.copy()
    for c in ("p50_s", "p95_s", "p99_s"):
        fmt[c] = fmt[c].map(lambda v: f"{v:.2f}" if pd.notna(v) else "—")
    fmt["goodput_rps"] = fmt["goodput_rps"].map(lambda v: f"{v:.2f}")
    fmt["error_rate"] = fmt["error_rate"].map(lambda v: f"{v:.1%}")
    fmt["meets_slo"] = fmt["meets_slo"].map(lambda v: "yes" if v else "no")
    out.append(fmt.to_markdown(index=False))
    out.append("")
    out.append("## Failure breakdown per step (steady-state window)\n")
    out.append(breakdown.to_markdown() if not breakdown.empty else "_no data_")
    out.append("")
    out.append("## Capacity")
    out.append("")
    out.append(f"- **SLO capacity: {capacity} concurrent users** (largest step meeting the SLO)")
    out.append(f"- Peak goodput X_max: {x_max:.2f} successful req/s"
               + (f" = {x_max * args.audio_seconds:.1f} s of audio per second" if args.audio_seconds else ""))
    out.append(f"- Little's-law ceiling with this service rate: N_max = X_max * (R_slo + Z) = "
               f"{x_max:.2f} * ({args.slo_p95_s:g} + {args.think_time_s:g}) = **{little_n:.0f} users**")
    out.append("")
    out.append("Interpretation: if a target (e.g. C2.2 = 1000 users) exceeds N_max, no amount of "
               "request routing can meet it at this service rate — it requires more inference "
               "throughput (GPU, batching, more workers), or a relaxed SLO / async semantics.")

    text = "\n".join(out)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
        table.to_csv(Path(args.out).with_suffix(".csv"), index=False)
        print(f"Written to {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
