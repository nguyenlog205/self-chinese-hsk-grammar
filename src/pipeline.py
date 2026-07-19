"""OCR pipeline for the grammar-point appendix (Appendix A, 语法等级大纲,
pages 176-260).

Pages here are bracket-numbered grammar points (`【一04】`) under hierarchical
headings (`A.1.1.1`) with example sentences. Most have too few detected text
boxes to trigger `run_with_box`'s reordering gate, so the reading-order fix
does little here (confirmed in experiment_result/results.json: mean CER
0.041 -> 0.041, unchanged); the metric that actually matters is *structural
fidelity* (see src/common/structure_fidelity.py) — headings and
bracket-point labels — which is already at 100% recall on the benchmark
sample.

Verdict (see docs/benchmark_result.md): ship as-is with plain RapidOCR
(`run_pure_tool`). `run_with_box` is kept only as the comparison that
confirmed reordering isn't needed here. The one known risk (occasional
whole-line drops, e.g. page-260) needs ground truth to detect and isn't
fixed here.
"""

from __future__ import annotations

from src.common.engine import EngineResult, run_rapidocr
from src.common.reading_order import reorder_reading_order


def run_pure_tool(image_path: str, engine=None) -> EngineResult:
    """Plain RapidOCR, no post-processing."""
    return run_rapidocr(image_path, engine=engine)


def run_with_box(
    image_path: str,
    engine=None,
    block_alpha: float = 0.75,
    row_gap_px: float = 30.0,
    min_boxes_for_reorder: int = 100,
) -> EngineResult:
    """RapidOCR, then reading-order reconstruction if the page has enough
    detected boxes to make it worthwhile (see src/common/reading_order.py).
    Expected to rarely fire on these sparser pages."""
    base = run_rapidocr(image_path, engine=engine)

    if base.boxes and len(base.boxes) >= min_boxes_for_reorder:
        ordered = reorder_reading_order(
            base.boxes, base.lines, block_alpha=block_alpha, row_gap_px=row_gap_px
        )
    else:
        ordered = base.lines

    return EngineResult(lines=ordered, text="\n".join(ordered), elapsed_s=base.elapsed_s, boxes=base.boxes)
