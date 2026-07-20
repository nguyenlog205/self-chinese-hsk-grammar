"""Parsing + structural-integrity helpers for EDA over the cleaned appendix
(outcome/processed.md, produced by src/cleaning_files.py).

Turns the flat heading/bullet Markdown into tidy records — one row per
grammar point, with its heading path, example-line stats, and cross-refs —
plus two integrity checks (heading-code gaps, bracket-label numbering gaps)
that can catch OCR content loss the 7-page benchmark can't see, since it
only covers the full 85-page document.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

HEADER_RE = re.compile(r"^(#{2,6})\s*(A\.[\d.]+)\s*(.*)$")
BULLET_RE = re.compile(r"^【([^0-9】]+?)(\d+)】(.*)$")
CROSSREF_RE = re.compile(r"见【([^0-9】]+?)(\d+)】")
PAGE_RE = re.compile(r"^<!--\s*page\s+(\d+)\s*-->$")


def canonical_prefix(raw: str) -> str:
    """Normalize a bracket-label prefix to one of 一/二/三/四/五/六/七至九,
    collapsing OCR dash variants ('七一九', '七—九') and stray trailing
    punctuation ('五.') onto the same canonical form."""
    p = raw.strip().rstrip(".·、 ")
    if re.fullmatch(r"七[一—-]九", p):
        return "七至九"
    return p


@dataclass
class GrammarPoint:
    line_no: int
    page: int | None
    level_code: str
    level_title: str
    category_path: str
    prefix_raw: str
    prefix: str
    number: int
    label: str
    n_example_lines: int
    example_char_count: int
    cross_refs: list[str] = field(default_factory=list)


def parse_document(text: str) -> tuple[list[GrammarPoint], list[dict]]:
    """Parse processed.md into (grammar points, heading records)."""
    lines = text.splitlines()
    stack: dict[int, tuple[str, str]] = {}
    headings: list[dict] = []
    points: list[GrammarPoint] = []
    current_page: int | None = None

    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        m_page = PAGE_RE.match(stripped)
        if m_page:
            current_page = int(m_page.group(1))
            i += 1
            continue

        m_h = HEADER_RE.match(line)
        if m_h:
            level = len(m_h.group(1))
            code, title = m_h.group(2), m_h.group(3).strip()
            stack[level] = (code, title)
            for deeper in [l for l in stack if l > level]:
                del stack[deeper]
            headings.append({"line_no": i + 1, "level": level, "code": code, "title": title})
            i += 1
            continue

        m_b = BULLET_RE.match(stripped)
        if m_b:
            prefix_raw, number, label = m_b.group(1), int(m_b.group(2)), m_b.group(3)
            level_code, level_title = stack.get(2, ("", ""))
            category_path = " > ".join(stack[l][1] for l in sorted(stack) if l >= 3)
            cross_refs = [f"{cp}{cn}" for cp, cn in CROSSREF_RE.findall(label)]

            j = i + 1
            n_example_lines = 0
            example_chars = 0
            while j < n:
                nxt = lines[j].strip()
                if nxt == "":
                    j += 1
                    continue
                if HEADER_RE.match(lines[j]) or BULLET_RE.match(nxt) or PAGE_RE.match(nxt):
                    break
                n_example_lines += 1
                example_chars += len(nxt)
                cross_refs += [f"{cp}{cn}" for cp, cn in CROSSREF_RE.findall(nxt)]
                j += 1

            points.append(GrammarPoint(
                line_no=i + 1,
                page=current_page,
                level_code=level_code,
                level_title=level_title,
                category_path=category_path,
                prefix_raw=prefix_raw,
                prefix=canonical_prefix(prefix_raw),
                number=number,
                label=label.strip(),
                n_example_lines=n_example_lines,
                example_char_count=example_chars,
                cross_refs=cross_refs,
            ))
            i = j
            continue

        i += 1

    return points, headings


def numbering_gaps(points: list[GrammarPoint]) -> dict[str, dict]:
    """Per canonical prefix: count, range, duplicate numbers, missing numbers
    within [min, max]."""
    by_prefix: dict[str, list[int]] = defaultdict(list)
    for p in points:
        by_prefix[p.prefix].append(p.number)

    report = {}
    for prefix, nums in by_prefix.items():
        counts = Counter(nums)
        dups = sorted(num for num, c in counts.items() if c > 1)
        lo, hi = min(nums), max(nums)
        missing = sorted(set(range(lo, hi + 1)) - set(nums))
        report[prefix] = {"count": len(nums), "min": lo, "max": hi, "duplicates": dups, "missing": missing}
    return report


def heading_code_gaps(headings: list[dict]) -> list[dict]:
    """Flag sibling heading codes (same parent, same depth) whose numeric
    suffix isn't exactly +1 over the previous sibling."""
    siblings: dict[str, list[tuple[int, int, str]]] = defaultdict(list)
    for h in headings:
        parts = h["code"].split(".")
        parent = ".".join(parts[:-1])
        try:
            last = int(parts[-1])
        except ValueError:
            continue
        siblings[parent].append((last, h["line_no"], h["code"]))

    issues = []
    for parent, items in siblings.items():
        items.sort()
        for (prev_n, _, prev_code), (n, line_no, code) in zip(items, items[1:]):
            if n != prev_n + 1:
                issues.append({"parent": parent, "prev": prev_code, "next": code, "line_no": line_no, "gap": n - prev_n})
    return issues
