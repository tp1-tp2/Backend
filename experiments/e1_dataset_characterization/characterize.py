#!/usr/bin/env python
"""E1 — Dataset characterization.

Produces the "Dataset Characterization" table the protocol asks for: clip
count/total duration, per-clip duration stats, speaker/dialect/condition
breakdowns (from manifest columns — these can't be derived from audio itself,
so they only appear if you filled them in), and a training-overlap flag you
fill in manually (the script can't know what audio the model was fine-tuned on).

Usage:
    python characterize.py --manifest path/to/manifest.csv [--training-overlap-note "..."]
"""
import argparse
import statistics
import subprocess
import sys
import wave
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common.manifest import load  # noqa: E402


def _duration_seconds(audio_path: str) -> float:
    # manifest.csv is 100% .wav (IWSLT2026 corpora) — read the header directly
    # with the stdlib wave module instead of shelling out to ffprobe, which
    # isn't installed on this host outside the service Docker images.
    if audio_path.lower().endswith(".wav"):
        with wave.open(audio_path, "rb") as f:
            return f.getnframes() / f.getframerate()
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", audio_path],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(out.stdout.strip())


def _fmt_hms(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _breakdown(rows, field: str) -> str:
    values = [getattr(r, field) for r in rows if getattr(r, field)]
    if not values:
        return "(no declarado en el manifest)"
    counts = Counter(values)
    return ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument(
        "--training-overlap-note",
        default="PENDIENTE: declarar manualmente si el split de prueba se solapa con datos de fine-tuning (obs. 18).",
    )
    parser.add_argument("--out", default=None, help="Markdown output path (default: stdout)")
    args = parser.parse_args()

    rows = load(args.manifest)
    durations = [_duration_seconds(r.audio_path) for r in rows]
    total = sum(durations)

    lines = [
        "# E1 — Dataset Characterization",
        "",
        f"- **Número de clips**: {len(rows)}",
        f"- **Duración total**: {_fmt_hms(total)} ({total:.1f}s)",
        f"- **Duración por clip**: min={min(durations):.2f}s, max={max(durations):.2f}s, "
        f"promedio={statistics.mean(durations):.2f}s, mediana={statistics.median(durations):.2f}s",
        f"- **Hablantes**: {_breakdown(rows, 'speaker')}",
        f"- **Sexo**: {_breakdown(rows, 'sex')}",
        f"- **Rango etario**: {_breakdown(rows, 'age')}",
        f"- **Variante dialectal**: {_breakdown(rows, 'dialect')}",
        f"- **Fuente**: {_breakdown(rows, 'source')}",
        f"- **Condiciones de grabación**: {_breakdown(rows, 'condition')}",
        "",
        "## Threats to Validity (external validity)",
        "",
        f"- {args.training_overlap_note}",
    ]
    output = "\n".join(lines)

    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Written to {args.out}")
    else:
        print(output)


if __name__ == "__main__":
    main()
