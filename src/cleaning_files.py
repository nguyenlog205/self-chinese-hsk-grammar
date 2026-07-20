"""Clean up outcome/*.md: fix Appendix A headings, strip bold on grammar-point
bullets, and drop/comment page boilerplate. Config: config/cleaning.yaml.
"""
import argparse
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_config(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def heading_level(code: str, offset: int) -> str:
    depth = code.count(".") + 1
    return "#" * (depth + offset)


def clean_lines(lines: list[str], config: dict) -> list[str]:
    code_pattern = re.compile(config["heading"]["code_pattern"])
    header_pattern = re.compile(r"^(#{1,6})\s*A\.(\d+(?:\.\d+)*)\s*(.*)$")
    offset = config["heading"]["level_offset"]

    bold_pattern = re.compile(config["grammar_point"]["bold_pattern"])
    drop_lines = set(config["boilerplate"]["drop_lines"])
    comment_patterns = [re.compile(p) for p in config["boilerplate"]["comment_patterns"]]

    out: list[str] = []
    i, n = 0, len(lines)
    while i < n:
        raw = lines[i].rstrip("\n")
        stripped = raw.strip()

        # 1. Header already marked with #, but possibly wrong level and/or
        #    title dropped to the next non-blank line.
        m_header = header_pattern.match(stripped)
        if m_header:
            code = m_header.group(2)
            title = m_header.group(3).strip()
            j = i + 1
            if not title:
                while j < n and lines[j].strip() == "":
                    j += 1
                if j < n:
                    title = lines[j].strip()
                    j += 1
            out.append(f"{heading_level(code, offset)} A.{code} {title}".rstrip())
            out.append("")
            i = j
            continue

        # 2. Plain "A.x.x.x<title>" line never marked as a header at all.
        m_code = code_pattern.match(stripped)
        if m_code:
            code = m_code.group(1)
            title = m_code.group(2).strip()
            out.append(f"{heading_level(code, offset)} A.{code} {title}".rstrip())
            out.append("")
            i += 1
            continue

        # 3. Grammar-point bullet: drop the bold wrapper.
        m_bold = bold_pattern.match(stripped)
        if m_bold:
            out.append(m_bold.group(1))
            i += 1
            continue

        # 4. Boilerplate: drop entirely, or wrap as an HTML comment.
        if stripped in drop_lines:
            i += 1
            continue
        if any(p.match(stripped) for p in comment_patterns):
            out.append(f"<!-- {stripped} -->")
            i += 1
            continue

        out.append(raw)
        i += 1

    return collapse_blank_lines(out)


def collapse_blank_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        if line == "" and out and out[-1] == "":
            continue
        out.append(line)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(ROOT / "config" / "cleaning.yaml"))
    args = parser.parse_args()

    config = load_config(Path(args.config))
    input_path = ROOT / config["input"]
    output_path = ROOT / config["output"]

    with open(input_path, encoding="utf-8") as f:
        lines = f.readlines()

    cleaned = clean_lines(lines, config)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(cleaned) + "\n")

    print(f"{input_path} -> {output_path} ({len(cleaned)} lines)")


if __name__ == "__main__":
    main()
