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

TOML, INI and SQL show their structure at levels 1–4 and the original file at 5. Other text formats (YAML, CSV, Markdown, logs, ...) don't change between levels 1–4.
