# Changelog

## 0.4.0 (unreleased)
First release on PyPI.
- `--max-tokens` / `-t`: fit a file, or a whole folder, into a token budget.
- Input from URLs (main content of web pages) and stdin (`-`); output to stdout (`-o -`, default when piped), clipboard (`--copy`) or JSON (`--json`).
- `batch -o -`: one combined document with `<file path="...">` blocks.
- Data-file profiles for JSON, JSONL/NDJSON, CSV/TSV and Excel: types, ranges, examples, category values; bounded memory.
- Detail levels 1–5 mean the same for every format; 5 is always the full content.
- Lighter install: the HTTP API is an optional extra (`token-shredder[api]`); converters load on demand (~4x faster start).
- Shreds more, tuned on 98 real files (17.3M tokens → 467k at the default level, was 1.03M): prose clean-up and real outline levels for PDF/DOCX/PPTX/TXT/Markdown; map-style JSON (lock files), XML and YAML summaries; tighter code outlines; reference sections dropped from web pages. A summary is never larger than the file.
- Robustness: UTF-8 BOM, UTF-16 and Windows-1252 text; `batch` skips node_modules/venv/build folders; clean one-line errors (write failures, bad URLs, binary stdin, empty files); total download timeout; URL charsets.
- `benchmarks/robustness.py` checks the invariants over any folder of files.
- Fixes from two pre-release reviews (no more overwriting `.md` inputs, no fused tables/lists, exit codes).

## 0.3.0
Uploaded to TestPyPI only.
