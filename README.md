# Token Shredder

**Fit any file, folder or web page into your LLM's context budget.**

```bash
token-shredder batch ./src --max-tokens 20000 --copy   # a whole folder, within 20k tokens, on your clipboard
token-shredder convert https://example.com/article     # just the article, as markdown
token-shredder convert export.csv                      # a 50 MB CSV as a one-page profile
```

Token Shredder turns PDF, DOCX, PPTX, XLSX, HTML, code, JSON/JSONL/CSV and ~25 other formats into compact markdown, offline. It **cuts content on purpose** where that helps a model: web pages lose navigation and boilerplate, code becomes an outline (signatures + docstrings), data files become a profile (columns, types, ranges, example values). One `--detail-level` from 1 (names only) to 5 (full file) sets how much is kept — or give it a token budget and it picks the level for you.

Runs locally. No API key, no model downloads.

> **Status:** alpha (v0.4.0). Feedback and issues welcome.

## Install

```bash
pip install token-shredder        # or: pipx install token-shredder
uvx token-shredder convert file.pdf   # run without installing
```

Python 3.10+.

## Use

```bash
# One file, URL or stdin
token-shredder convert paper.pdf               # writes paper.md, prints a token report
token-shredder convert paper.pdf -o -          # markdown to stdout (also the default when piped)
token-shredder convert paper.pdf --copy        # straight to the clipboard
token-shredder convert https://docs.python.org/3/whatsnew/3.13.html
curl -s https://api.github.com/repos/python/cpython | token-shredder convert -
token-shredder convert app.py -d 5             # full file, no compression

# Token budget: the highest detail level that fits, truncated (and marked) if nothing fits
token-shredder convert app.py --max-tokens 2000

# Folders (recursive). With a budget it is shared: small files stay whole, big ones get the rest.
token-shredder batch ./docs -o ./docs-md                    # one .md per file
token-shredder batch ./src --max-tokens 20000 -o - | pbcopy  # one document, <file path="..."> blocks

# Machine-readable output for scripts and tools
token-shredder convert data.json --json        # {"markdown": ..., "output_tokens": ..., ...}
```

`-q` prints only errors, `-v` shows progress. When the output goes to stdout, the token report goes to stderr.

```python
from token_shredder import convert_file, batch_convert

result = convert_file("paper.pdf", max_tokens=4000, write_output=False, show_metrics=False)
print(result.detail_level, result.output_tokens)
print(result.markdown)
```

## What you get, measured

Real public files at the default detail level, tokens counted with tiktoken `cl100k_base`. "Baseline" is what you would otherwise paste: plain extracted text for PDF/DOCX, the page's plain text for HTML, the raw file for code and JSON. "Words kept" is the share of distinct words (4+ letters) from the baseline still in the output — a rough check of how much content survives.

| File | Baseline | MarkItDown | Token Shredder | vs baseline | Words kept |
|---|---:|---:|---:|---:|---:|
| *Attention Is All You Need* (arXiv PDF, 15 p.) | 10,168 | 12,175 | 9,640 | **5%** | 99% |
| IRS form W-9 (PDF) | 9,009 | 9,058 | 8,417 | **7%** | 100% |
| Calibre demo document (DOCX) | 2,386 | 2,943 | 2,525 | −6% | 100% |
| Wikipedia "Python" article (HTML; raw page 325,067) | 27,535 | 71,099 | 9,684 | **65%** | 58% ¹ |
| `requests/sessions.py` (Python) | 7,336 | — | 1,288 | **82%** | 28% |
| Express `router/index.js` (JS) | 3,859 | — | 223 | **94%** | 17% |
| GitHub issues API, 10 issues (JSON) | 15,234 | — | 1,115 | **93%** | 20% |
| GitHub repo API response (JSON) | 1,863 | — | 915 | **51%** | 52% |
| Airport codes, 86,343 rows, 8.8 MB (CSV) | 3,841,232 | — | 887 | **99.98%** | profile |

¹ The article text is kept; the reference list, "See also" and external links are dropped at the default level (`-d 4` keeps them).

Across a wider test set of 98 public files (papers, RFCs, READMEs, web pages, code in 6 languages, lock files, feeds, spreadsheets, configs; `benchmarks/robustness.py`), the default level produces 492,638 tokens from 17.3 million, with no crashes, budget overruns or size inversions. 

What this means:

- **PDF / DOCX / text:** cleaned text — broken lines and split words rejoined, page headers/footers and page numbers removed — 5–7% below plain extraction and 14–21% below MarkItDown. For real compression use a lower level: `-d 2` gives headings plus the first sentence of each paragraph (about 40% of the text), `-d 1` the outline.
- **HTML:** the main content in page order — headings, paragraphs, lists, tables; navigation, cookie banners, scripts, link URLs and reference sections dropped. 14% of MarkItDown's size on the Wikipedia page.
- **Code:** an outline — classes, methods and functions with signatures and the first sentence of each doc comment; private helpers listed without docs. Good for "what is in this file and how do I call it?", not for editing or debugging (use `-d 5`). Python uses the real parser; other languages use pattern matching.
- **Data files (JSON, JSONL, CSV, Excel):** a profile — row count, and per field its type, range, mean, length, example values and category counts — plus an index line per record (issue number + title, package + version; up to a few hundred records). An 8.8 MB CSV becomes one page. If the profile would not be smaller than the data, you get the data itself (minified JSON / CSV), as with the repo response above. `-d 4` always gives all the data.

