#!/usr/bin/env python
"""E5 report — aggregates run_pcm_vs_compressed.py's raw CSV into the
"PCM vs. comprimido" table (WER/CER, latencia, tamaño), with a hypothesis test
+ effect size per E7.

Usage:
    python report.py --raw ../results/e5_raw.csv --out ../results/e5_report.md
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.stats import compare, summarize  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", required=True)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    df = pd.read_csv(args.raw)
    conditions = df["condition"].unique().tolist()
    pcm_condition = "pcm"
    other_condition = next(c for c in conditions if c != "pcm")

    lines = ["# E5 — Raw PCM vs. Compressed Streaming Report", ""]
    lines += ["| Condition | n | WER (mean±CI95) | CER (mean±CI95) | Latency s (mean±CI95) | Bytes sent (mean) |",
              "|---|---|---|---|---|---|"]

    for condition in [pcm_condition, other_condition]:
        group = df[df["condition"] == condition]
        wer_s = summarize(group["wer"].dropna().tolist())
        cer_s = summarize(group["cer"].dropna().tolist())
        lat_s = summarize(group["transmit_latency_s"].dropna().tolist())
        bytes_mean = group["bytes_sent"].mean()
        lines.append(
            f"| {condition} | {len(group)} | {wer_s.mean:.3f}±[{wer_s.ci95_low:.3f},{wer_s.ci95_high:.3f}] | "
            f"{cer_s.mean:.3f}±[{cer_s.ci95_low:.3f},{cer_s.ci95_high:.3f}] | "
            f"{lat_s.mean:.2f}±[{lat_s.ci95_low:.2f},{lat_s.ci95_high:.2f}] | {bytes_mean:.0f} |"
        )

    lines.append("")
    lines.append("## Hypothesis test (PCM vs. comprimido)")
    lines.append("")
    lines.append("| Metric | Test | p-value | Effect size | Significant at 0.05? |")
    lines.append("|---|---|---|---|---|")
    for metric, col in [("WER", "wer"), ("CER", "cer"), ("Latency", "transmit_latency_s")]:
        a = df[df["condition"] == pcm_condition][col].dropna().tolist()
        b = df[df["condition"] == other_condition][col].dropna().tolist()
        if len(a) < 3 or len(b) < 3:
            lines.append(f"| {metric} | (n<3, skipped) | - | - | - |")
            continue
        result = compare(a, b)
        lines.append(
            f"| {metric} | {result.test_used} | {result.p_value:.4f} | "
            f"{result.effect_size_name}={result.effect_size:.3f} | {'yes' if result.significant_at_05 else 'no'} |"
        )

    lines.append("")
    lines.append(
        "**Interpretación**: si WER/CER del canal comprimido son significativamente mayores "
        "(p<0.05, effect size no despreciable), la afirmación de alucinación por compresión "
        "queda soportada empíricamente. Si no, hay que corregir esa afirmación en el paper."
    )

    output = "\n".join(lines)
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Written to {args.out}")
    else:
        print(output)


if __name__ == "__main__":
    main()
