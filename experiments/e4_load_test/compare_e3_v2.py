#!/usr/bin/env python
"""E3 v2 — proposed architecture vs. monolith (same host, engine, precision
and inference lanes), from the per-request raw CSVs of run_v2_suite.py.

Per user level (requests grouped by active users, repetitions pooled):
success %, goodput (median over repetitions), p50/p95/p99 of SUCCESSFUL
responses, and a two-sample test on those response times (Shapiro-Wilk ->
t-test + Cohen's d, otherwise Mann-Whitney U + Cliff's delta; common/stats.py).
Response times can only be compared where both architectures complete
requests; above capacity the comparison is about how each one fails.

    python compare_e3_v2.py --out ../results/e3v2_report.md
"""
import argparse
import random
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
from aggregate_v2 import LEVELS  # noqa: E402
from common.stats import compare  # noqa: E402

RESULTS = HERE.parent / "results"


def load(label: str) -> pd.DataFrame:
    frames = []
    for i, raw in enumerate(sorted(RESULTS.glob(f"e3v2_{label}_r*_raw.csv")), 1):
        d = pd.read_csv(raw, low_memory=False)
        t = d[d.name == "/api/v1/transcribe"].copy()
        t["rep"] = i
        frames.append(t)
    t = pd.concat(frames)
    t["lvl"] = pd.cut(t.users, [0] + LEVELS, labels=LEVELS)
    t["st"] = t.status.map(lambda v: str(v).split(".")[0])
    return t


def magnitude(name: str, v: float) -> str:
    a = abs(v)
    if name == "cliffs_delta":
        return "despreciable" if a < 0.147 else "pequeño" if a < 0.33 else "mediano" if a < 0.474 else "grande"
    return "despreciable" if a < 0.2 else "pequeño" if a < 0.5 else "mediano" if a < 0.8 else "grande"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--step-seconds", type=float, default=180)
    ap.add_argument("--max-sample", type=int, default=2000, help="cap per group for Cliff's delta")
    ap.add_argument("--out", default=str(RESULTS / "e3v2_report.md"))
    a = ap.parse_args()
    p, m = load("proposed"), load("monolith")
    nrep_p, nrep_m = p.rep.nunique(), m.rep.nunique()
    rng = random.Random(0)
    lines = [f"# E3 v2 — propuesta (n={nrep_p}) frente a monolito (n={nrep_m})\n",
             "| Usuarios | Arquitectura | Solicitudes | Éxito | Goodput (mediana) | p50 | p95 | p99 | Fallos |",
             "|---|---|---|---|---|---|---|---|---|"]
    tests = ["\n| Usuarios | Prueba | Valor p | Tamaño de efecto | Magnitud | Mediana propuesta (s) | Mediana monolito (s) | Significativo |",
             "|---|---|---|---|---|---|---|---|"]
    for lvl in LEVELS:
        okt = {}
        for name, d in (("Propuesta", p), ("Monolito", m)):
            x = d[d.lvl == lvl]
            if x.empty:
                continue
            ok = x[x.success == 1]
            gp = ok.groupby("rep").size().reindex(range(1, d.rep.nunique() + 1), fill_value=0) / a.step_seconds
            rt = ok.response_time_ms / 1000
            fails = x[x.success != 1].st.value_counts()
            ftxt = ", ".join(f"{k}×{v}" for k, v in fails.head(3).items()) or "—"
            lines.append(f"| {lvl} | {name} | {len(x)} | {100 * len(ok) / len(x):.1f} % | {gp.median():.2f} | "
                         f"{rt.median():.1f} | {rt.quantile(.95):.1f} | {rt.quantile(.99):.1f} | {ftxt} |")
            okt[name] = list(rt)
        if len(okt.get("Propuesta", [])) >= 3 and len(okt.get("Monolito", [])) >= 3:
            sa = okt["Propuesta"] if len(okt["Propuesta"]) <= a.max_sample else rng.sample(okt["Propuesta"], a.max_sample)
            sb = okt["Monolito"] if len(okt["Monolito"]) <= a.max_sample else rng.sample(okt["Monolito"], a.max_sample)
            r = compare(sa, sb)
            tests.append(f"| {lvl} | {r.test_used} | {r.p_value:.4g} | {r.effect_size_name} = {r.effect_size:.3f} | "
                         f"{magnitude(r.effect_size_name, r.effect_size)} | {pd.Series(okt['Propuesta']).median():.1f} | "
                         f"{pd.Series(okt['Monolito']).median():.1f} | {'Sí' if r.significant_at_05 else 'No'} |")
    text = "\n".join(lines + tests) + "\n"
    Path(a.out).write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
