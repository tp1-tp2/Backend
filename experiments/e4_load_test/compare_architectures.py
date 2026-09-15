#!/usr/bin/env python
"""E3 — Monolithic baseline vs. proposed architecture.

Reuses this same load suite (locustfile.py) — run it twice, once with
--host http://localhost:8000 (the real microservices stack) and once with
--host http://localhost:8006 (monolith-baseline, Phase 2), same hardware, same
model, same dataset. This script joins the two runs' Locust stats_history.csv
files and reports the latency/throughput comparison with a proper hypothesis
test + effect size (via common/stats.compare), matching E7's rigor requirement.

Usage:
    python compare_architectures.py \
        --proposed-history ../results/e4_proposed_stats_history.csv \
        --monolith-history ../results/e4_monolith_stats_history.csv \
        --out ../results/e3_report.md

Fault isolation (the other half of E3's table) comes from running
e6_fault_injection/inject.py against both --base-url targets — see that
script's docstring.
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.stats import compare  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposed-history", required=True)
    parser.add_argument("--monolith-history", required=True)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    proposed = pd.read_csv(args.proposed_history)
    monolith = pd.read_csv(args.monolith_history)
    proposed.columns = [c.strip() for c in proposed.columns]
    monolith.columns = [c.strip() for c in monolith.columns]

    lines = ["# E3 — Monolithic vs. Proposed Architecture", ""]
    lines += ["| Metric | Proposed (mean) | Monolith (mean) | Test | p-value | Effect size | Significant? |",
              "|---|---|---|---|---|---|---|"]

    for metric, col in [("p50 latency (ms)", "50%"), ("p95 latency (ms)", "95%"),
                         ("p99 latency (ms)", "99%"), ("Throughput (req/s)", "Requests/s")]:
        a, b = proposed[col].dropna().tolist(), monolith[col].dropna().tolist()
        if len(a) < 3 or len(b) < 3:
            lines.append(f"| {metric} | {sum(a)/len(a) if a else float('nan'):.1f} | "
                          f"{sum(b)/len(b) if b else float('nan'):.1f} | (n<3, skipped) | - | - | - |")
            continue
        result = compare(a, b)
        lines.append(
            f"| {metric} | {sum(a)/len(a):.1f} | {sum(b)/len(b):.1f} | {result.test_used} | "
            f"{result.p_value:.4f} | {result.effect_size_name}={result.effect_size:.3f} | "
            f"{'yes' if result.significant_at_05 else 'no'} |"
        )

    max_users_proposed = proposed["User Count"].max()
    max_users_monolith = monolith["User Count"].max()
    lines.append("")
    lines.append(f"- **Máx. usuarios concurrentes probados**: propuesta={max_users_proposed}, monolito={max_users_monolith}")
    lines.append("- **Aislamiento de fallos**: ver el reporte de `e6_fault_injection/` corrido contra ambas arquitecturas.")

    output = "\n".join(lines)
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Written to {args.out}")
    else:
        print(output)


if __name__ == "__main__":
    main()
