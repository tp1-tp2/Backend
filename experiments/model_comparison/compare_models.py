#!/usr/bin/env python
"""Paired comparison of two eval_asr_models.py result CSVs over the same clips.

Reports corpus-level WER/CER (total errors / total reference units — the figure
papers usually quote), per-clip median [IQR], a Wilcoxon signed-rank test on
per-clip WER/CER (paired: same clips, so Mann-Whitney U would be the wrong test),
matched-pairs rank-biserial correlation as effect size, win/tie/loss counts,
per-source breakdown and RTF.

Usage:
    python compare_models.py --a ../results/mc_whisper_e5.csv --a-name whisper-base \
        --b ../results/mc_xlsr_e5.csv --b-name xls-r-cpt --out ../results/mc_report_e5.md
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata, wilcoxon


def corpus_rates(d: pd.DataFrame) -> tuple[float, float]:
    return d.word_errors.sum() / d.ref_words.sum(), d.char_errors.sum() / d.ref_chars.sum()


def med_iqr(s: pd.Series) -> str:
    return f"{s.median():.3f} [{s.quantile(.25):.3f}, {s.quantile(.75):.3f}]"


def rank_biserial(diff: np.ndarray) -> float:
    d = diff[diff != 0]
    if len(d) == 0:
        return 0.0
    ranks = rankdata(np.abs(d))
    return (ranks[d > 0].sum() - ranks[d < 0].sum()) / ranks.sum()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--a", required=True)
    ap.add_argument("--a-name", required=True)
    ap.add_argument("--b", required=True)
    ap.add_argument("--b-name", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    a, b = pd.read_csv(args.a), pd.read_csv(args.b)
    m = a.merge(b, on="audio_path", suffixes=("_a", "_b"))
    assert len(m) == len(a) == len(b), "result files do not cover the same clips"
    A = m[[c for c in m.columns if c.endswith("_a")]].rename(columns=lambda c: c[:-2]).assign(audio_path=m.audio_path)
    B = m[[c for c in m.columns if c.endswith("_b")]].rename(columns=lambda c: c[:-2]).assign(audio_path=m.audio_path)
    na, nb = args.a_name, args.b_name

    lines = [f"# Comparación pareada de modelos ASR: {na} vs {nb}", "",
             f"n = {len(m)} clips idénticos, mismo preprocesamiento de audio (16 kHz mono) y misma normalización de texto (`common/text_norm.py`).", "",
             "## Resultados globales", "",
             f"| Métrica | {na} | {nb} |", "|---|---|---|"]
    wa, ca = corpus_rates(A)
    wb, cb = corpus_rates(B)
    lines += [f"| WER corpus | {wa*100:.2f}% | {wb*100:.2f}% |",
              f"| CER corpus | {ca*100:.2f}% | {cb*100:.2f}% |",
              f"| WER por clip, mediana [IQR] | {med_iqr(A.wer)} | {med_iqr(B.wer)} |",
              f"| CER por clip, mediana [IQR] | {med_iqr(A.cer)} | {med_iqr(B.cer)} |",
              f"| RTF mediana (2 hilos CPU) | {A.rtf.median():.3f} | {B.rtf.median():.3f} |",
              f"| Clips con WER > 1 (inserciones/alucinación) | {(A.wer > 1).sum()} | {(B.wer > 1).sum()} |",
              "", "## Prueba pareada (Wilcoxon de rangos con signo)", "",
              "| Métrica | p-value | Rank-biserial (efecto) | Clips donde gana " + nb + " | Empates | Clips donde gana " + na + " |",
              "|---|---|---|---|---|---|"]
    for metric in ("wer", "cer"):
        diff = (A[metric] - B[metric]).to_numpy()
        p = wilcoxon(A[metric], B[metric]).pvalue if np.any(diff != 0) else 1.0
        lines.append(f"| {metric.upper()} | {p:.4g} | {rank_biserial(diff):+.3f} | {(diff > 0).sum()} | {(diff == 0).sum()} | {(diff < 0).sum()} |")
    lines += ["", "Rank-biserial > 0 = " + nb + " tiene menor error; magnitud: ~0.1 pequeño, ~0.3 medio, ≥0.5 grande.", ""]

    if A.source.notna().any() and A.source.astype(str).str.len().gt(0).any():
        lines += ["## Por fuente del corpus", "", f"| Fuente | n | WER {na} | WER {nb} | CER {na} | CER {nb} |", "|---|---|---|---|---|---|"]
        for src, idx in A.groupby("source").groups.items():
            wa_s, ca_s = corpus_rates(A.loc[idx])
            wb_s, cb_s = corpus_rates(B.loc[idx])
            lines.append(f"| {src} | {len(idx)} | {wa_s*100:.1f}% | {wb_s*100:.1f}% | {ca_s*100:.1f}% | {cb_s*100:.1f}% |")
        lines.append("")

    lines += ["## Ejemplos (3 clips con mayor diferencia de WER)", ""]
    for i in (A.wer - B.wer).abs().sort_values(ascending=False).index[:3]:
        lines += [f"**{Path(A.audio_path[i]).name}**", "",
                  f"- Referencia: {A.reference[i]}",
                  f"- {na} (WER {A.wer[i]:.2f}): {A.hypothesis[i]}",
                  f"- {nb} (WER {B.wer[i]:.2f}): {B.hypothesis[i]}", ""]

    Path(args.out).write_text("\n".join(lines), encoding="utf-8")
    print(f"Written {args.out}")


if __name__ == "__main__":
    main()
