# API reference

Limitations: see [Known gaps and limitations](LIMITATIONS.md). The HTTP API has no authentication; run it on localhost or behind your own auth.

## HTTP API

```bash
pip install "token-shredder[api]"
uvicorn token_shredder.api:app          # http://127.0.0.1:8000
```

The server uses the same pipeline as the CLI, with the cache off. It takes uploaded files only: no URLs, `max_tokens`, `query` or `keep_secrets` (secrets are always redacted). Uploads over 100 MB give 413.

### POST /convert

Multipart upload with field `file`; query/form parameters:

- `detail_level`: int 1-5 (default 3; 422 if out of range)
- `preserve_images`: bool (default false)
- `deduplicate`: bool (default true)

```bash
curl -F file=@paper.pdf "http://127.0.0.1:8000/convert?detail_level=3"
```

Response:

```json
{
  "markdown": "...",
  "source_file": "paper.pdf",
  "format": "pdf",
  "source_tokens": 8450,
  "output_tokens": 3820,
  "tokens_saved": 4630,
  "tokens_saved_pct": 54.8,
  "processing_time_ms": 2300.0,
  "pages": 12,
  "images_count": 0,
  "tables_count": 3,
  "warnings": []
}
```

(Numbers are illustrative.) 422 with a `detail` message if the file can't be converted.

### POST /batch

Several `files` fields, plus `detail_level` and `preserve_images`. Returns `results` (as above), `errors` (one message per failed file), `total_tokens_saved`, `files_processed`.

### GET /health

`{"status": "ok", "version": "<installed version>"}`

## Python API

```python
from token_shredder import convert_file, batch_convert, ConversionError
```

### convert_file

```python
convert_file(file_path, output_path=None, detail_level=None, preserve_images=False,
             embed_images=False, include_comments=False, deduplicate=True, minify_code=True,
             optimize_structure=True, show_metrics=True, cache_enabled=True, confirm_large=True,
             write_output=True, max_tokens=None, display_name=None, file_format=None,
             redact_secrets=True, query=None) -> ConversionResult
```

- `detail_level` None means 3 (or, with `max_tokens`, "up to 5"). Must be 1-5, else `ValueError`; `max_tokens` must be at least 50.
- `write_output=True` writes `FILE.md` (or `output_path`); use `write_output=False` to only get the result.
- `show_metrics=True` prints the token report to stdout.
- `include_comments` and `embed_images` are accepted but currently have no effect.
- `query` adds the best-matching parts in full ([USAGE.md](USAGE.md)).
- Raises `ConversionError` (unsupported type, unreadable file, ...).
- File paths only: URL and stdin handling live in the CLI (`token_shredder.sources`).

`ConversionResult` fields: `markdown`, `source_file`, `target_file`, `format`, `source_tokens`, `output_tokens`, `tokens_saved`, `tokens_saved_pct`, `quality_score` (only filled by `quality`), `processing_time_ms`, `pages`, `images_count`, `tables_count`, `warnings`, `detail_level`.

### batch_convert

```python
batch_convert(directory, output_dir=None, detail_level=None, workers=4, preserve_images=False,
              quiet=False, max_tokens=None, write_output=True, cache_enabled=True,
              redact_secrets=True, query=None) -> list[ConversionResult]
```

Same file selection as the CLI (skipped folders, secret-looking names; see [USAGE.md](USAGE.md#batch)). Output is `NAME.EXT.md`, mirrored under `output_dir` if given, else next to the originals. Raises an error at the end if any file failed. Also importable from `token_shredder.main`, which also has `combine_results(results, root)` for the `<file>` block document.

### Other exports

- `get_converter(format_type)` -> converter instance for an extension such as `"pdf"`, or `None`
- `detect_file_format(file_path)` -> extension string (`"xls"` is detected but has no converter)
- `TokenCounter` (`from token_shredder.metrics`): see [TOKEN_COUNTER.md](TOKEN_COUNTER.md)
- `QualityScorer().score(converted, original) -> float` (0-100 heuristic)
- `Deduplicator(threshold=1.0).process(content) -> str`: collapses repeated lines; 1.0 means exact repeats only
- `CodeMinifier().process(content, language="python") -> str`
- `StructureOptimizer().process(content) -> str`
