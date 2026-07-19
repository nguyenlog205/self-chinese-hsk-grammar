"""Full-document generation: run the validated pipeline across every page of
the grammar-point appendix (Appendix A, 语法等级大纲) and write the result to
outcome/.

Usage (from the ai-project conda env, from the project root):
    python -m src.generate_outcome

Uses `run_pure_tool` (validated in experiment_result/results.json,
docs/benchmark_result.md: `run_with_box` is a no-op on these sparser pages,
100% heading/bracket-point recall on the benchmark sample already).

Markdown structuring (heading/bracket-point formatting) follows the same
rule-based approach used to validate the pipeline: lines matching an
`A.x.x.x` or `N(.N)*` heading pattern become Markdown headings, `【...】`
bracket-numbered points become bold, everything else stays as plain
paragraph lines.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
import time
from pathlib import Path

import yaml

import src.pipeline as pipeline

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config/pipeline.yaml"
OUT_PATH = PROJECT_ROOT / "outcome/语言文字规范_附录A_语法等级大纲.md"

HEADING_RE = re.compile(r"^A(\.\d+)+(\s|$)")
NUMERIC_HEADING_RE = re.compile(r"^\d+(\.\d+)*\s+\S")
BRACKET_POINT_RE = re.compile(r"^[【\[].+?[】\]]")
PAGE_NUM_RE = re.compile(r"^\d{1,4}$")


def format_page(lines: list[str], page_num: int) -> str:
    out = [f"<!-- page {page_num} -->"]
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if PAGE_NUM_RE.match(line) and lines and line == lines[-1].strip():
            continue  # drop trailing bare page-number footer
        if HEADING_RE.match(line):
            out.append(f"#### {line}")
        elif NUMERIC_HEADING_RE.match(line) and len(line) < 30:
            out.append(f"### {line}")
        elif BRACKET_POINT_RE.match(line):
            out.append(f"**{line}**")
        else:
            out.append(line)
    return "\n\n".join(out)


def render_pages(pdf_path: Path, first_page: int, last_page: int, out_dir: Path) -> None:
    """Render pages [first_page, last_page] (in the *full* source document's
    page numbering) to out_dir/page-NNN.png. Rendered from the full 260-page
    source PDF (not the per-appendix split file) so pdftoppm's zero-padding
    width is always 3 digits and output filenames directly carry the real
    full-document page number — no local-index bookkeeping needed."""
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "pdftoppm", "-r", "300", "-png",
            "-f", str(first_page), "-l", str(last_page),
            str(pdf_path), str(out_dir / "page"),
        ],
        check=True,
    )


def main():
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    first_page, last_page = config["page_range"]
    n_pages = last_page - first_page + 1

    pdf_path = PROJECT_ROOT / "data/origins/语言文字规范.pdf"
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    from rapidocr import RapidOCR

    with tempfile.TemporaryDirectory(prefix="gen_outcome_") as tmp:
        tmp_dir = Path(tmp)
        print(f"rendering {n_pages} pages...")
        render_pages(pdf_path, first_page, last_page, tmp_dir)

        engine = RapidOCR()
        t_start = time.perf_counter()
        page_blocks = []
        for page_num in range(first_page, last_page + 1):
            img_path = tmp_dir / f"page-{page_num:03d}.png"
            result = pipeline.run_pure_tool(str(img_path), engine=engine)
            page_blocks.append(format_page(result.lines, page_num))
            done = page_num - first_page + 1
            if done % 20 == 0 or done == n_pages:
                elapsed = time.perf_counter() - t_start
                print(f"  ...page {page_num} ({done}/{n_pages}, {elapsed:.0f}s elapsed)")

        OUT_PATH.write_text("\n\n---\n\n".join(page_blocks), encoding="utf-8")
        elapsed = time.perf_counter() - t_start
        print(f"wrote {OUT_PATH} ({n_pages} pages, {elapsed:.0f}s)")


if __name__ == "__main__":
    main()
