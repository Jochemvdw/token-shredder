# Changelog

## 0.4.0 (unreleased)
First release on PyPI.
- `--max-tokens` / `-t`: fit a file, or a whole folder, into a token budget.
- Input from URLs (main content of web pages) and stdin (`-`); output to stdout (`-o -`, default when piped), clipboard (`--copy`) or JSON (`--json`).
- `batch -o -`: one combined document with `<file path="...">` blocks.
- Data-file profiles for JSON, JSONL/NDJSON, CSV/TSV and Excel: types, ranges, examples, category values; bounded memory.
- Detail levels 1–5 mean the same for every format; 5 is always the full content.
- Lighter install: the HTTP API is an optional extra (`token-shredder[api]`); converters load on demand (~4x faster start).
- Many fixes from a pre-release review (no more overwriting `.md` inputs, no fused tables/lists, clean errors, non-UTF-8 input).

## 0.3.0
Uploaded to TestPyPI only.
