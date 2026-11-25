# Detail levels

`--detail-level` / `-d` takes 1–5 and means the same for every format: **higher = more content**. 3 is the default. Level 5 is always the full content with no compression. A higher level never produces a smaller output than a lower one (tested in `tests/test_detail_levels.py`).

| Level | Code (Python, JS/TS, Java, Go, Rust, C/C++) | JSON | HTML | PDF / DOCX / PPTX / XLSX |
|---|---|---|---|---|
| 1 | Class, function and method names | Top-level keys and types | Headings only | Extracted text |
| 2 | + signatures (and imports for Python) | + nested keys (3 levels) | + paragraphs, lists, quotes, code blocks | Extracted text |
| **3** | **+ first paragraph of each docstring / doc comment** | **+ an example value per key** ¹ | **+ tables** | **Extracted text** |
| 4 | + full docstrings / doc comments | All data, minified (lossless) | + link URLs and citation markers | + PPTX speaker notes |
| 5 | Full source file | Original file | Original HTML | Extracted text, no clean-up |

¹ If the schema would be longer than the minified data, you get the minified data instead.

Python outlines come from Python's own parser, so they are exact. Other languages use a line-based pattern match: it finds most top-level and member declarations but can miss unusual syntax.

Every text format gives the original file at level 5. TOML, INI, SQL, YAML, XML and similar config/data files are summarised at levels 1–4: structure plus short values, so lists and long values are dropped. Markdown and logs don't change between levels 1–4.

## Data files (JSON, JSONL/NDJSON, CSV, XLSX)

These are summarised by a streaming profiler (`token_shredder/profiling.py`): memory stays bounded however many rows the file has, so a 50 MB CSV costs about one page at level 3.

| Level | JSON / JSONL (lists of objects) | CSV | XLSX (per sheet) |
|---|---|---|---|
| 1 | Field names + types | Column names | Column names |
| 2 | + presence counts (`n/N` when a field is missing in some rows), number ranges | + types and ranges | + types and ranges |
| **3** | **+ string lengths, examples, enums (the full profile)** | **Full profile + first 5 rows as a table** | **Same as CSV** |
| 4 | All data, minified (JSONL: one object per line) | All data as CSV (more compact than a markdown table) | The whole table |
| 5 | Original file | Original file | Full tables |

Profile lines look like ``- `price`: number 0.5–1999 (int: no)``, ``- `status`: string, enum: open (60%), closed (40%)`` and ``- `title`: string 3–120 chars, e.g. "Fix crash…"``. A field is reported as an enum when it has at most 10 distinct values and either at least 20 values or repeated values; the profiler stops tracking distinct values after 50. Nested objects are flattened one level (`user.login`). ISO dates are reported as `(date) min–max`. In CSV and XLSX, numbers, `true`/`false` and empty cells (null) are inferred from the text; values with leading zeros stay strings.

Where the summary would be longer than the whole data, you get the whole data instead. CSV delimiters (`,` `;` tab `|`) are detected automatically; `.tsv` files are read as tab-separated. JSONL lines that fail to parse are skipped and counted ("3 lines could not be parsed").

## Token budget (`--max-tokens`)

Instead of choosing a level, give a budget: `token-shredder convert file -t 4000`.

- **One file:** the highest level (up to `-d`, default 5) whose output fits. If that level uses less than a quarter of the budget, the next level up is cut to the budget instead (a web page's article text beats its headings). If nothing fits, level 1 is cut. Cut output ends with `[... truncated to fit N tokens]`.
- **A folder** (`batch -t N`): the budget is shared. Files that are small at full detail get everything; large files split the rest equally, and each gets the best level that fits its share. Leftover budget is offered once more to files still below full detail.

Tokens are counted with tiktoken `cl100k_base`. Claude's tokenizer counts somewhat differently, so keep a margin of about 10–20% if you are close to a hard limit.
