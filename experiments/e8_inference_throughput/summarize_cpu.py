#!/usr/bin/env python
"""Quick per-config summary of E8 CSVs: audio-s/s and p50/p95 per concurrency,
peak throughput, and the WER/CER control per configuration."""
import glob
import sys
from pathlib import Path

import jiwer
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.text_norm import normalize  # noqa: E402

RESULTS = Path(__file__).resolve().parents[1] / "results"


def main() -> None:
    rows, peaks = [], []
    for f in sorted(glob.glob(str(RESULTS / "e8_*.csv"))):
        name = Path(f).stem
        if any(k in name for k in ("parity", "report", "cpu_levels", "cpu_summary")):
            continue
        try:
            d = pd.read_csv(f)
        except pd.errors.EmptyDataError:
            continue
        ok = d[d.status == 200]
        if ok.empty:
            continue
        label = d.label.iloc[0]
        for c, g in ok.groupby("concurrency"):
            span = g.ts.max() - g.ts.min() + g.latency_s.median()
            rows.append({"label": label, "c": c, "n": len(g), "req_s": len(g) / span,
                         "audio_s_per_s": g.audio_s.sum() / span,
                         "p50": g.latency_s.median(), "p95": g.latency_s.quantile(0.95),
                         "errors": int((d[d.concurrency == c].status != 200).sum())})
        ref = ok.reference_text.fillna("").map(normalize)
        hyp = ok.text.fillna("").map(normalize)
        mask = ref.str.len() > 0
        peaks.append({"label": label,
                      "wer": jiwer.wer(list(ref[mask]), list(hyp[mask])),
                      "cer": jiwer.cer(list(ref[mask]), list(hyp[mask]))})
    t = pd.DataFrame(rows)
    pk = t.groupby("label").audio_s_per_s.max().rename("peak_audio_s_per_s")
    out = pd.DataFrame(peaks).set_index("label").join(pk)
    base = out.loc["cpu-fp32-b1", "peak_audio_s_per_s"] if "cpu-fp32-b1" in out.index else None
    if base:
        out["speedup"] = out.peak_audio_s_per_s / base
    pd.set_option("display.width", 200)
    print(t.round(3).to_string(index=False))
    print()
    print(out.sort_values("peak_audio_s_per_s", ascending=False).round(3).to_string())
    t.to_csv(RESULTS / "e8_cpu_levels.csv", index=False)
    out.to_csv(RESULTS / "e8_cpu_summary.csv")


if __name__ == "__main__":
    main()
