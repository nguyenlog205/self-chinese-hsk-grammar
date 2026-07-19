# Benchmark result — grammar-point appendix (Appendix A)

The project's scope narrowed to just the grammar-point appendix
(语法等级大纲, pages 176-260) — the reference/vocabulary-table parts that
were also benchmarked earlier are no longer needed and were removed (see git
history if that work is wanted again).

## Result

`src/pipelines/part3.py` runs plain RapidOCR (`run_pure_tool`) over each
page. Benchmarked against the 7-page hand-transcribed sample in
`data/benchmark/` (`config/experiments/part3.yaml`,
`experiment_result/part3/results.json`):

- **Mean CER: 0.041** (95.9% character accuracy)
- **Heading recall: 100%** — every `A.x.x.x` section heading in the ground
  truth was recoverable from the OCR output.
- **Bracket-point recall: 100%** — every `【一04】`-style grammar-point label
  was recoverable too.
- `run_with_box` (box-count-gated reading-order reconstruction, see
  `src/common/reading_order.py`) produces **identical** output to
  `run_pure_tool` here — these pages are sparse enough that the reordering
  gate never fires. Not needed for this part; kept in the pipeline only as
  the comparison that confirmed that.

**Verdict: ship as-is.** No post-processing was added — plain RapidOCR
already recovers the headings and grammar-point labels that matter for this
document, which is the whole point of extracting it.

## Known limitation

`notebooks/part3/error_analysis.ipynb` found one real failure mode:
`page-260` (the closing prose passage) drops one full source line (38
characters) from the OCR output entirely — a detection miss, not a
formatting issue. It didn't show up in the structure-fidelity metric because
that page has no headings or bracket points to lose, but it's real content
loss.

Detecting this systematically (flagging pages with unusually large deletion
runs) requires ground truth to compare against, which only exists for the
7-page benchmark sample — not for the other 78 pages in the full 85-page
appendix. **Not implemented.** If exact fidelity matters for a specific
page, cross-check `outcome/语言文字规范_第三部分_p176-260.md` against the
source PDF (`data/origins/语言文字规范.pdf`, pages 176-260) directly.
