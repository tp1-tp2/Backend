#!/usr/bin/env python
"""E2 report — aggregates run_transcribe_benchmark.py's raw CSV into the
WER/CER/RTF table the paper needs (mean ± 95% CI, split by device_used per E2's
"RTF promedio en CPU y en GPU por separado" requirement).

Usage:
    python report.py --raw ../results/e2_raw.csv --out ../results/e2_report.md
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.stats import summarize  # noqa: E402


def _row_for(label: str, values: pd.Series) -> str:
    s = summarize(values.dropna().tolist())
    basis = "mean±CI95" if s.is_normal else "median±IQR (non-normal, Shapiro p={:.3f})".format(s.shapiro_p)
    if s.is_normal:
        return f"| {label} | {s.n} | {s.mean:.3f} | [{s.ci95_low:.3f}, {s.ci95_high:.3f}] | {basis} |"
    return f"| {label} | {s.n} | {s.median:.3f} | [{s.iqr_low:.3f}, {s.iqr_high:.3f}] | {basis} |"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", required=True)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    df = pd.read_csv(args.raw)
    lines = ["# E2 — WER / CER / RTF Report", ""]

    lines += ["## Overall", "", "| Metric | n | value | interval | basis |", "|---|---|---|---|---|"]
    lines.append(_row_for("WER", df["wer"]))
    lines.append(_row_for("CER", df["cer"]))
    lines.append(_row_for("RTF", df["rtf"]))
    lines.append("")

    lines += ["## RTF por dispositivo", "", "| Device / compute_type | n | value | interval | basis |", "|---|---|---|---|---|"]
    for (device, compute_type), group in df.groupby(["device_used", "compute_type"]):
        if len(group) < 2:
            lines.append(f"| {device}/{compute_type} | {len(group)} | (n<2, no CI) | - | - |")
            continue
        lines.append(_row_for(f"{device}/{compute_type}", group["rtf"]))
    lines.append("")

    lines += ["## WER por duración de clip (bucketed)", ""]
    df["duration_bucket"] = pd.cut(df["audio_duration_s"], bins=[0, 5, 15, 30, 60, 1e9],
                                    labels=["0-5s", "5-15s", "15-30s", "30-60s", "60s+"])
    bucket_stats = df.groupby("duration_bucket", observed=True)["wer"].agg(["count", "mean"])
    lines.append(bucket_stats.to_markdown())

    output = "\n".join(lines)
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Written to {args.out}")
    else:
        print(output)


if __name__ == "__main__":
    main()
