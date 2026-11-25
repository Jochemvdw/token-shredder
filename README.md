# Token Shredder

Convert files to compact markdown before you paste them into an LLM prompt.

Token Shredder turns PDF, DOCX, PPTX, HTML, code, JSON and ~25 other formats into markdown. For documents it gives you clean text. For HTML, code and JSON it goes further and **cuts content on purpose**: web pages lose navigation and link URLs, code becomes an outline (signatures + docstrings), JSON becomes a schema with example values. That is where the big token savings come from, and it is the trade-off to know about. One `--detail-level` from 1 (names only) to 5 (full file) controls how much is cut, the same way for every format.

Runs locally. No API key, no model downloads.

> **Status:** alpha (v0.3.0). Feedback and issues welcome.

## Install

```bash
pip install token-shredder        # or: pipx install token-shredder
```

Python 3.10+.

## Use

```bash
token-shredder convert paper.pdf              # writes paper.md and prints a token report
token-shredder convert app.py -o app.md
token-shredder convert data.json -d 4         # all JSON data, minified (default 3 = schema)
token-shredder convert app.py -d 5             # full file, no compression
token-shredder batch ./docs -o ./docs-md   # recursive; report.pdf -> docs-md/report.pdf.md
token-shredder preview page.html              # show output + savings, write nothing
token-shredder convert big.pdf -q             # no report, errors only (-v for progress messages)
```

```python
from token_shredder import convert_file

result = convert_file("paper.pdf", output_path="paper.md", show_metrics=False)
print(result.markdown)
```

## What you get, measured

Real public files at the default detail level, tokens counted with tiktoken `cl100k_base`. "Baseline" is what you would otherwise paste: plain extracted text for PDF/DOCX, the page's plain text for HTML, the raw file for code and JSON. "Words kept" is the share of distinct words (4+ letters) from the baseline still in the output — a rough check of how much content survives.

| File | Baseline | MarkItDown | Token Shredder | vs baseline | Words kept |
|---|---:|---:|---:|---:|---:|
| *Attention Is All You Need* (arXiv PDF, 15 p.) | 10,168 | 12,175 | 10,243 | −1% | 100% |
| IRS form W-9 (PDF) | 9,009 | 9,058 | 9,039 | 0% | 100% |
| Calibre demo document (DOCX) | 2,386 | 2,943 | 2,536 | −6% | 100% |
| Wikipedia "Python" article (HTML; raw page 325,067) | 27,535 | 71,099 | 20,383 | **26%** | 82% |
| `requests/sessions.py` (Python) | 7,336 | — | 1,398 | **81%** | 32% |
| Express `router/index.js` (JS) | 3,859 | — | 223 | **94%** | 17% |
| GitHub issues API, 10 issues (JSON) | 15,234 | — | 966 | **94%** | 13% |
| GitHub repo API response (JSON) | 1,863 | — | 1,523 | **18%** | 100% |

What this means:

- **PDF / DOCX:** about the same size as plain extracted text (DOCX adds list markers and table layout), and 14–16% smaller than MarkItDown's output on the same files. Use it for clean, structured text — not for compression.
- **HTML:** headings, paragraphs, lists and tables in page order; navigation, scripts and link URLs dropped. A third of MarkItDown's size on the Wikipedia page, 26% below the page's plain text.
- **Code:** an outline — classes, methods and functions with signatures and the first docstring paragraph. Good for "what is in this file and how do I call it?", not for editing or debugging (use `-d 5`). Python uses the real parser; other languages use pattern matching.
- **JSON:** a schema with one example value per key; a list of objects is described once. If that would not be smaller than the data, you get the data minified (lossless), as with the repo response above. `-d 4` always gives all the data.

The token report the CLI prints uses the same baseline, except for HTML, where it compares with the raw page. Reproduce the table with [`benchmarks/`](benchmarks/).

## Detail levels

`-d 1` … `-d 5`, default 3. Higher always means more content: 1 = names/headings only, 2 = + signatures/structure, 3 = + docstrings, examples and tables, 4 = + full docs, JSON data, link URLs, 5 = the full file. Per format: [docs/DETAIL_LEVELS.md](docs/DETAIL_LEVELS.md).

## Formats

PDF, DOCX, PPTX, XLSX, HTML, Markdown, TXT, CSV, JSON, JSON5, YAML, TOML, INI, XML, SVG, SQL, GraphQL, Protobuf, `.env`, logs, Dockerfile, Makefile, `.gitignore`, shell scripts, and code (Python, JS/TS/JSX/TSX, Java, Go, Rust, C/C++). See [docs/FILE_FORMATS.md](docs/FILE_FORMATS.md).

## Related tools

- [MarkItDown](https://github.com/microsoft/markitdown) and [Docling](https://github.com/docling-project/docling) aim for a faithful conversion. Docling also does layout analysis, tables and OCR with ML models. If you need every word or accurate tables from scanned PDFs, use those.
- [Repomix](https://github.com/yamadashy/repomix) `--compress` (npm) and [Aider's repo map](https://aider.chat/docs/repomap.html) produce code outlines for whole repositories with real parsers (tree-sitter). Token Shredder works per file and also covers documents and JSON.
- [Caveman](https://github.com/JuliusBrussee/caveman) shortens Claude's replies, so it works on the output side. Token Shredder works on the input side.

## Known limitations

- No OCR: scanned PDFs give little or no text.
- PDF tables come out as plain text lines.
- Outlines for languages other than Python come from pattern matching and can miss unusual declarations.
- Detail levels don't change PDF/DOCX output (except PPTX speaker notes at 4).
- YAML, TOML, INI, SQL, XML and similar files are summarised at levels 1–4 (structure, short values); use `-d 5` for the full file.
- Converting a `.md` file writes `name.shredded.md`; the input is never overwritten.
- `convert` caches results for an hour in `~/.token-shredder/cache`; use `--no-cache` to skip it.

## HTTP API

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
