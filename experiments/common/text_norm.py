"""Text normalization applied before jiwer WER/CER comparisons (E2, E5).

What "Quechua-aware tokenization" should mean beyond lowercase + punctuation
stripping is a judgment call for the thesis, not something this script can
decide on its own (see docs/03-experiment-tooling.md and the plan's "what is
NOT a coding task" section) — this gives a reasonable, documented default
that keeps E2/E5 runnable; revisit if the professor's rubric wants more.
"""
import re
import unicodedata

_PUNCT_RE = re.compile(r"[^\w\s'’]", re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = text.lower()
    text = _PUNCT_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text
