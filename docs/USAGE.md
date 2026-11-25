# Usage

Limitations (outlines drop function bodies, no OCR, `--query` is keyword ranking, ...): see [Known gaps and limitations](../README.md#known-gaps-and-limitations).

## Commands

| Command | What it does |
|---|---|
| `convert SOURCE` | One file, `http(s)` URL, or `-` for stdin |
| `batch DIRECTORY` | All supported files in a folder (recursive) |
| `preview FILE [-d N]` | Prints token counts and the first 1000 characters of the output; writes nothing |
| `quality FILE [-d N]` | Token counts and a 0-100 score: a rough word-overlap heuristic against level 5, not a measure of meaning kept |
| `analyze FILE` | Format, size and basic facts (e.g. lines, functions, classes for code); no conversion |
| `version` | Prints the installed version |

## convert

```bash
token-shredder convert paper.pdf                 # writes paper.md next to the input, prints a token report
token-shredder convert paper.pdf -o notes.md     # a chosen file
token-shredder convert paper.pdf -o -            # markdown to stdout
token-shredder convert paper.pdf --copy          # clipboard
token-shredder convert data.json --json          # JSON: source, format, detail_level, source_tokens, output_tokens, notes, markdown
token-shredder convert app.py -d 5               # full file
token-shredder convert app.py -t 2000            # most detailed output that fits 2000 tokens
token-shredder convert app.py -Q "how are errors handled"
token-shredder convert https://example.com/article
curl -s https://example.com/data.json | token-shredder convert - --type json
```

| Option | Meaning |
|---|---|
| `-o, --output` | Output file, or `-` for stdout. Default: stdout when piped or when the input is a URL/stdin, else `FILE.md` |
| `-d, --detail-level 1..5` | 1 = names only, 3 = default, 5 = full content ([DETAIL_LEVELS.md](DETAIL_LEVELS.md)). With `-t`: the highest level to try |
| `-t, --max-tokens N` | Token budget (at least 50): the highest level that fits; cut and marked if even level 1 is too big |
| `-Q, --query "..."` | Adds the best-matching functions, sections, rows or records in full next to the outline (keyword ranking, offline) |
| `-c, --copy` | Copy the result to the clipboard (needs `pbcopy`, `wl-copy`, `xclip`, `xsel` or `clip`) |
| `--json` | JSON instead of markdown |
| `--type EXT` | Format of stdin/URL content when it can't be detected, e.g. `json`, `pdf` |
| `--keep-secrets` | Don't redact credentials (see below) |
| `--no-deduplicate`, `--no-minify` | Turn off the repeated-line collapse (prose formats only) and the code-block minifier |
| `--preserve-images` | PDF only: adds an `## Images` list (images per page) at level 3+ |
| `--no-cache` | Skip the 1-hour cache in `~/.token-shredder/cache` (URLs and stdin are never cached) |
| `-q`, `-v` | Quiet (errors only) / progress messages |

When the output goes to stdout, the token report goes to stderr. Converting a `.md` file writes `name.shredded.md`; the input is never overwritten. Exit code 1 means failure, with a one-line message.

**URLs** (`http`/`https` only): the main content of web pages, or the file if the URL points to a PDF/DOCX/JSON/etc. Downloads are limited to 50 MB. **stdin** (`-`): the format is sniffed from the content; give `--type` for binary data.

**Secrets:** well-known credential formats become `[REDACTED: kind]` at every level; `.env` values are never shown. A safety net, not a scanner.

## batch

```bash
token-shredder batch ./docs -o ./docs-md          # one NAME.EXT.md per file, folder structure mirrored
token-shredder batch ./src                        # .md files written next to the originals
token-shredder batch ./src -t 20000 -o -          # one document on stdout, budget shared over all files
token-shredder batch ./src -Q "retry logic" --copy
```

- Options: `-o` (output folder, or `-` for stdout), `-d`, `-t` (total budget, shared: small files stay whole, big ones split the rest), `-Q`, `-c`, `--json`, `-w/--workers 1..64` (default 4), `--keep-secrets`, `--preserve-images`, `--no-cache`, `-q`, `-v`. (`--type`, `--no-deduplicate` and `--no-minify` exist only on `convert`.)
- With `-o -`, `--copy` or `--json` the result is one document of `<file path="relative/path" detail_level="N">...</file>` blocks and nothing is written to disk.
- Skipped: hidden files and folders, `node_modules`, `venv`, `.venv`, `env`, `dist`, `build`, `target`, `vendor`, `site-packages`, `__pycache__`, `.git` and similar, `*.egg-info`, empty files, earlier batch output (`name.pdf.md`), and files whose name looks like secrets (`secret`, `credential`, `password`, `private key`, `token`, `service account`, `*.env`). Skipped secret-looking files are listed on stderr.
- If the budget is too small for every file (about 100 tokens each), the most deeply nested files are left out, with a note.
- If some files fail, the others are still output and the exit code is 1.

## Python

```python
from token_shredder import convert_file, batch_convert

r = convert_file("paper.pdf", max_tokens=4000, query="training setup",
                 write_output=False, show_metrics=False)
print(r.detail_level, r.output_tokens, r.warnings)
print(r.markdown)
```

Signatures: [API.md](API.md#python-api). `convert_file` takes file paths only, not URLs or stdin.
