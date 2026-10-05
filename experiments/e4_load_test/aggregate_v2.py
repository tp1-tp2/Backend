#!/usr/bin/env python
"""Aggregates E4 v2 repetitions per run label and user level.

Requests are grouped by the number of active users when they were issued
(the `users` column of the raw CSV), which is robust to step-boundary drift.
Per level and repetition: success %, goodput (successful req/s over the
180 s step), p50/p95 of successful responses, % fast rejections (503/429)
and their median time, % timeouts (504/connection) and % 5xx (500/502).
The table reports the MEDIAN across repetitions and the [min–max] range of
goodput. Async runs also get the job-completion summary (`*_jobs.json`).

    python aggregate_v2.py --labels S1-v1-cpu-sync S2-v2-cpu-sync S2c-v2-cpu-sync-edge --out ../results/e4v2_aggregate.md
"""
import argparse
import glob
import json
from pathlib import Path

import pandas as pd

RESULTS = Path(__file__).resolve().parents[1] / "results"
LEVELS = [10, 50, 100, 200, 500, 1000]


def per_rep(raw: Path, step_s: float) -> pd.DataFrame:
    d = pd.read_csv(raw, low_memory=False)
    t = d[d.name == "/api/v1/transcribe"].copy()
    if t.empty:  # async run: score the end-to-end job (submit -> done)
        t = d[d.name == "job_e2e"].copy()
    t["lvl"] = pd.cut(t.users, [0] + LEVELS, labels=LEVELS)
    t["st"] = t.status.map(lambda v: str(v).split(".")[0])
    rows = []
    for lvl, x in t.groupby("lvl", observed=True):
        n = len(x)
        ok = x[x.success == 1]
        rej = x[x.st.isin(["503", "429"])]
        rows.append({
            "users": int(lvl), "n": n,
            "success_pct": 100 * len(ok) / n,
            "goodput": len(ok) / step_s,
            "p50": ok.response_time_ms.median() / 1000 if len(ok) else float("nan"),
            "p95": ok.response_time_ms.quantile(0.95) / 1000 if len(ok) else float("nan"),
            "rejected_pct": 100 * len(rej) / n,
            "reject_p50": rej.response_time_ms.median() / 1000 if len(rej) else float("nan"),
            "timeout_pct": 100 * x.st.isin(["504", "0"]).sum() / n,
            "err5xx_pct": 100 * x.st.isin(["500", "502"]).sum() / n,
        })
    return pd.DataFrame(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", nargs="+", required=True)
    ap.add_argument("--step-seconds", type=float, default=180)
    ap.add_argument("--out", default=str(RESULTS / "e4v2_aggregate.md"))
    a = ap.parse_args()
    out = []
    for label in a.labels:
        raws = sorted(glob.glob(str(RESULTS / f"e4v2_{label}_r*_raw.csv")))
        if not raws:
            continue
        reps = pd.concat([per_rep(Path(r), a.step_seconds).assign(rep=i + 1) for i, r in enumerate(raws)])
        med = reps.groupby("users").median(numeric_only=True)
        gmin = reps.groupby("users").goodput.min()
        gmax = reps.groupby("users").goodput.max()
        out.append(f"### {label} (n = {len(raws)} repeticiones; mediana entre repeticiones)\n")
        out.append("| Usuarios | Éxito | Goodput req/s [mín–máx] | p50 OK (s) | p95 OK (s) | Rechazo 503 | Mediana rechazo (s) | Timeout / conexión | 5xx |")
        out.append("|---|---|---|---|---|---|---|---|---|")
        for u, r in med.iterrows():
            out.append(
                f"| {u} | {r.success_pct:.1f} % | {r.goodput:.2f} [{gmin[u]:.2f}–{gmax[u]:.2f}] | {r.p50:.1f} | "
                f"{r.p95:.1f} | {r.rejected_pct:.1f} % | "
                f"{'—' if pd.isna(r.reject_p50) else f'{r.reject_p50:.2f}'} | {r.timeout_pct:.1f} % | {r.err5xx_pct:.1f} % |"
            )
        jobs = sorted(glob.glob(str(RESULTS / f"e4v2_{label}_r*_jobs.json")))
        if jobs:
            out.append("\n| Repetición | Enviados | Aceptados | Aceptación | Procesados | Fallidos | Completitud |")
            out.append("|---|---|---|---|---|---|---|")
            for i, j in enumerate(jobs, 1):
                d = json.load(open(j, encoding="utf-8"))
                out.append(f"| r{i} | {d['submitted']} | {d['accepted']} | {100 * d['acceptance_rate']:.2f} % | "
                           f"{d['processed']} | {d['failed']} | {100 * d['completion_rate']:.1f} % |")
        out.append("")
    text = "\n".join(out)
    Path(a.out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
