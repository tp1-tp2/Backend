#!/usr/bin/env python
"""Converts the IWSLT2024 Quechua-Spanish corpus (a Siminchik subset,
Cardenas et al. 2018 — github.com/Llamacha/IWSLT2024_Quechua_data) into this
project's manifest.csv format (see experiments/common/manifest.py).

Only `train` and `valid` are used: the `test` split's Quechua transcriptions
were withheld by the shared-task organizers (README: "test folder will be
made visible after the submissions have been received") — without
reference_text those clips are useless for E2/E5's WER/CER measurement.

Each split's txt/<split>.yaml is a line-aligned list of
{duration, offset, speaker_id, wav} entries matching txt/<split>.que
(one Quechua transcription per line, same order).

Usage:
    python build_manifest_from_iwslt.py \
        --corpus-root "C:\\Users\\DIRORE\\Downloads\\audios-transcripcion\\IWSLT2024_Quechua_data-main" \
        --out manifest.csv
"""
import argparse
import csv
from pathlib import Path

import yaml

SPLITS = ["train", "valid"]
# The corpus is a radio-recording extract of Siminchik (southern Quechua) —
# per the corpus README, not independently re-verified here. Refine per-clip
# if you have more precise dialect/condition info.
SOURCE = "siminchik (IWSLT2024 constrained subset, Cardenas et al. 2018)"
DIALECT = "quechua sureño"
CONDITION = "radio"


def _load_split(corpus_root: Path, split: str) -> list[dict]:
    split_dir = corpus_root / "que_spa_constrained" / split
    yaml_path = split_dir / "txt" / f"{split}.yaml"
    que_path = split_dir / "txt" / f"{split}.que"
    wav_dir = split_dir / "wav"

    entries = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    transcriptions = que_path.read_text(encoding="utf-8").splitlines()

    if len(entries) != len(transcriptions):
        raise ValueError(
            f"{split}: {len(entries)} yaml entries but {len(transcriptions)} transcription lines — "
            "corpus files are supposed to be line-aligned, something is off"
        )

    rows = []
    for entry, text in zip(entries, transcriptions):
        wav_path = wav_dir / entry["wav"]
        if not wav_path.exists():
            raise FileNotFoundError(f"{split}: referenced wav not found: {wav_path}")
        rows.append({
            "audio_path": str(wav_path.resolve()),
            "reference_text": text.strip(),
            "speaker": entry.get("speaker_id", ""),
            "sex": "",
            "age": "",
            "dialect": DIALECT,
            "source": SOURCE,
            "condition": CONDITION,
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", required=True, help="Path to IWSLT2024_Quechua_data-main/")
    parser.add_argument("--out", default="manifest.csv")
    parser.add_argument("--splits", nargs="+", default=SPLITS, choices=["train", "valid"])
    args = parser.parse_args()

    corpus_root = Path(args.corpus_root)
    all_rows = []
    for split in args.splits:
        rows = _load_split(corpus_root, split)
        print(f"{split}: {len(rows)} clips with reference text")
        all_rows.extend(rows)

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["audio_path", "reference_text", "speaker", "sex", "age", "dialect", "source", "condition"]
        )
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n{len(all_rows)} total rows written to {args.out}")
    print(f"Unique speakers: {len({r['speaker'] for r in all_rows})}")


if __name__ == "__main__":
    main()
