#!/usr/bin/env python
"""Aggregates E6 v2 repetitions (results/e6v2_<scenario>_r<k>.summary.json)
into one row per scenario: detection and MTTR (mean and range), success rate
before/during/after pooled over the repetitions (requests summed), failures
by status during the outage, neighbour propagation and lost async jobs.

    python aggregate_v2.py --out ../results/e6v2_aggregate.md
"""
import argparse
import glob
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

RESULTS = Path(__file__).resolve().parents[1] / "results"


def _pool(runs, window):
    req = sum(r[window]["requests"] for r in runs)
    ok = sum(r[window]["requests"] * (r[window]["success_rate"] or 0) for r in runs)
    return req, (ok / req if req else None)


def _stat(values):
    v = [x for x in values if x is not None]
    if not v:
        return "—"
    mean = sum(v) / len(v)
    return f"{mean:.1f} ({min(v):.1f}–{max(v):.1f})" if len(v) > 1 else f"{mean:.1f}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(RESULTS / "e6v2_aggregate.md"))
    a = ap.parse_args()
    groups = defaultdict(list)
    for f in sorted(glob.glob(str(RESULTS / "e6v2_*.summary.json"))):
        d = json.load(open(f, encoding="utf-8"))
        groups[re.sub(r"_r\d+$", "", d["scenario"])].append(d)

    lines = ["| Escenario | n | Detección (s) | MTTR (s) | Éxito antes | Éxito durante | Éxito después | "
             "Éxito global | Fallos durante | Propagación | Trabajos perdidos |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    rows = []
    for scen, runs in groups.items():
        fails = Counter()
        for r in runs:
            fails.update(r.get("during_failures_by_status") or {})
        cells = {w: _pool(runs, w) for w in ("before", "during", "after", "overall")}
        lost = [r.get("jobs_lost") for r in runs if r.get("jobs_lost") is not None]
        row = {
            "scenario": scen, "n": len(runs),
            "detection": _stat([r.get("detection_time_s") for r in runs]),
            "mttr": _stat([r.get("mttr_s") for r in runs]),
            **{w: cells[w] for w in cells},
            "fails": ", ".join(f"{k}×{v}" for k, v in sorted(fails.items())) or "—",
            "propagation": "Sí" if any(any(r["neighbour_degraded"].values()) for r in runs) else "No",
            "lost": sum(lost) if lost else "—",
        }
        rows.append(row)

        def pct(c):
            req, rate = c
            return f"{rate * 100:.1f} % ({req})" if rate is not None else "—"

        lines.append(
            f"| {scen} | {row['n']} | {row['detection']} | {row['mttr']} | {pct(cells['before'])} | "
            f"{pct(cells['during'])} | {pct(cells['after'])} | {pct(cells['overall'])} | {row['fails']} | "
            f"{row['propagation']} | {row['lost']} |"
        )
    text = "\n".join(lines) + "\n"
    Path(a.out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
