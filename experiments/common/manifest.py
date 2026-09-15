"""Loads and validates the audio+reference-transcript manifest shared by
E1 (dataset characterization), E2 (WER/CER/RTF) and E5 (streaming codec
comparison). One CSV, one format, reused across all three so the same dataset
underlies every accuracy-related measurement in the paper.
"""
import csv
import dataclasses
from pathlib import Path


@dataclasses.dataclass
class ManifestRow:
    audio_path: str  # resolved to an absolute path by load()
    reference_text: str
    speaker: str = ""
    sex: str = ""
    age: str = ""
    dialect: str = ""
    source: str = ""  # e.g. "siminchik", "ad-hoc"
    condition: str = ""  # e.g. "studio", "field"


REQUIRED_COLUMNS = {"audio_path", "reference_text"}


def load(manifest_path: str) -> list[ManifestRow]:
    """Reads the manifest CSV, resolves audio_path relative to the CSV's own
    directory (unless already absolute), and raises with a clear message if
    a referenced audio file is missing — better to fail here than mid-benchmark.
    """
    path = Path(manifest_path)
    base_dir = path.parent
    rows: list[ManifestRow] = []

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing_cols = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        if missing_cols:
            raise ValueError(f"Manifest is missing required columns: {missing_cols}")

        for i, raw in enumerate(reader, start=2):  # header is line 1
            audio_path = raw["audio_path"].strip()
            resolved = Path(audio_path)
            if not resolved.is_absolute():
                resolved = (base_dir / resolved).resolve()
            if not resolved.exists():
                raise FileNotFoundError(f"Manifest line {i}: audio file not found: {resolved}")

            rows.append(
                ManifestRow(
                    audio_path=str(resolved),
                    reference_text=raw["reference_text"].strip(),
                    speaker=raw.get("speaker", "").strip(),
                    sex=raw.get("sex", "").strip(),
                    age=raw.get("age", "").strip(),
                    dialect=raw.get("dialect", "").strip(),
                    source=raw.get("source", "").strip(),
                    condition=raw.get("condition", "").strip(),
                )
            )

    if not rows:
        raise ValueError(f"Manifest {manifest_path} has no data rows")
    return rows
