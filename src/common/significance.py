"""Paired Wilcoxon signed-rank testing, shared by every experiment track.

Import-safe refactor of notebook/ocr_benchmark/significance.py. Wilcoxon
(not a paired t-test) is used because CER/Bag-CER differences are not
expected to be normally distributed (a few catastrophic outliers can
dominate the tails); see notebook/ocr_benchmark_report.md Section 3.2 /
report/src/03_experiment_and_result.tex for the original write-up.
"""

from __future__ import annotations

from scipy.stats import wilcoxon


def paired_test(xs: list[float], ys: list[float], alternative: str = "less") -> dict:
    """Paired Wilcoxon signed-rank test between two equal-length score lists.

    `alternative="less"` tests H1: xs < ys (i.e. xs has lower error).
    Returns a dict with n, n_nonzero_diff, statistic, p_value, and whether
    the result is significant at alpha=0.05.
    """
    if len(xs) != len(ys):
        raise ValueError(f"paired samples must be equal length, got {len(xs)} vs {len(ys)}")

    diffs = [x - y for x, y in zip(xs, ys)]
    n_nonzero = sum(1 for d in diffs if d != 0)

    if n_nonzero == 0:
        stat, p = float("nan"), float("nan")
    else:
        stat, p = wilcoxon(xs, ys, alternative=alternative)

    return {
        "n": len(xs),
        "n_nonzero_diff": n_nonzero,
        "statistic": stat,
        "p_value": p,
        "significant_at_0.05": bool(p < 0.05) if p == p else False,
    }
