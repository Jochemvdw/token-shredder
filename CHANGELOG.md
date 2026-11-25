# Changelog

## 0.4.0 (unreleased)
First release on PyPI.
- `--max-tokens` / `-t`: fit a file, or a whole folder, into a token budget.
- `--query` / `-Q`: the parts of a file or folder that best match a question (functions, sections, rows, records) are added in full next to the outline (keyword ranking, offline).
- Input from URLs (main content of web pages) and stdin (`-`); output to stdout (`-o -`, default when piped), clipboard (`--copy`) or JSON (`--json`).
- `batch -o -`: one combined document with `<file path="...">` blocks.
- Data-file profiles for JSON, JSONL/NDJSON, CSV/TSV and Excel: types, ranges, examples, category values; bounded memory.
- Detail levels 1–5 mean the same for every format; 5 is always the full content.
- Lighter install: the HTTP API is an optional extra (`token-shredder[api]`; extras: `api`, `claude`, `dev`); converters load on demand (faster start).
- Shreds more, tuned on 98 real files (17.3M tokens → 493k at the default level): prose clean-up and real outline levels for PDF/DOCX/PPTX/TXT/Markdown; map-style JSON (lock files), XML and YAML summaries; tighter code outlines; reference sections dropped from web pages. A summary is never larger than the file.
- Robustness: UTF-8 BOM, UTF-16 and Windows-1252 text; `batch` skips node_modules/venv/build folders; clean one-line errors (write failures, bad URLs, binary stdin, empty files); total download timeout; URL charsets.
- PDF headings from typography (font size, bold) when a PDF has no bookmarks; JSON full-data output keeps numbers exactly as written; XML/YAML that doesn't parse is flagged with a note.
- Secrets: well-known credential formats are redacted in all output (`--keep-secrets` to disable); `.env` values never shown; `batch` skips secret-looking files.
- Data files: per-record index (issue titles with comment counts, dates and authors; package versions), category counts and means; Python enum/dataclass fields in outlines; faster Excel (streaming).
- `batch`: dependency folders skipped, partial results still output when some files fail, very large folders trimmed to the budget with a note.
- `benchmarks/robustness.py` checks the invariants over any folder of files.
- Fixes from two pre-release reviews (no more overwriting `.md` inputs, no fused tables/lists, exit codes).

## 0.3.0
Uploaded to TestPyPI only.
