"""Shared, mechanical OCR-engine call — not a "pipeline".

Instantiate/reuse a RapidOCR engine, run it on an image, wrap the result.
Carries no pipeline-specific decisions (no reordering, no post-processing,
no gating) — those stay in src/pipeline.py.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class EngineResult:
    lines: list[str]
    text: str
    elapsed_s: float
    boxes: list | None = field(default=None)


def run_rapidocr(image_path: str, engine=None) -> EngineResult:
    """Run RapidOCR on a single page image.

    Pass an existing `engine` (a `rapidocr.RapidOCR()` instance) to avoid
    re-loading the ONNX models on every call, e.g. in a loop over many pages.
    """
    from rapidocr import RapidOCR

    if engine is None:
        engine = RapidOCR()

    t0 = time.perf_counter()
    result = engine(image_path)
    elapsed = time.perf_counter() - t0

    texts = list(result.txts) if result is not None and result.txts else []
    boxes = list(result.boxes) if result is not None and result.boxes is not None else None
    return EngineResult(lines=texts, text="\n".join(texts), elapsed_s=elapsed, boxes=boxes)
