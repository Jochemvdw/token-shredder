# Advanced

Limitations: see [Known gaps and limitations](../README.md#known-gaps-and-limitations).

## Pipeline

Per file: converter for the detected format -> (levels 1-4 only) repeated-line collapse for prose formats (`--no-deduplicate`), minifier for fenced code blocks of code formats (`--no-minify`), structure optimizer -> secret redaction (`--keep-secrets`) -> token counting. Level 5 is the file itself, with redaction only.

## Configuration

There is no config file and no settings for the CLI. `token_shredder/config.py` defines defaults and reads `TOKEN_SHREDDER_DETAIL`, `TOKEN_SHREDDER_CACHE`, `TOKEN_SHREDDER_WORKERS` and `TOKEN_SHREDDER_MAX_FILE_SIZE`, but the CLI and the Python functions never use those values (no `~/.token-shredder/config.yaml` is read). Use command-line options or function arguments instead.

What does take effect:

- `TOKEN_SHREDDER_LOG_LEVEL` (e.g. `DEBUG`; default `WARNING`): log level. `-q` and `-v` override it.
- Cache directory `~/.token-shredder/cache` and lifetime of one hour (fixed). Entries are keyed by file content and options. `--no-cache` / `cache_enabled=False` skips it; URLs, stdin and the HTTP API never use it.

## Performance

- `batch --workers N` (1-64, default 4) converts files in parallel.
- A lower `-d` or a `-t` budget gives smaller output, not necessarily faster conversion; data files are streamed with bounded memory regardless of size.
- Very large folders with `-t` can take tens of seconds.

## Custom converters and processors

There is no plugin system. Converters are looked up in the `CONVERTERS` dict in `src/token_shredder/converters/__init__.py` (extension -> `"module:Class"`, module inside `token_shredder.converters`), so adding a format means adding a module there and an entry, plus the extension to `SUPPORTED_SUFFIXES` in `main.py` for `batch`. See [CONTRIBUTING.md](../CONTRIBUTING.md).

Processors (`Deduplicator`, `CodeMinifier`, `StructureOptimizer`) are plain classes with a `process(content)` method and can be used on their own ([API.md](API.md)).
