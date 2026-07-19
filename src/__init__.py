"""OCR extraction for the 语言文字规范 grammar-point appendix (Appendix A).

- src/common/           shared utilities: scoring (CER/Bag-CER), significance
                         testing, reading-order reconstruction, structure-
                         fidelity metrics, error analysis
- src/pipeline.py       the OCR pipeline (grammar appendix)
- src/run_benchmark.py  benchmark CLI against data/benchmark/
- src/generate_outcome.py  full-document generation CLI -> outcome/
"""
