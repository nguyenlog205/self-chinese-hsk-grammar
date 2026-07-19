"""Error analysis: not just *how much* CER a page has, but *what kind* of
error it is — substitution, deletion (dropped text), insertion (hallucinated
text), and specifically whether a substitution is a pinyin tone-mark loss
(e.g. 'tīng' -> 'ting'), which earlier spot-checks flagged as a recurring
RapidOCR failure mode distinct from wrong-character recognition.

Built on the same normalized text used by src/common/scoring.py, so error
categories add up to the same edit distance CER is computed from.
"""

from __future__ import annotations

import unicodedata
from collections import Counter

from src.common.scoring import normalize


def align(reference: str, hypothesis: str) -> list[tuple[str, str, str]]:
    """Levenshtein alignment via DP + backtrace.

    Returns a list of (op, ref_char, hyp_char) tuples, op in
    {'match', 'sub', 'del', 'ins'}: 'del' is a reference character missing
    from the hypothesis, 'ins' is an extra hypothesis character not present
    in the reference.
    """
    a, b = reference, hypothesis
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        ai = a[i - 1]
        for j in range(1, m + 1):
            cost = 0 if ai == b[j - 1] else 1
            dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost)

    ops: list[tuple[str, str, str]] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and a[i - 1] == b[j - 1] and dp[i][j] == dp[i - 1][j - 1]:
            ops.append(("match", a[i - 1], b[j - 1]))
            i, j = i - 1, j - 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
            ops.append(("sub", a[i - 1], b[j - 1]))
            i, j = i - 1, j - 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            ops.append(("del", a[i - 1], ""))
            i -= 1
        else:
            ops.append(("ins", "", b[j - 1]))
            j -= 1
    ops.reverse()
    return ops


def _is_tone_mark_loss(ref_char: str, hyp_char: str) -> bool:
    """True if ref_char and hyp_char share the same base Latin letter but
    differ only in tone-mark diacritic (e.g. 'ī' vs 'i', 'á' vs 'a', or one
    tone vs another like 'á' vs 'à')."""
    if not ref_char or not hyp_char or ref_char == hyp_char:
        return False
    ref_base = unicodedata.normalize("NFD", ref_char)[0]
    hyp_base = unicodedata.normalize("NFD", hyp_char)[0]
    return ref_base.isalpha() and ref_base.lower() == hyp_base.lower()


def categorize_errors(reference: str, hypothesis: str) -> dict:
    """Categorize edit operations between normalized reference/hypothesis text."""
    ref_norm = normalize(reference)
    hyp_norm = normalize(hypothesis)
    ops = align(ref_norm, hyp_norm)

    substitutions = Counter()
    tone_mark_losses = Counter()
    deletions = Counter()
    insertions = Counter()

    n_match = n_sub = n_del = n_ins = n_tone = 0
    for op, ref_c, hyp_c in ops:
        if op == "match":
            n_match += 1
        elif op == "sub":
            n_sub += 1
            substitutions[(ref_c, hyp_c)] += 1
            if _is_tone_mark_loss(ref_c, hyp_c):
                n_tone += 1
                tone_mark_losses[(ref_c, hyp_c)] += 1
        elif op == "del":
            n_del += 1
            deletions[ref_c] += 1
        elif op == "ins":
            n_ins += 1
            insertions[hyp_c] += 1

    total_edits = n_sub + n_del + n_ins
    return {
        "ref_len": len(ref_norm),
        "n_match": n_match,
        "n_substitutions": n_sub,
        "n_deletions": n_del,
        "n_insertions": n_ins,
        "n_tone_mark_losses": n_tone,
        "share_substitutions": n_sub / total_edits if total_edits else 0.0,
        "share_deletions": n_del / total_edits if total_edits else 0.0,
        "share_insertions": n_ins / total_edits if total_edits else 0.0,
        "share_tone_mark_of_substitutions": n_tone / n_sub if n_sub else 0.0,
        "top_substitutions": [
            {"ref": r, "hyp": h, "count": c} for (r, h), c in substitutions.most_common(10)
        ],
        "top_deletions": [{"char": c, "count": n} for c, n in deletions.most_common(10)],
        "top_insertions": [{"char": c, "count": n} for c, n in insertions.most_common(10)],
    }
