"""Character-level scoring: CER (order-sensitive) and Bag-CER (order-insensitive).

Import-safe refactor of the logic in notebook/ocr_benchmark/score.py, used by
every experiment (one_tool_only and hybrid alike) so scores stay comparable.
The original notebook/ocr_benchmark/score.py is left untouched; it documents
exactly what produced the baseline benchmark's scores.json.
"""

import re
from collections import Counter


def normalize(text: str) -> str:
    """Strip markdown/table syntax, decorative leader dots, and whitespace."""
    text = re.sub(r"\|", "", text)
    text = re.sub(r"^[#\-\s]+$", "", text, flags=re.MULTILINE)
    text = re.sub(r"[#*`]", "", text)
    text = re.sub(r"---+", "", text)
    text = re.sub(r"[.]{3,}", "", text)  # decorative TOC leader-dot runs, not content
    text = re.sub(r"\s+", "", text)
    return text


def levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[-1]


def cer(reference: str, hypothesis: str) -> float:
    """Order-sensitive character error rate."""
    ref_norm = normalize(reference)
    hyp_norm = normalize(hypothesis)
    if not ref_norm:
        return 0.0 if not hyp_norm else 1.0
    dist = levenshtein(ref_norm, hyp_norm)
    return dist / len(ref_norm)


def bag_cer(reference: str, hypothesis: str) -> float:
    """Order-insensitive character error rate, via multiset overlap."""
    ref_norm = normalize(reference)
    hyp_norm = normalize(hypothesis)
    if not ref_norm:
        return 0.0 if not hyp_norm else 1.0
    ref_counts = Counter(ref_norm)
    hyp_counts = Counter(hyp_norm)
    overlap = sum((ref_counts & hyp_counts).values())
    return 1 - (overlap / len(ref_norm))
