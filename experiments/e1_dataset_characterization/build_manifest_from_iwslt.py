#!/usr/bin/env python
"""Converts the IWSLT2026 Quechua-Spanish corpus (github.com/johneortega/
IWSLT2026_Quechua_data) into this project's manifest.csv format (see
experiments/common/manifest.py).

The repo bundles two distinct corpora, each read by a different parser here:

1. `que_spa_unconstrained/{train,valid}` — a Siminchik extract (Cardenas et al.
   2018, southern Quechua, radio recordings). Byte-identical to the
   `que_spa_constrained` folder from the older IWSLT2024_Quechua_data repo —
   confirmed by diffing transcriptions line-by-line. `txt/<split>.yaml` is a
   line-aligned list of {duration, offset, speaker_id, wav} matching
   `txt/<split>.que`. `test` has no `.que` file (withheld by past shared-task
   organizers) so it's skipped — no reference_text means no usable ground truth.

2. `que_spa_synthetic_translation/train` — a Huqariq corpus extract (Zevallos
   et al. 2022), genuinely different speakers/recordings. Only a `train` split
   exists. Format is a single TSV (`txt/train.tsv`, columns: path, speaker_id,
   offset, duration, que, spa) instead of yaml+text-file pairs.

Combining both roughly triples the manifest size (698 -> ~2,111 clips) and,
importantly, draws from two independent corpora/speaker pools instead of one —
worth calling out explicitly in E1's dataset characterization / external
validity section.

Deliberately NOT used here: QuechuaBase/asr-puno-quechua and the Mozilla
Common Voice Puno Quechua (qxp) data it's built from — the deployed model
(QuechuaBase/whisper-base-qxp-finetuned) was very likely fine-tuned on that
same corpus family, so using it for evaluation would risk train/test
contamination (see docs/03-experiment-tooling.md's note on E1 obs. 18).

Usage:
    python build_manifest_from_iwslt.py \
        --corpus-root /path/to/IWSLT2026_Quechua_data \
        --out manifest.csv
"""
import argparse
import csv
from pathlib import Path

import yaml

FIELDNAMES = ["audio_path", "reference_text", "speaker", "sex", "age", "dialect", "source", "condition"]

# --- que_spa_unconstrained (Siminchik extract) ---
SIMINCHIK_SPLITS = ["train", "valid"]
SIMINCHIK_SOURCE = "siminchik (IWSLT2026/que_spa_unconstrained, Cardenas et al. 2018)"
SIMINCHIK_DIALECT = "quechua sureño"
SIMINCHIK_CONDITION = "radio"

# --- que_spa_synthetic_translation (Huqariq extract) ---
HUQARIQ_SOURCE = "huqariq (IWSLT2026/que_spa_synthetic_translation, Zevallos et al. 2022)"
HUQARIQ_DIALECT = ""  # not declared by the corpus — leave for manual refinement if known
HUQARIQ_CONDITION = ""


def _load_siminchik_split(corpus_root: Path, split: str) -> list[dict]:
    split_dir = corpus_root / "que_spa_unconstrained" / split
    yaml_path = split_dir / "txt" / f"{split}.yaml"
    que_path = split_dir / "txt" / f"{split}.que"
    wav_dir = split_dir / "wav"

    if not que_path.exists():
        print(f"  [siminchik/{split}] no {split}.que found (reference text withheld) — skipping")
        return []

    entries = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    transcriptions = que_path.read_text(encoding="utf-8").splitlines()
    if len(entries) != len(transcriptions):
        raise ValueError(
            f"siminchik/{split}: {len(entries)} yaml entries but {len(transcriptions)} transcription "
            "lines — corpus files are supposed to be line-aligned, something is off"
        )

    rows = []
    for entry, text in zip(entries, transcriptions):
        wav_path = wav_dir / entry["wav"]
        if not wav_path.exists():
            raise FileNotFoundError(f"siminchik/{split}: referenced wav not found: {wav_path}")
        rows.append({
            "audio_path": str(wav_path.resolve()),
            "reference_text": text.strip(),
            "speaker": entry.get("speaker_id", ""),
            "sex": "",
            "age": "",
            "dialect": SIMINCHIK_DIALECT,
            "source": SIMINCHIK_SOURCE,
            "condition": SIMINCHIK_CONDITION,
        })
    return rows


def _load_huqariq_train(corpus_root: Path) -> list[dict]:
    split_dir = corpus_root / "que_spa_synthetic_translation" / "train"
    tsv_path = split_dir / "txt" / "train.tsv"
    wav_dir = split_dir / "wav"

    if not tsv_path.exists():
        print("  [huqariq] train.tsv not found — skipping")
        return []

    rows = []
    with open(tsv_path, newline="", encoding="utf-8") as f:
        for raw in csv.DictReader(f, delimiter="\t"):
            text = (raw.get("que") or "").strip()
            if not text:
                continue
            wav_path = wav_dir / raw["path"]
            if not wav_path.exists():
                raise FileNotFoundError(f"huqariq: referenced wav not found: {wav_path}")
            rows.append({
                "audio_path": str(wav_path.resolve()),
                "reference_text": text,
                "speaker": raw.get("speaker_id", ""),
                "sex": "",
                "age": "",
                "dialect": HUQARIQ_DIALECT,
                "source": HUQARIQ_SOURCE,
                "condition": HUQARIQ_CONDITION,
            })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", required=True, help="Path to IWSLT2026_Quechua_data/")
    parser.add_argument("--out", default="manifest.csv")
    parser.add_argument(
        "--skip", nargs="*", default=[], choices=["siminchik", "huqariq"],
        help="Corpora to exclude (e.g. --skip huqariq to reproduce the old IWSLT2024-only manifest)",
    )
    args = parser.parse_args()

    corpus_root = Path(args.corpus_root)
    all_rows = []

    if "siminchik" not in args.skip:
        for split in SIMINCHIK_SPLITS:
            rows = _load_siminchik_split(corpus_root, split)
            print(f"[siminchik/{split}] {len(rows)} clips with reference text")
            all_rows.extend(rows)

    if "huqariq" not in args.skip:
        rows = _load_huqariq_train(corpus_root)
        print(f"[huqariq/train] {len(rows)} clips with reference text")
        all_rows.extend(rows)

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n{len(all_rows)} total rows written to {args.out}")
    print(f"Unique speakers: {len({r['speaker'] for r in all_rows if r['speaker']})}")
    print(f"Sources: {sorted({r['source'] for r in all_rows})}")


if __name__ == "__main__":
    main()
