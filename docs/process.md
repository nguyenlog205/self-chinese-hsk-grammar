# Post-processing: cleaning the OCR output

`outcome/语言文字规范_附录A_语法等级大纲.md` is the raw RapidOCR output (see
`docs/benchmark_result.md` for why no OCR-side post-processing was needed).
It still has three structural defects that OCR-as-plain-text can't avoid,
all fixed by `src/cleaning_files.py` into `outcome/processed.md`.

## Problems found

**1. Section headers are inconsistent or missing.**

The appendix is numbered `A.x`, `A.x.x`, `A.x.x.x`, `A.x.x.x.x` (up to 4
levels deep). In the raw OCR output:

- 277 section headers were plain text, code glued directly to the title
  with no space and no `#`: `A.1.1.1名词`.
- 6 section headers did get a `#### ` prefix, but OCR dropped the title
  onto the next line, and all 6 were marked `####` regardless of actual
  depth:
  ```
  #### A.1.1

  词类
  ```

**2. Page boilerplate.** Every page repeats a `GF 0025—2021` /
`GF0025—2021` standard-number footer and a bare `---` separator (redundant
with the `<!-- page N -->` marker already present).

**3. Grammar-point bullets are bold.** The `【一01】...` labels (the thing
`docs/benchmark_result.md` calls out as 100%-recall) came out of OCR wrapped
in `**...**`. Not wrong, just unwanted for this document.

## Rules applied

Defined in `config/cleaning.yaml`, implemented in `src/cleaning_files.py`.

| # | Rule | Before | After |
|---|---|---|---|
| 1 | Header level = (number of `.`-separated segments after `A`) + 1 | `A.1` / `A.1.1` / `A.1.1.1` / `A.1.1.7.1` | `##` / `###` / `####` / `#####` |
| 2 | Merge a title that OCR dropped onto the next line back into its header | `#### A.1.1` ⏎⏎ `词类` | `### A.1.1 词类` |
| 3 | Insert the missing space between a glued code and title | `A.1.1.1名词` | `#### A.1.1.1 名词` |
| 4 | Strip the bold wrapper off grammar-point bullets | `**【一01】...**` | `【一01】...` |
| 5 | Drop bare `---` separators | `---` | *(removed)* |
| 6 | Comment out the repeated standard-number footer | `GF 0025—2021` | `<!-- GF 0025—2021 -->` |
| 7 | Collapse consecutive blank lines left behind by the above | n/a | n/a |

Rule 1 applies uniformly whether the header already had a (possibly wrong)
`#` prefix or was still plain text; the existing `#` count is never
trusted, only the numeric code is.

## Running it

```bash
python3 src/cleaning_files.py --config config/cleaning.yaml
# outcome/语言文字规范_附录A_语法等级大纲.md -> outcome/processed.md
```

## Verification

Counts checked against the raw file after running:

- Headers: 283 total (7 `##` + 59 `###` + 113 `####` + 104 `#####`), up
  from 6, matching 6 fixed + 277 newly recognized, with no plain `A.x.x.x`
  lines left unconverted.
- Grammar-point bullets: 572 before and after (none lost, none gained),
  preserving the 100% recall result from the benchmark.
- Page markers: 85 `<!-- page N -->` comments, unchanged.
- No `**` and no bare `---` remain anywhere in the output.

## Known gaps (not handled by this pass)

- Body text still has soft-wrapped lines (one visual line per paragraph
  line from the source, not one Markdown paragraph), left untouched since it
  doesn't affect headings or grammar-point extraction, the two things this
  document is used for downstream.
- Cross-references inside body text (e.g. `见【二58】"比较句2-（4）"`) are left
  as plain text, not turned into links.
