"""Reading-order reconstruction from OCR bounding boxes.

Plain, standalone utility — not a "pipeline". src/pipeline.py calls it
directly for the "+ box" variant; it has no dependency on the caller.

Motivation: RapidOCR's raw output lists recognized text lines in scan order
(top-to-bottom across the *full page width*), which interleaves adjacent
columns in multi-column tables, e.g. entries 537, 578, 538, 579, ... instead
of 537, 538, ..., 578, .... Levenshtein-based CER penalizes that reordering
as heavily as a wrong character, even though every token was recognized
correctly.

A naive column-major concatenation (cluster by x, emit each column's boxes
top-to-bottom, one full column before the next) makes this *worse* on
two-column vocabulary tables: those tables are laid out as two blocks, each
block itself a "number / word / pinyin" triplet per row, so grouping by
fine-grained x-cluster produces "all numbers, then all words, then all
pinyin" instead of row records.

The algorithm here is two-level instead:
1. Cluster boxes into *blocks* by x-position, using a threshold set relative
   to the single largest gap on the page (`block_alpha * max_gap`) rather
   than a fixed fraction of page width — a fixed fraction cannot separate
   both a 2-block vocabulary table (~24% gutter) and a 5-column syllable
   table (~12% gutters, but 4 of them) at the same time.
2. Within each block, group boxes into *rows* by y-position, using a small
   absolute pixel threshold (line height is consistently ~60-65px at 300 DPI
   across every layout in this document, so row grouping does not need
   per-page-type tuning the way block detection does).
3. Sort rows top-to-bottom, sort items left-to-right within a row, and
   concatenate blocks left-to-right.

This helps dense multi-column tables a great deal but *hurts* sparse pages
(title pages, short prose): with few boxes, a couple of stray x-outliers are
enough to trigger a spurious block split, and the raw scan order was already
correct for those pages. Callers should gate use of this function on box
count (empirically, pages with >=100 detected boxes benefit; pages below
that threshold do not) — the gate is left to the caller, not hardcoded here.
"""

from __future__ import annotations

import numpy as np


def _centers(boxes) -> tuple[np.ndarray, np.ndarray]:
    pts = [np.asarray(b, dtype=float) for b in boxes]
    xs = np.array([p[:, 0].mean() for p in pts])
    ys = np.array([p[:, 1].mean() for p in pts])
    return xs, ys


def detect_blocks(xs: np.ndarray, block_alpha: float = 0.75) -> list[int]:
    """Cluster x-centers into blocks via a max-gap-relative threshold.

    Sorts x-centers, finds every gap larger than `block_alpha` times the
    single largest gap on the page, and splits into a new block at each such
    gap. Returns a block id per item, in the original input order.
    """
    n = len(xs)
    if n <= 1:
        return [0] * n

    order = np.argsort(xs)
    sorted_xs = xs[order]
    gaps = np.diff(sorted_xs)
    max_gap = gaps.max() if len(gaps) else 0.0
    threshold = block_alpha * max_gap if max_gap > 0 else float("inf")

    block_of_sorted = [0] * n
    current = 0
    for i in range(1, n):
        if gaps[i - 1] > threshold:
            current += 1
        block_of_sorted[i] = current

    block_ids = [0] * n
    for sorted_pos, original_idx in enumerate(order):
        block_ids[original_idx] = block_of_sorted[sorted_pos]
    return block_ids


def group_rows(indices: list[int], ys: np.ndarray, row_gap_px: float = 30.0) -> list[list[int]]:
    """Group `indices` (into the shared xs/ys arrays) into rows by y-position.

    Sorts by y and starts a new row whenever the gap to the previous item
    exceeds `row_gap_px`. Line height in this document is ~60-65px at 300
    DPI regardless of column layout, so 30px (about half a line) reliably
    separates distinct rows without needing per-page tuning.
    """
    if not indices:
        return []
    order = sorted(indices, key=lambda i: ys[i])
    rows: list[list[int]] = [[order[0]]]
    for idx in order[1:]:
        if ys[idx] - ys[rows[-1][-1]] > row_gap_px:
            rows.append([idx])
        else:
            rows[-1].append(idx)
    return rows


def reorder_reading_order(
    boxes: list,
    texts: list[str],
    block_alpha: float = 0.75,
    row_gap_px: float = 30.0,
) -> list[str]:
    """Reorder `texts` into (block-major, then row-major within block, then
    left-to-right within row) order, using `boxes` (per-line bounding
    quadrilaterals) instead of raw full-width scan order.
    """
    if not boxes:
        return list(texts)

    xs, ys = _centers(boxes)
    block_ids = detect_blocks(xs, block_alpha=block_alpha)

    n_blocks = max(block_ids) + 1
    block_mean_x = [
        float(np.mean([xs[i] for i in range(len(texts)) if block_ids[i] == b]))
        for b in range(n_blocks)
    ]
    block_order = sorted(range(n_blocks), key=lambda b: block_mean_x[b])

    ordered_texts: list[str] = []
    for block in block_order:
        member_indices = [i for i in range(len(texts)) if block_ids[i] == block]
        for row in group_rows(member_indices, ys, row_gap_px=row_gap_px):
            row.sort(key=lambda i: xs[i])
            ordered_texts.extend(texts[i] for i in row)
    return ordered_texts
