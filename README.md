# 语言文字规范: Grammar Appendix Extraction

Extracting the grammar-point appendix (Appendix A, **语法等级大纲**, pages
176-260) from a scanned Chinese-language standard (*Chinese Proficiency
Grading Standards for International Chinese Language Education*, GF
0025-2021) into usable structured Markdown.

The source PDF has no text layer (`pdftotext` recovers only a repeated
watermark), so the appendix has to go through OCR. Rather than assuming an
approach would work, it was benchmarked against a 7-page hand-transcribed
sample first; see `docs/benchmark_result.md`.

## Result

Plain RapidOCR, no post-processing needed: **mean CER 0.041**, and (the
metric that actually matters here) **100% recall on both section headings
(`A.x.x.x`) and bracket-numbered grammar points (`【一04】`)** across the
benchmark sample. Full reasoning and the one known limitation (an
occasional dropped line, not auto-fixable without ground truth) in
`docs/benchmark_result.md`.

## Repository layout

```
├── data/
│   ├── origins/                source PDF + the Appendix A split (data/README.md)
│   └── benchmark/               7-page hand-transcribed sample: images/ + groundtruth/
│
├── config/pipeline.yaml        benchmark config: pages, variants, metrics
│
├── src/
│   ├── common/                  shared utilities
│   │   ├── engine.py               RapidOCR call wrapper
│   │   ├── scoring.py               CER / Bag-CER
│   │   ├── significance.py          paired Wilcoxon signed-rank test
│   │   ├── reading_order.py         box-count-gated reordering (unused here, kept for comparison)
│   │   ├── structure_fidelity.py    heading / bracket-point recall
│   │   └── error_analysis.py        edit-alignment error categorization
│   ├── pipeline.py              the OCR pipeline (pure_tool / with_box variants)
│   ├── run_benchmark.py         benchmark CLI
│   └── generate_outcome.py      full-document generation CLI
│
├── notebooks/error_analysis.ipynb   what kind of error remains (not just how much)
├── experiment_result/                 results.json, error_analysis.json
├── docs/benchmark_result.md            findings + verdict
│
└── outcome/
    └── 语言文字规范_附录A_语法等级大纲.md   the final extracted appendix
```

## Reproducing

Runs in the `ai-project` conda environment (`rapidocr`, `scipy`, `nbformat`
already installed there):

```bash
# Benchmark against data/benchmark/ -> experiment_result/results.json
python -m src.run_benchmark --config config/pipeline.yaml

# Error-analysis notebook (re-executable, real output)
jupyter nbconvert --to notebook --execute notebooks/error_analysis.ipynb

# Full 85-page appendix generation -> outcome/语言文字规范_附录A_语法等级大纲.md
python -m src.generate_outcome
```
