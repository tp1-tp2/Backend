#!/usr/bin/env python
"""Full-corpus WER control of the CTranslate2 engine (docs/17 §1, docs/15).

Reads the per-clip CSVs written by engine_parity.py for the full corpus
(results/e2_parity_full_<engine>_<compute>.csv), compares each CTranslate2
configuration with the transformers fp32 reference CLIP BY CLIP (Wilcoxon
signed-rank on per-clip WER/CER, paired effect size = matched-pairs
rank-biserial correlation), and then:

1. writes results/e2_parity_full_report.md,
2. writes results/e2_parity_full_chapter_text.md with ready-to-paste chapter
   texts (wording depends on whether the difference is significant — the
   result is reported as it comes out, favourable or not). The chapter
   (cap-5-extracted.md) is edited by hand; this script never touches it,
3. appends/updates the full-corpus section in docs/17-resultados-v2-cpu.md.

RTF from this run is NOT reported: the three configurations ran in parallel
containers sharing the CPU, so timings are contended (only WER/CER matter).

    python wer_full_control.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import wilcoxon

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RES = ROOT / "experiments" / "results"
DOC17 = ROOT / "docs" / "17-resultados-v2-cpu.md"
MARK_START = "<!-- WER_FULL_START -->"
MARK_END = "<!-- WER_FULL_END -->"


def rank_biserial(diff: np.ndarray) -> float:
    """Matched-pairs rank-biserial correlation (Kerby 2014): effect size for
    the Wilcoxon signed-rank test. >0 means the CT2 config has HIGHER error."""
    d = diff[diff != 0]
    if len(d) == 0:
        return 0.0
    ranks = pd.Series(np.abs(d)).rank().to_numpy()
    pos, neg = ranks[d > 0].sum(), ranks[d < 0].sum()
    return float((pos - neg) / (pos + neg))


def magnitude(r: float) -> str:
    a = abs(r)
    return "despreciable" if a < 0.1 else "pequeño" if a < 0.3 else "mediano" if a < 0.5 else "grande"


def load(name: str) -> pd.DataFrame:
    d = pd.read_csv(RES / f"e2_parity_full_{name}.csv")
    return d.drop_duplicates("audio_path").set_index("audio_path")


def main() -> None:
    ref = load("transformers_fp32")
    rows, comps = [], {}
    for name, label in (("transformers_fp32", "transformers fp32 (referencia)"),
                        ("ctranslate2_fp32", "CTranslate2 fp32"),
                        ("ctranslate2_int8", "CTranslate2 int8")):
        d = load(name)
        common = ref.index.intersection(d.index)
        x, r = d.loc[common], ref.loc[common]
        row = {"config": label, "n": len(common),
               "wer_mean": x.wer.mean(), "wer_median": x.wer.median(),
               "cer_mean": x.cer.mean(), "cer_median": x.cer.median(),
               "identical": int((x.hypothesis.fillna("") == r.hypothesis.fillna("")).sum()),
               "n_empty": int((x.hypothesis.fillna("").str.strip() == "").sum()),
               "wer_gt_1_5": int((x.wer > 1.5).sum())}
        if name != "transformers_fp32":
            dw = (x.wer - r.wer).to_numpy()
            dc = (x.cer - r.cer).to_numpy()
            pw = wilcoxon(x.wer, r.wer).pvalue if np.any(dw != 0) else 1.0
            pc = wilcoxon(x.cer, r.cer).pvalue if np.any(dc != 0) else 1.0
            row.update({"delta_wer_mean": dw.mean(), "p_wer": pw, "rb_wer": rank_biserial(dw),
                        "delta_cer_mean": dc.mean(), "p_cer": pc, "rb_cer": rank_biserial(dc)})
            comps[name] = row
        rows.append(row)
    t = pd.DataFrame(rows)

    # ---- report
    lines = ["# Control de WER del motor CTranslate2 sobre el corpus completo\n",
             f"Clips comparados: {int(t.n.min())}. Comparación por clip frente a "
             "transformers fp32 (prueba de rangos con signo de Wilcoxon; tamaño de efecto: correlación "
             "biserial de rangos para muestras pareadas, > 0 = más error que la referencia).\n",
             "| Configuración | n | WER medio | WER mediana | CER medio | CER mediana | Salida idéntica a la referencia | Vacías | WER > 1.5 | ΔWER medio | p (WER) | r (WER) | ΔCER medio | p (CER) |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in t.iterrows():
        extra = (f"{r.delta_wer_mean:+.4f} | {r.p_wer:.3g} | {r.rb_wer:+.3f} ({magnitude(r.rb_wer)}) | "
                 f"{r.delta_cer_mean:+.4f} | {r.p_cer:.3g}") if "p_wer" in r and not pd.isna(r.get("p_wer")) else "— | — | — | — | —"
        lines.append(f"| {r.config} | {r.n} | {r.wer_mean:.4f} | {r.wer_median:.4f} | {r.cer_mean:.4f} | "
                     f"{r.cer_median:.4f} | {r.identical}/{r.n} | {r.n_empty} | {r.wer_gt_1_5} | {extra} |")
    lines.append("\nEl RTF de esta corrida no se reporta: las tres configuraciones se ejecutaron en paralelo "
                 "compartiendo la CPU, de modo que los tiempos están contaminados por la competencia; solo WER y CER son válidos.")
    report = "\n".join(lines) + "\n"
    (RES / "e2_parity_full_report.md").write_text(report, encoding="utf-8")
    print(report)

    # ---- chapter texts (wording follows the result)
    c32, c8 = comps["ctranslate2_fp32"], comps["ctranslate2_int8"]
    rref = t.iloc[0]
    sig = [c for c in (c32, c8) if c["p_wer"] < 0.05]

    def fmt_p(p):
        return "p \\< 0.001" if p < 0.001 else f"p \\= {p:.3f}"

    def pts(d):  # mean WER difference in percentage points
        return f"{100 * d:+.1f}".replace("+", "+").replace(".", ".")

    n = int(t.n.min())
    base = (f"Sobre el corpus completo ({n} clips), el WER medio fue de {rref.wer_mean:.3f} con el motor de referencia, "
            f"de {c32['wer_mean']:.3f} con CTranslate2 en fp32 y de {c8['wer_mean']:.3f} con CTranslate2 en int8 "
            f"(medianas de {rref.wer_median:.3f}, {c32['wer_median']:.3f} y {c8['wer_median']:.3f}). ")
    if not sig:
        text = base + (f"Las diferencias por clip no fueron significativas (prueba de rangos con signo de Wilcoxon: "
                       f"{fmt_p(c32['p_wer'])} en fp32 y {fmt_p(c8['p_wer'])} en int8), lo que confirma a escala de corpus "
                       f"que la optimización del motor no altera la calidad del reconocimiento.")
        finding = f"El control sobre los {n} clips del corpus confirmó que el motor optimizado de CPU no altera de forma significativa el WER."
        threat = ("* **Control de calidad del motor optimizado.** La equivalencia de WER entre motores se verificó por clip sobre los "
                  f"{n} clips del corpus, sin diferencias significativas.")
    else:
        parts = []
        for lab, c in (("fp32", c32), ("int8", c8)):
            parts.append(f"en {lab}, una diferencia media de {pts(c['delta_wer_mean'])} puntos porcentuales de WER "
                         f"({fmt_p(c['p_wer'])})")
        text = base + ("A diferencia de la muestra de 30 clips, a escala de corpus la diferencia por clip respecto de la referencia "
                       "fue estadísticamente significativa en al menos una configuración (prueba de rangos con signo de Wilcoxon): "
                       + "; ".join(parts) + ". La ganancia de throughput del motor optimizado conlleva, por tanto, un costo "
                       "en precisión que debe declararse y ponderarse según el escenario de uso.")
        finding = (f"Sobre los {n} clips del corpus, el motor optimizado de CPU mostró una diferencia de WER estadísticamente "
                   "significativa respecto del motor de referencia (" + "; ".join(parts) + "). Su adopción constituye, por "
                   "tanto, un compromiso entre capacidad y precisión que la plataforma puede resolver por configuración: "
                   "el motor de referencia sigue disponible, y la aceleración con GPU no alteró el WER.")
        threat = ("* **Control de calidad del motor optimizado.** La comparación por clip sobre el corpus detectó una "
                  f"diferencia de WER significativa sobre {n} clips que la muestra de 30 clips no tenía potencia para revelar; los resultados "
                  "de capacidad obtenidos con ese motor deben leerse junto con ese costo en precisión.")
    texts = {
        "WER_FULL_RTF": "0.069 con el motor optimizado de CPU (muestra de 30 clips, una solicitud a la vez)",
        "WER_FULL_TEXT": text,
        "WER_FULL_FINDING": finding,
        "WER_FULL_THREAT": threat,
    }
    where = {
        "WER_FULL_TEXT": "5.2 Resultados > Rendimiento: después de la frase del control de WER de la muestra de 30 clips (RTF 0.135 -> 0.069)",
        "WER_FULL_FINDING": "5.3.2 Hallazgos: al final del hallazgo sobre el motor de inferencia / capacidad",
        "WER_FULL_THREAT": "5.3.3 Amenazas: reemplaza la viñeta 'Control de calidad del motor optimizado' (hoy dice 'en curso')",
    }
    snippet = ["# Textos para el capítulo 5 — control de WER sobre el corpus completo", "",
               "Generado por `experiments/e8_inference_throughput/wer_full_control.py`. "
               "Pegar a mano en `cap-5-extracted.md`.", ""]
    for k, v in texts.items():
        if k in where:
            snippet += [f"## {where[k]}", "", v, ""]
    (RES / "e2_parity_full_chapter_text.md").write_text("\n".join(snippet) + "\n", encoding="utf-8")
    (RES / "e2_parity_full_chapter_text.json").write_text(json.dumps(texts, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- docs/17 section (idempotent)
    sec = (f"{MARK_START}\n### Control de WER sobre el corpus completo\n\n"
           + report.split("\n", 1)[1] + "\n**Lectura:** " + text.replace("\\", "") + f"\n{MARK_END}\n")
    doc = DOC17.read_text(encoding="utf-8")
    if MARK_START in doc:
        doc = doc[:doc.index(MARK_START)] + sec + doc[doc.index(MARK_END) + len(MARK_END) + 1:]
    else:
        anchor = "## 2. Adaptación"
        doc = doc.replace(anchor, sec + "\n---\n\n" + anchor, 1)
    DOC17.write_text(doc, encoding="utf-8")


if __name__ == "__main__":
    main()
