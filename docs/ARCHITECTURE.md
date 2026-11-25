# Architecture

Limitations: see [Known gaps and limitations](../README.md#known-gaps-and-limitations).

```
file / URL / stdin
   -> source handling (sources.py: URL download or stdin to a temp file, format detection)
   -> converter for the format (converters/)
   -> post-processing at levels 1-4 (processors/)
   -> secret redaction (secrets.py)
   -> optional --query / --max-tokens selection (query.py, main.py)
   -> output: .md file, stdout, clipboard or JSON, plus token report
```

## Modules (`src/token_shredder/`)

- `main.py`: Typer CLI (`convert`, `batch`, `analyze`, `version`, `preview`, `quality`), `convert_file`, `batch_convert`, token-budget fitting and folder budget sharing.
- `converters/`: one class per format family, loaded on first use. `CONVERTERS` in `converters/__init__.py` maps extensions to classes; each implements `BaseConverter` (`convert`, `convert_to_markdown`, `get_file_info`).
- `profiling.py`: streaming profiler for JSON/JSONL/CSV/XLSX. `prose.py`: clean-up shared by PDF/DOCX/PPTX/TXT/Markdown.
- `query.py`: chunking (functions, sections, rows, records) and BM25 keyword ranking for `--query`.
- `sources.py`: URL download (50 MB limit) and stdin.
- `secrets.py`: redaction of well-known credential formats.
- `processors/`: `Deduplicator`, `CodeMinifier`, `StructureOptimizer` (used by the pipeline), plus `Summarizer` and `ImageHandler` (not used by the CLI).
- `metrics/`: `TokenCounter` (tiktoken), `QualityScorer` (word-overlap heuristic; used by `quality`), `Benchmark`.
- `api.py`: optional FastAPI server (`token-shredder[api]`); `config.py`: cache manager and unused settings defaults ([ADVANCED.md](ADVANCED.md)).
- `models/`: `ConversionResult`, `ConversionOptions`.

## Behaviour worth knowing

- Detail level 5 is the file itself; levels 1-4 are summaries, never larger than the file (for text formats and documents up to 2 MB).
- With a budget, the highest level that fits is chosen; if nothing fits, level 1 is truncated.
- Errors: unreadable or unsupported input -> one-line message and exit code 1. In `batch`, files that work are still output.
