"""Benchmark CLI: score src/pipeline.py against data/benchmark/.

Usage (from the ai-project conda env, run from the project root):
    python -m src.run_benchmark --config config/pipeline.yaml

Loads the config, runs whichever variants (pure_tool / with_box) it lists
over the benchmark pages, scores whichever metrics it lists, and writes a
JSON results file.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

import yaml

import src.pipeline as pipeline
from src.common.scoring import bag_cer, cer
from src.common.significance import paired_test
from src.common.structure_fidelity import structure_fidelity

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    required = ["benchmark", "variants", "metrics", "output"]
    missing = [k for k in required if k not in config]
    if missing:
        raise ValueError(f"{path}: missing required config keys: {missing}")
    return config


def run_variant(variant: str, image_path: str, box_params: dict, engine):
    if variant == "pure_tool":
        return pipeline.run_pure_tool(image_path, engine=engine)
    if variant == "with_box":
        return pipeline.run_with_box(image_path, engine=engine, **box_params)
    raise ValueError(f"unknown variant: {variant!r} (expected 'pure_tool' or 'with_box')")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/pipeline.yaml", help="path to the pipeline config")
    args = parser.parse_args()

    config = load_config(args.config)

    images_dir = PROJECT_ROOT / config["benchmark"]["images_dir"]
    gt_dir = PROJECT_ROOT / config["benchmark"]["groundtruth_dir"]
    pages = [f"page-{p:03d}" for p in config["benchmark"]["pages"]]
    variants = config["variants"]
    metrics = config["metrics"]
    box_params = config.get("box_params", {})

    from rapidocr import RapidOCR

    engine = RapidOCR()

    per_page = []

    for page in pages:
        img_path = str(images_dir / f"{page}.png")
        gt_text = (gt_dir / f"{page}.md").read_text(encoding="utf-8")

        row = {"page": page}
        for variant in variants:
            result = run_variant(variant, img_path, box_params, engine)
            if "cer" in metrics:
                row[f"{variant}_cer"] = cer(gt_text, result.text)
            if "bag_cer" in metrics:
                row[f"{variant}_bag_cer"] = bag_cer(gt_text, result.text)
            if "structure_fidelity" in metrics:
                row[f"{variant}_structure_fidelity"] = structure_fidelity(gt_text, result.text)

        per_page.append(row)
        print(f"{page}: " + "  ".join(f"{v}_cer={row.get(f'{v}_cer'):.3f}" for v in variants if f"{v}_cer" in row))

    summary: dict[str, object] = {"per_page": per_page}

    if "cer" in metrics:
        for variant in variants:
            vals = [r[f"{variant}_cer"] for r in per_page]
            summary[f"mean_{variant}_cer"] = statistics.mean(vals)
            summary[f"median_{variant}_cer"] = statistics.median(vals)

    if "bag_cer" in metrics:
        for variant in variants:
            vals = [r[f"{variant}_bag_cer"] for r in per_page]
            summary[f"mean_{variant}_bag_cer"] = statistics.mean(vals)

    if "structure_fidelity" in metrics:
        for variant in variants:
            heading_recalls = [r[f"{variant}_structure_fidelity"]["heading_recall"] for r in per_page]
            bracket_recalls = [r[f"{variant}_structure_fidelity"]["bracket_recall"] for r in per_page]
            summary[f"mean_{variant}_heading_recall"] = statistics.mean(heading_recalls)
            summary[f"mean_{variant}_bracket_recall"] = statistics.mean(bracket_recalls)

    if "significance" in metrics and "pure_tool" in variants and "with_box" in variants:
        pure_cer = [r["pure_tool_cer"] for r in per_page]
        box_cer = [r["with_box_cer"] for r in per_page]
        summary["wilcoxon_with_box_vs_pure_tool_cer"] = paired_test(box_cer, pure_cer, alternative="less")

    print("\n=== SUMMARY ===")
    print(json.dumps({k: v for k, v in summary.items() if k != "per_page"}, indent=2, default=str))

    out_dir = PROJECT_ROOT / config["output"]["results_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "results.json"
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
