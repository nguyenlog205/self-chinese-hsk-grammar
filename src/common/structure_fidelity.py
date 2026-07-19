"""Structure-fidelity metrics: did the pipeline preserve headings and
bracket-numbered grammar points, not just get individual characters right.

CER/Bag-CER treat the whole page as one character stream and don't say
anything about whether specific structural markers survived OCR. For part 3
(the grammar-point appendix), that's the more relevant question: a page can
have a fine Bag-CER while still losing a `A.1.1.1` section heading or a
`【一04】` grammar-point label, which matters more for downstream use
(building study notes from the appendix) than a percentage-point diff.

Ground truth in data/benchmark/groundtruth/ marks structure explicitly:
heading lines start with `#` (e.g. `#### A.1.1.1　名词`), and bracket-numbered
grammar points appear inline as `【一04】`, `【二36】`, etc.
"""

from __future__ import annotations

import re

from src.common.scoring import normalize

_HEADING_RE = re.compile(r"^#{1,6}\s*(.+)$", re.MULTILINE)
_BRACKET_RE = re.compile(r"【[^】]+】")


def extract_headings(md_text: str) -> list[str]:
    """Return normalized heading text (Markdown '#' lines, hash stripped)."""
    return [normalize(m.group(1)) for m in _HEADING_RE.finditer(md_text)]


def extract_bracket_points(md_text: str) -> list[str]:
    """Return bracket-numbered grammar-point labels, e.g. '【一04】'."""
    return _BRACKET_RE.findall(md_text)


def _recall(reference_items: list[str], hypothesis_text: str) -> float:
    """Fraction of reference_items found as a substring of hypothesis_text
    (both compared after the same normalization used for CER)."""
    if not reference_items:
        return 1.0
    hyp_norm = normalize(hypothesis_text)
    found = sum(1 for item in reference_items if item and item in hyp_norm)
    return found / len(reference_items)


def heading_recall(reference: str, hypothesis: str) -> float:
    """Fraction of ground-truth headings recoverable from the hypothesis text."""
    return _recall(extract_headings(reference), hypothesis)


def bracket_recall(reference: str, hypothesis: str) -> float:
    """Fraction of ground-truth bracket-numbered points recoverable from the
    hypothesis text."""
    ref_points = [normalize(b) for b in extract_bracket_points(reference)]
    return _recall(ref_points, hypothesis)


def structure_fidelity(reference: str, hypothesis: str) -> dict:
    """Combined structure-fidelity report for one page."""
    headings = extract_headings(reference)
    brackets = extract_bracket_points(reference)
    return {
        "n_headings": len(headings),
        "n_bracket_points": len(brackets),
        "heading_recall": heading_recall(reference, hypothesis),
        "bracket_recall": bracket_recall(reference, hypothesis),
    }
