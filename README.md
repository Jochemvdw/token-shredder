# Token Shredder

**Shrink files, folders and web pages into compact markdown that fits your LLM's token budget — locally, without AI.**

For developers who paste code, documents and data into Claude, ChatGPT or another model and run out of context (or money). Token Shredder keeps the structure and the facts a model needs and drops the rest: code becomes an outline, a CSV becomes a summary of its columns, a web page becomes its article. It's lossy on purpose — and you decide how lossy, or give it a token budget and a question.

No API key and no AI model; it runs on your machine. (The one network access: on first use, the tokenizer library downloads a 1.7 MB file once.)

> **Status:** alpha (v0.4.1). Tested on ~120 real files and on macOS, Linux and Windows; the interface may still change. See [what it can't do](#limitations).

## Install

```bash
pip install token-shredder              # or: pipx install token-shredder
uvx token-shredder convert file.pdf     # or run it without installing
```

Python 3.10–3.13.

## See it

**A 60 KB CSV (30,085 tokens) → 751 tokens:** `token-shredder convert titanic.csv`

```text
Rows: 891, columns: 12
- `Survived`: number, enum: 0 ×549 (62%), 1 ×342 (38%)
- `Pclass`: number, enum: 3 ×491 (55%), 1 ×216 (24%), 2 ×184 (21%)
- `Sex`: string, enum: male ×577 (65%), female ×314 (35%)
- `Age`: number 0.42–80 (int: no), mean 29.7 | null ×177
- `Fare`: number 0–512.329 (int: no), mean 32.2
...
First 5 rows: (table)
```

**A 1,400-line TypeScript file (38,753 tokens) → 2,300 tokens:** `token-shredder convert strings.ts -Q "how does truncate work"`

````text
## Declarations (1438 lines)
export function isFalsyOrWhitespace(str: string | undefined): boolean
// Helper to produce a string with a variable number of arguments.
export function format(value: string, ...args: any[]): string
...                                          ← every function: signature + first line of its doc

## Relevant to "how does truncate work"
### export function truncate(value: string, maxLength: number, ...) (lines 106-117)
```ts
export function truncate(value: string, maxLength: number, suffix = Ellipsis): string {
	if (value.length <= maxLength) {
		return value;
	...                                          ← the matching function in full
```
````

## Use

```bash
token-shredder convert paper.pdf                  # writes paper.md, prints how many tokens it saved
token-shredder convert paper.pdf -o -             # print the markdown instead (default when piped)
token-shredder convert paper.pdf --copy           # put it on the clipboard
token-shredder convert https://example.com/post   # a web page: just the article
cat data.json | token-shredder convert -          # from stdin

token-shredder convert app.py --max-tokens 2000   # the most detail that fits in 2,000 tokens
token-shredder convert app.py -Q "how are retries handled"   # outline + the matching parts in full

token-shredder batch ./src --max-tokens 20000 --copy          # a whole folder within 20k tokens
token-shredder batch ./docs -o ./docs-md                       # one .md per file
```

`batch` reads folders recursively and skips hidden folders, dependency/build folders (`node_modules`, `venv`, `dist`, ...) and files named like secrets. With `-o -` or `--copy` it produces one document with a `<file path="...">` block per file. Every option: [docs/USAGE.md](docs/USAGE.md).

## How it works

**Detail levels.** `-d 1` to `-d 5`; the default is 3. Higher always means more content, for every format, and a summary is never larger than the full file.

| Level | Code | Data (CSV, JSON, Excel, ...) | Web pages | PDF, Word, text |
|---|---|---|---|---|
| 1 | public names | column/field names and types | headings | headings |
| 2 | + signatures | + counts and ranges | + paragraphs, lists | + first sentence of each paragraph |
| **3** | **+ first line of each doc comment** | **+ examples, category counts, one line per record** | **+ tables; reference lists dropped** | **the full text, cleaned up** |
| 4 | + full doc comments | all data, compacted | + link URLs, references | + page markers, speaker notes |
| 5 | the file itself | the file itself | the raw HTML | the raw extracted text |

"Cleaned up" means broken lines and split words are rejoined and page headers, footers and page numbers are removed. "One line per record" is a short index such as `7651: <issue title> [2 comments, 2026-11-21, by …]` or `react: 17.0.2`. Per-format details: [docs/DETAIL_LEVELS.md](docs/DETAIL_LEVELS.md).

**Token budget** (`--max-tokens N`, `-t N`). Picks the highest level that fits. For a folder the budget is shared: small files stay whole, big ones split the rest. If nothing fits, the output is cut and marked `[... truncated ...]`.

**Question** (`--query "..."`, `-Q`). Splits the file(s) into functions, sections, rows or records, ranks them by how well their words match your question, and adds the best ones in full after the outline. This is plain keyword matching — fast and offline, but it won't find a part that uses different words than your question.

**Credentials.** Well-known API key, token and private-key formats are replaced by `[REDACTED: kind]`, and `.env` values are never shown. This catches common mistakes; it is not a secret scanner, so still check what you paste. `--keep-secrets` turns it off.

Tokens are counted with tiktoken (`cl100k_base`), which is close to but not the same as Claude's tokenizer.

## Formats

PDF, Word (`.docx`), PowerPoint (`.pptx`), Excel (`.xlsx`), HTML, Markdown, text, CSV/TSV, JSON, JSONL, JSON5, YAML, TOML, INI, XML, SVG, SQL, GraphQL, Protobuf, CSS, `.env`, logs, Dockerfile, Makefile, `.gitignore`, shell scripts, and code: Python, JavaScript/TypeScript, Java, Go, Rust, C/C++. Not supported: scanned PDFs and images (no OCR), audio/video, `.doc`/`.xls`/`.ppt`. Details: [docs/FILE_FORMATS.md](docs/FILE_FORMATS.md).

## How well it works

Default level, tokens counted with tiktoken. "Plain text" is what you'd otherwise paste: the extracted text of a PDF/Word file, the visible text of a web page, the file itself for code and data.

| File | Plain text | MarkItDown | Token Shredder |
|---|---:|---:|---:|
| arXiv paper (PDF, 15 pages) | 10,168 | 12,175 | 9,640 |
| Wikipedia article (HTML) | 27,535 | 71,099 | 9,684 |
| `requests/sessions.py` (Python) | 7,336 | — | 1,288 |
| 10 GitHub issues (JSON) | 15,234 | — | 1,115 |
| 86,343-row CSV, 8.8 MB | 3,841,232 | — | 887 |

PDFs and Word files only get slightly smaller at the default level (they are cleaned, not summarised); use `-d 2` or a budget for more. Code and data shrink a lot because the output is an outline or a summary.

**Do the answers survive?** In a small self-run test, a model (Claude Sonnet) answered 60 questions about 12 files twice: once from MarkItDown's output and once from Token Shredder's, without knowing which was which. A second model graded the answers blind.

- Both got **52 of 60** right. Token Shredder used **7× fewer tokens** (166k vs 1.2M).
- One file decided the tie: a lockfile MarkItDown makes 831k tokens long, too big to give the model at all. Without it, MarkItDown did better: 52/55 against 47/55.
- Token Shredder's misses were "how does this function work inside?" questions; with `-Q` set to the question it got 5 of those 6. MarkItDown's misses were exact counts in a large table.

Full tables, caveats and how to reproduce them: [docs/BENCHMARKS.md](docs/BENCHMARKS.md).

## When not to use it

- **You need every word or every row.** Use [MarkItDown](https://github.com/microsoft/markitdown), which converts faithfully, or `-d 5`.
- **Scanned PDFs, images, audio, complex PDF tables.** Use MarkItDown or [Docling](https://github.com/docling-project/docling) (OCR, layout models).
- **Packing a whole repository with exact parsers for every language.** Use [Repomix](https://github.com/yamadashy/repomix) `--compress` or [Aider's repo map](https://aider.chat/docs/repomap.html).

## Limitations

The ones that matter most:

- **Code outlines drop function bodies.** Use `-Q "your question"` for the relevant functions, or `-d 5` for the whole file.
- **Outlines for languages other than Python are pattern-based**, not parsed, and can miss unusual declarations.
- **Data summaries drop most individual values.** The per-record index covers a few hundred records; `-d 4` gives all the data.
- **No OCR**, and PDF tables come out as plain lines of text.
- **`-Q` is keyword matching**, not semantic search.
- **Token counts are estimates**; keep 10–20% margin near a hard limit.

Everything else (web page edge cases, encodings, caching, very large folders, ...): [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

## Python API

```python
from token_shredder import convert_file, batch_convert

r = convert_file("paper.pdf", max_tokens=4000, query="training setup",
                 write_output=False, show_metrics=False)
r.markdown        # the output
r.output_tokens   # its size (and r.source_tokens: the plain-text size)
r.detail_level    # the level that was used
r.warnings        # notes: truncation, redactions, query matches, ...
```

`batch_convert(folder, max_tokens=..., query=..., write_output=False)` returns one result per file. Reference: [docs/API.md](docs/API.md). There is also an optional HTTP API: `pip install "token-shredder[api]"`, then `uvicorn token_shredder.api:app` (no authentication; keep it on localhost).

## Development

```bash
pip install -e ".[dev]"
python -m pytest
python benchmarks/robustness.py <folder>     # run every file through all levels and check the invariants
```

[CHANGELOG.md](CHANGELOG.md) · [CONTRIBUTING.md](CONTRIBUTING.md) · MIT licence ([LICENSE](LICENSE))
