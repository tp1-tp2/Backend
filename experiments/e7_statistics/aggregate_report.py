#!/usr/bin/env python
"""E7 — statistical rigor applies transversally, not as a separate experiment:
every report.py in e2/e4/e5/e6 already imports common/stats.py so their tables
carry 95% CI / hypothesis test / effect size columns. This script just stitches
whatever *_report.md files exist in --results-dir into one consolidated
document for the thesis appendix — run it last.

Usage:
    python aggregate_report.py --results-dir ../results --out ../results/full_report.md
"""
import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    report_files = sorted(results_dir.glob("*_report.md"))
    if not report_files:
        print(f"No *_report.md files found in {results_dir} — run the individual report.py scripts first.")
        return

    sections = ["# Consolidated Experimental Report\n"]
    for path in report_files:
        sections.append(path.read_text(encoding="utf-8"))
        sections.append("\n---\n")

    Path(args.out).write_text("\n".join(sections), encoding="utf-8")
    print(f"Consolidated {len(report_files)} report(s) into {args.out}")


if __name__ == "__main__":
    main()
