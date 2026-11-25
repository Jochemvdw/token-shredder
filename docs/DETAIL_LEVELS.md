# Detail levels

Limitations: see [Known gaps and limitations](LIMITATIONS.md).

`--detail-level` / `-d` takes 1–5 and means the same for every format: **higher = more content**. 3 is the default. Level 5 is always the full content with no compression. A higher level never produces a smaller output than a lower one (tested in `tests/test_detail_levels.py`).

| Level | Code (Python, JS/TS, Java, Go, Rust, C/C++) | Data (JSON, CSV, XLSX, ...) | HTML | PDF / DOCX / PPTX |
|---|---|---|---|---|
| 1 | Public class, function and method names (overloads counted) | Field names and types | Headings only | Headings only (PDF bookmarks or numbered headings, Heading styles, slide titles) |
| 2 | + signatures (and imports for Python) | + counts and ranges | + paragraphs, lists, quotes, code blocks | + first sentence of each paragraph (first line of each slide text box) |
| **3** | **+ first sentence of each doc comment; private members listed without docs** | **+ examples and category values (full profile)** ¹ | **+ tables; reference lists and "See also" dropped** | **Full cleaned text** ² |
| 4 | + full doc comments, private members' docs | All data (minified JSON / CSV) | + link URLs, citation markers, reference sections | + PDF page markers, PPTX speaker notes, DOCX headers/footers |
| 5 | Full source file | Original file | Original HTML | Extracted text, no clean-up |

¹ Details per data format in the section below.

**Never larger than the file:** for every text format, if a level's output would not be smaller than the file itself, you get the file (level 5) instead.

² Prose clean-up (levels 1-4, PDF/DOCX/PPTX/TXT/Markdown): words split over two lines are healed (`trans-` + `former`), hard-wrapped lines become paragraphs (list items, headings, tables and code stay separate), running headers/footers and page numbers (lines repeating on 3+ pages), form feeds, dot leaders and runs of spaces are removed, and a table of contents that only repeats the headings is dropped (kept at 4). Level 5 skips the clean-up.

## Prose documents (PDF, DOCX, PPTX, TXT, Markdown)

| Level | PDF | DOCX | PPTX | TXT / RFC | Markdown |
|---|---|---|---|---|---|
| 1 | Title + PDF bookmarks, else headings found by font size / bold and numbering (forms get a minimal outline) | Title + Heading styles | Slide titles | Title + numbered headings (`4.3.2.  Origins`) | `#` headings |
| 2 | + first sentence of each paragraph | same | + first line of each text box | same | same (first item of each list) |
| **3** | **Cleaned text** | **Cleaned text, tables in document order** | **Slide text and tables** | **Cleaned text** | **Badges, images, HTML comments and tags, link URLs and link reference definitions removed; link text, code blocks and tables kept** |
| 4 | + `## Page N` markers, table of contents | + header/footer text | + speaker notes | + table of contents | Whitespace-normalised original (URLs, images and HTML back) |
| 5 | Raw extraction | Raw extraction | Raw extraction | Original file | Original file |

Python outlines come from Python's own parser, so they are exact. Other languages use a line-based pattern match: it finds most top-level and member declarations but can miss unusual syntax.

Every text format gives the original file at level 5. INI, SQL and similar config files are summarised at levels 1–4: structure plus short values, so lists and long values are dropped. XML, YAML and TOML have their own levels (see below). Logs don't change between levels 1–4. Markdown and TXT are cleaned as described under Prose documents.

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

A dict with many keys whose values look alike (an npm lockfile's `packages`, OpenAPI `paths`) is reported as "map of N entries" with example keys and a profile of the values, like a list of records. A field that has one value in every row is shown as `= value`; URL, id and long-text fields get one example, short text up to three.

Where the summary would be longer than the whole data, you get the whole data instead, at every level (an XLSX sheet whose summary is not smaller than its table gives the table). CSV delimiters (`,` `;` tab `|`) are detected automatically; `.tsv` files are read as tab-separated. JSONL lines that fail to parse are skipped and counted ("3 lines could not be parsed").

## Config files (XML, YAML, TOML)

| Level | XML | YAML | TOML |
|---|---|---|---|
| 1 | Element outline: tags with counts | Top-level keys per document (k8s: kind and name) | Tables |
| 2 | + attribute names, profile of repeated elements | + nested key outline | + key names |
| **3** | **+ values; repeated records one line each (RSS items, Maven dependencies)** | **+ compact YAML with values; long lists of mappings profiled** | **+ short values** |
| 4 | All values, compact | All values, compact | + long values |
| 5 | Original file | Original file | Original file |

At levels 1-4 the output is never larger than the file and never smaller than the level below: when a summary would not be smaller than the file, the file itself is returned. Multi-document YAML (`---`) and namespaced XML are handled; a file that does not parse is returned as is.

## Token budget (`--max-tokens`)

Instead of choosing a level, give a budget: `token-shredder convert file -t 4000`.

- **One file:** the highest level (up to `-d`, default 5) whose output fits. If that level uses less than a quarter of the budget, the next level up is cut to the budget instead (a web page's article text beats its headings). If nothing fits, level 1 is cut. Cut output ends with `[... truncated to fit N tokens]`.
- **A folder** (`batch -t N`): the budget is shared. Files that are small at full detail get everything; large files split the rest equally, and each gets the best level that fits its share. Leftover budget is offered once more to files still below full detail.

## Questions (`--query`)

`-Q "question"` keeps the normal outline and adds the best-matching parts in full (functions, document sections, CSV rows, JSON records), ranked by keyword relevance (BM25, no model). The outline is level 3 for code and data, headings only (level 1) for prose, unless you set `-d`. Without `-t` up to about 6,000 tokens of matches are added per file; with `-t`, about 65% of the budget goes to matches and the rest to the outline. In `batch`, matches are ranked across all files together. If the whole file is smaller than the result, you get the whole file. A note in the output (`notes` in JSON) says how many parts were included or that nothing matched.

Tokens are counted with tiktoken `cl100k_base`. Claude's tokenizer counts somewhat differently, so keep a margin of about 10–20% if you are close to a hard limit.