The token report the CLI prints uses the same baseline, except for HTML, where it compares with the raw page. Reproduce the table with [`benchmarks/`](benchmarks/).

## Head-to-head with MarkItDown: answers vs tokens

60 questions about 12 files (papers, a Wikipedia page, an RFC, code, a CSV, an npm lockfile, GitHub API JSON, configs), written from the original files. A model (Claude Sonnet) answered them twice, once from each tool's output, without knowing which tool made which text; a separate model graded the answers blind against reference answers.

| | Tokens given to the model | Fully correct | Partly correct | Not answerable |
|---|---:|---:|---:|---:|
| MarkItDown | 1,201,114 | 52 / 60 | 3 | 5 ¹ |
| Token Shredder (default level) | **165,892** | **52 / 60** | 4 | 4 |
| *without the lockfile* | | | | |
| MarkItDown | 369,915 | 52 / 55 | 3 | 0 |
| Token Shredder | **141,989** | 47 / 55 | 4 | 4 |

¹ MarkItDown's version of the 831k-token lockfile doesn't fit in a 200k context window, so those 5 questions couldn't be asked.

Where each one loses:
- **Token Shredder** misses implementation details of code ("how does `truncate` work inside?" — the outline has signatures, not bodies) and record-level facts it doesn't index (which issue has the most comments). Use `-d 5` for code you need to read in full.
- **MarkItDown** gives the model the whole CSV table, but a model reading 40k tokens of rows can't count exactly (survivors, passengers per class) — Token Shredder's profile states those counts. And very large files don't fit at all.

Caveats: one answering model, 60 questions, written by a model; the answering model read parts of four long files (three MarkItDown, one Token Shredder) instead of the whole text. Questions and grades: [`benchmarks/qa/`](benchmarks/qa/).

## Detail levels

`-d 1` … `-d 5`, default 3. Higher always means more content: 1 = names/headings only, 2 = + signatures/structure, 3 = + docstrings, examples and tables, 4 = + full docs, JSON data, link URLs, 5 = the full file. Per format: [docs/DETAIL_LEVELS.md](docs/DETAIL_LEVELS.md).

## Formats

PDF, DOCX, PPTX, XLSX, HTML, Markdown, TXT, CSV, JSON, JSON5, YAML, TOML, INI, XML, SVG, SQL, GraphQL, Protobuf, `.env`, logs, Dockerfile, Makefile, `.gitignore`, shell scripts, and code (Python, JS/TS/JSX/TSX, Java, Go, Rust, C/C++). See [docs/FILE_FORMATS.md](docs/FILE_FORMATS.md).

## Related tools

- [MarkItDown](https://github.com/microsoft/markitdown) and [Docling](https://github.com/docling-project/docling) aim for a faithful conversion. Docling also does layout analysis, tables and OCR with ML models. If you need every word or accurate tables from scanned PDFs, use those.
- [Repomix](https://github.com/yamadashy/repomix) `--compress` (npm) and [Aider's repo map](https://aider.chat/docs/repomap.html) produce code outlines for whole repositories with real parsers (tree-sitter). Token Shredder works per file and also covers documents and JSON.
- [Caveman](https://github.com/JuliusBrussee/caveman) shortens Claude's replies, so it works on the output side. Token Shredder works on the input side.

## Known limitations

- PDF tables come out as plain text lines.
- Outlines for languages other than Python come from pattern matching and can miss unusual declarations.
- PDF outlines (`-d 1`) come from bookmarks, else from font size, bold text and numbering; forms and slide-style PDFs get only a minimal outline.
- No OCR yet: scanned PDFs and images give little or no text.
- YAML, TOML, INI, SQL, XML and similar files are summarised at levels 1–4 (structure, short values); use `-d 5` for the full file.
- Converting a `.md` file writes `name.shredded.md`; the input is never overwritten.
- `batch` skips hidden folders and dependency/build folders (`node_modules`, `venv`, `dist`, `build`, `target`, `vendor`, ...).
- Text that isn't UTF-8 is read as Windows-1252 (UTF-16 and BOMs are detected).
- Output is meant for AI models, so well-known credential formats (API keys, tokens, private keys) are replaced by `[REDACTED: kind]`, `.env` values are never shown, and `batch` skips files named like secrets/credentials. `--keep-secrets` turns redaction off. This is a safety net, not a guarantee.
- `convert` caches results for an hour in `~/.token-shredder/cache`; use `--no-cache` to skip it.

## HTTP API (optional)

```bash
pip install "token-shredder[api]"
uvicorn token_shredder.api:app
curl -F file=@paper.pdf "http://127.0.0.1:8000/convert?detail_level=3"
```

## Development

```bash
pip install -e ".[dev]"
python -m pytest
```

## License

MIT — see [LICENSE](LICENSE).
