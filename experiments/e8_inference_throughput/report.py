#!/usr/bin/env python
"""E8 report — throughput/latency per configuration and concurrency, plus a
statistical comparison of each configuration against a baseline label.

    python report.py --csv ../results/e8_*.csv --baseline cpu-fp32-b1 \\
        --out ../results/e8_report.md

Per (label, concurrency): successful req/s, audio seconds processed per
second (throughput in real-time factor terms: 50 = fifty seconds of audio per
wall second), p50/p95 latency, error rate. "Speed-up" compares each label's
PEAK audio-s/s with the baseline's peak.

If the runs used --manifest (texts + references present), WER is computed per
label as an output-preservation control: a faster configuration is only an
improvement if it transcribes the same thing.
"""
import argparse
import glob
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.stats import compare  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", nargs="+", required=True)
    ap.add_argument("--baseline", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    files = [p for pattern in args.csv for p in glob.glob(pattern)]
    df = pd.concat([pd.read_csv(p, keep_default_na=False) for p in files], ignore_index=True)
    df["ok"] = df["status"].astype(str) == "200"

    rows = []
    for (label, level), g in df.groupby(["label", "concurrency"]):
        ok = g[g["ok"]]
        span = g["ts"].max() - (g["ts"] - g["latency_s"]).min()
        span = span if span > 0 else 1.0
        rows.append({
            "label": label, "concurrency": level, "requests": len(g),
            "req_per_s": len(ok) / span,
            "audio_s_per_s": ok["audio_s"].astype(float).sum() / span,
            "p50_s": float(np.percentile(ok["latency_s"], 50)) if len(ok) else np.nan,
            "p95_s": float(np.percentile(ok["latency_s"], 95)) if len(ok) else np.nan,
            "error_rate": 1 - len(ok) / len(g),
            "device": ",".join(sorted(set(ok["device_used"]) - {""})),
            "compute": ",".join(sorted(set(ok["compute_type"]) - {""})),
        })
    table = pd.DataFrame(rows).sort_values(["label", "concurrency"])

    out = ["# E8 — Inference throughput", ""]
    fmt = table.copy()
    for c in ("req_per_s", "audio_s_per_s", "p50_s", "p95_s"):
        fmt[c] = fmt[c].map(lambda v: f"{v:.2f}")
    fmt["error_rate"] = fmt["error_rate"].map(lambda v: f"{v:.1%}")
    out.append(fmt.to_markdown(index=False))

    peaks = table.groupby("label")["audio_s_per_s"].max()
    out += ["", "## Peak throughput per configuration", ""]
    base_peak = peaks.get(args.baseline) if args.baseline else None
    for label, peak in peaks.sort_values().items():
        speed = f" — **{peak / base_peak:.1f}x** vs `{args.baseline}`" if base_peak else ""
        out.append(f"- `{label}`: {peak:.1f} s of audio per second{speed}")

    if args.baseline and args.baseline in set(df["label"]):
        out += ["", f"## Latency at concurrency 1 vs `{args.baseline}` (single-request cost)", ""]
        base = df[(df["label"] == args.baseline) & (df["concurrency"] == 1) & df["ok"]]["latency_s"]
        for label in sorted(set(df["label"]) - {args.baseline}):
            other = df[(df["label"] == label) & (df["concurrency"] == 1) & df["ok"]]["latency_s"]
            if len(base) >= 3 and len(other) >= 3:
                c = compare(other.tolist(), base.tolist())
                out.append(f"- `{label}`: median {other.median():.3f}s vs {base.median():.3f}s — "
                           f"{c.test_used}, p={c.p_value:.4f}, {c.effect_size_name}={c.effect_size:.3f}")

    if (df["reference_text"].astype(str) != "").any():
        import jiwer

        from common.text_norm import normalize

        out += ["", "## Output-preservation control (WER per configuration)", ""]
        for label, g in df[df["ok"] & (df["reference_text"].astype(str) != "")].groupby("label"):
            refs = [normalize(r) for r in g["reference_text"]]
            hyps = [normalize(h) for h in g["text"]]
            pairs = [(r, h) for r, h in zip(refs, hyps) if r]
            wer = jiwer.wer([p[0] for p in pairs], [p[1] for p in pairs]) if pairs else float("nan")
            out.append(f"- `{label}`: corpus WER {wer:.3f} over {len(pairs)} transcriptions")

    text = "\n".join(out)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        table.to_csv(Path(args.out).with_suffix(".csv"), index=False)
        print(f"Written to {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
