# data/

Input data for extracting the grammar-point appendix (Appendix A,
语法等级大纲) from `语言文字规范.pdf`.

```
data/
├── origins/     source PDF + the Appendix A page split
└── benchmark/   hand-transcribed sample: images + ground truth (7 pages)
```

## `origins/`

| File | Pages | Content |
|---|---|---|
| `语言文字规范.pdf` | 1-260 | Full source document (scanned, no text layer). `src/generate_outcome.py` renders pages 176-260 from this file directly (not from the split file below), since poppler's `pdftoppm` zero-pads page numbers based on the *source* file's total page count, keeping filenames consistent. |
| `语言文字规范_第三部分_p176-260.pdf` | 176-260 | Appendix A only (语法等级大纲) — convenience split, kept for reference / sharing just this section. |

The document has no extractable text layer — `pdftotext` on the full PDF
recovers only a repeated "仅供查阅" watermark, confirming every page is a
scanned image.

## `benchmark/`

7 hand-labeled pages (176, 190, 205, 220, 235, 250, 260) used to score
`src/pipeline.py` (`config/pipeline.yaml`, `experiment_result/results.json`):

- **`images/page-NNN.png`** — 300 DPI PNG render, matching the full source
  PDF's page numbering.
- **`groundtruth/page-NNN.md`** — hand transcription (by directly reading
  the rendered image), preserving section headings and bracket-numbered
  grammar points as structured Markdown — the reference `src/common/scoring.py`
  and `src/common/structure_fidelity.py` score OCR output against.

## Adding more samples

Render a new page at 300 DPI into `images/` (e.g. `pdftoppm -r 300 -png -f N
-l N data/origins/语言文字规范.pdf data/benchmark/images/page`), transcribe it
by hand into `groundtruth/`, then add its page number to
`config/pipeline.yaml`'s `benchmark.pages` list.
