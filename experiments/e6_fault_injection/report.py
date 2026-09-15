#!/usr/bin/env python
"""E6 report — consolidates multiple inject.py summary.json files (one per
service stopped, plus one against monolith-baseline) into the "Fault Injection
Results" table the protocol asks for.

Usage:
    python report.py --summaries ../results/e6_asr_service.summary.json \
        ../results/e6_auth_service.summary.json ../results/e6_monolith.summary.json \
        --out ../results/e6_report.md
"""
import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summaries", nargs="+", required=True)
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    lines = [
        "# E6 — Fault Injection Results",
        "",
        "| Container | Detection (s) | Recovery (s) | Requests lost | % lost | Propagated? |",
        "|---|---|---|---|---|---|",
    ]

    for path in args.summaries:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        det = f"{data['detection_time_s']:.1f}" if data["detection_time_s"] is not None else "n/a"
        rec = f"{data['recovery_time_s']:.1f}" if data["recovery_time_s"] is not None else "NOT recovered"
        propagated = any(data["propagation"].values()) if data["propagation"] else False
        lines.append(
            f"| {data['container']} | {det} | {rec} | {data['requests_lost']}/{data['requests_during_outage']} | "
            f"{data['pct_lost']:.1f}% | {'yes' if propagated else 'no'} |"
        )

    lines.append("")
    lines.append(
        "**Nota de interpretación**: para el baseline monolítico, se espera que la caída de cualquier "
        "componente tumbe todo el proceso (recovery = tiempo hasta que el único contenedor completo "
        "vuelve a estar sano). Para la arquitectura propuesta, se espera aislamiento — 'Propagated? = no' "
        "para los demás servicios cuando se detiene uno."
    )

    output = "\n".join(lines)
    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Written to {args.out}")
    else:
        print(output)


if __name__ == "__main__":
    main()
