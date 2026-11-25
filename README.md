# Token Shredder

**Fit any file, folder or web page into your LLM's context budget — and keep the parts your question needs.**

```bash
token-shredder batch ./src --max-tokens 20000 --copy            # a whole folder in 20k tokens, on your clipboard
token-shredder convert app.ts -Q "how does truncate work"       # outline + the full code of truncate()
token-shredder convert https://example.com/article              # just the article, as markdown
token-shredder convert export.csv                               # a 50 MB CSV as a one-page profile
```

Token Shredder converts PDF, Word, PowerPoint, Excel, web pages, code, JSON/CSV and ~25 other formats into compact markdown for pasting into Claude, ChatGPT or any other model. It runs locally: no API key, no AI model. Nothing leaves your machine, except when you give it a URL to fetch and once on first use, when the tokenizer library (tiktoken) downloads its ~1.7 MB encoding file.

> **Status:** alpha (v0.4.0). It works and is tested on ~120 real files, but the interface may still change. Feedback and issues welcome.

## What it does

- **Shrinks what a model doesn't need, on purpose.** Web pages lose navigation, cookie banners and reference lists. Code becomes an outline (signatures + first line of each doc comment). Data files become a profile (columns, types, ranges, counts, examples) plus one index line per record. PDFs and Word files are cleaned (broken lines rejoined, page headers/footers removed).
- **One dial for everything.** `--detail-level 1..5`: 1 = names/headings only, 3 = default, 5 = the full file. Higher always means more, for every format.
- **Token budgets.** `--max-tokens N` picks the most detailed output that fits — for one file, or shared over a whole folder (small files stay whole, big ones split the rest).
- **Question-aware.** `--query "..."` adds the parts that match your question in full — functions, document sections, CSV rows, JSON records — next to the outline. Keyword ranking, no AI model involved.
- **Pipes and clipboard.** Reads files, URLs or stdin; writes a `.md` file, stdout (`-o -`, the default when piped), the clipboard (`--copy`) or JSON (`--json`).
- **Safe to paste.** Well-known credential formats (API keys, tokens, private keys) are replaced by `[REDACTED: kind]`, `.env` values are never shown, and `batch` skips files named like secrets.

## When to use it — and when not

| Use Token Shredder when… | Use something else when… |
|---|---|
| a file or folder doesn't fit, or costs too much, in a prompt | you need every word or every row: [MarkItDown](https://github.com/microsoft/markitdown) converts faithfully |
| you have big data files (CSV, JSON, lockfiles, Excel) | you need OCR, image descriptions or audio: MarkItDown, [Docling](https://github.com/docling-project/docling) |
| you want a web page's article without the clutter | you need accurate tables from complex PDFs: Docling |
| you want "the shape of this codebase" plus the code for one question | you want a whole repo packed with exact parsers: [Repomix](https://github.com/yamadashy/repomix) `--compress`, [Aider's repo map](https://aider.chat/docs/repomap.html) |

## Install

```bash
pip install token-shredder            # or: pipx install token-shredder
uvx token-shredder convert file.pdf   # run without installing
```

Python 3.10–3.13 on macOS, Linux and Windows (Windows is tested in CI only).

## Use

```bash
# One file, URL or stdin
token-shredder convert paper.pdf                 # writes paper.md and prints a token report
token-shredder convert paper.pdf -o -            # markdown to stdout
token-shredder convert paper.pdf --copy          # straight to the clipboard
token-shredder convert https://docs.python.org/3/whatsnew/3.13.html
curl -s https://api.github.com/repos/python/cpython | token-shredder convert -
token-shredder convert app.py -d 5               # the full file, no compression

# A token budget: the most detailed output that fits (cut and marked if nothing fits)
token-shredder convert app.py --max-tokens 2000

# A question: outline + the best-matching parts in full
token-shredder convert rfc9110.txt -Q "what does the TRACE method do"
token-shredder batch ./src -Q "how are retries handled" -t 20000 -o - | pbcopy

# Folders (recursive; skips hidden, node_modules, venv, dist, build, ...)
token-shredder batch ./docs -o ./docs-md                       # one .md per file
token-shredder batch ./src --max-tokens 20000 -o -             # one document with <file path="..."> blocks

# For scripts and tools
token-shredder convert data.json --json          # {"markdown": ..., "output_tokens": ..., "notes": [...]}
```

`-q` prints only errors, `-v` shows progress. When the output goes to stdout, the token report goes to stderr. Exit code 1 means something failed (with a one-line message); `batch` still outputs the files that worked.

```python
from token_shredder import convert_file, batch_convert

r = convert_file("paper.pdf", max_tokens=4000, query="training setup",
                 write_output=False, show_metrics=False)
print(r.detail_level, r.output_tokens, r.warnings)
print(r.markdown)
```

## What you get, measured

Real public files at the default level; tokens counted with tiktoken `cl100k_base`. "Baseline" is what you'd otherwise paste: plain extracted text for PDF/DOCX, the page's plain text for HTML, the raw file for everything else.

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

¹ The article is kept; the reference list, "See also" and external links are dropped (`-d 4` keeps them).

On a wider set of 98 public files (papers, RFCs, READMEs, web pages, code in 6 languages, lockfiles, feeds, spreadsheets, configs) the default level gives 492,638 tokens from 17.3 million, with no crashes, budget overruns or size inversions (`benchmarks/robustness.py`). 18 real government Word/PowerPoint/Excel files pass the same checks.

### Do the answers survive? Head-to-head with MarkItDown

60 questions about 12 of those files, written from the originals. A model (Claude Sonnet) answered them from each tool's output without knowing which tool made which text; a separate model graded blind against reference answers.

| | Tokens given to the model | Fully correct | Partly correct | Not answerable |
|---|---:|---:|---:|---:|
| MarkItDown | 1,201,114 | 52 / 60 | 3 | 5 ¹ |
| Token Shredder (default level) | **166,711** | **54 / 60** ² | 3 | 3 |
| *without the lockfile* | | | | |
| MarkItDown | 369,915 | **52 / 55** | 3 | 0 |
| Token Shredder | **142,808** | 49 / 55 ² | 3 | 3 |

¹ MarkItDown's version of the 831k-token lockfile doesn't fit in a 200k context window, so those questions couldn't be asked.
² The blind run gave 52/60; after the record index gained comment counts, dates and authors, the 5 GitHub-issue questions were re-asked under the same rules and all were answered correctly (graded by us against the references, not blind).

- **Token Shredder loses** on how code works inside ("how does `truncate` work?") — the outline has signatures, not bodies. With `--query` set to the question, 5 of those 6 missed questions were answered correctly (one needed a constant defined elsewhere in the file); again graded by us, not blind.
- **MarkItDown loses** on exact counts in big tables (a model can't count 891 rows of a pasted CSV reliably; the profile states the counts) and on files that don't fit at all.

Caveats: one answering model, 60 questions written by a model, and the answering model read parts of four long files instead of all of it. Questions, references and grades: [`benchmarks/qa/`](benchmarks/qa/).

## Detail levels

| Level | Code | Data (JSON/CSV/XLSX...) | Web pages | PDF / Word / text |
|---|---|---|---|---|
| 1 | public names | field names and types | headings | outline (headings) |
| 2 | + signatures | + counts and ranges | + paragraphs and lists | + first sentence per paragraph |
| **3** (default) | **+ first line of each doc comment** | **+ examples, categories, record index** | **+ tables, no reference lists** | **cleaned full text** |
| 4 | + full doc comments | all data, minified | + link URLs, references | + page markers, notes |
| 5 | the file | the file | the raw HTML | raw extraction |

A summary is never larger than the full file (level 5); if it would be, you get the full file. Details per format: [docs/DETAIL_LEVELS.md](docs/DETAIL_LEVELS.md), formats: [docs/FILE_FORMATS.md](docs/FILE_FORMATS.md).

## Formats

PDF, DOCX, PPTX, XLSX, HTML, Markdown, TXT, CSV/TSV, JSON, JSONL/NDJSON, JSON5, YAML, TOML, INI, XML, SVG, CSS, SQL, GraphQL, Protobuf, `.env`, logs, Dockerfile, Makefile, `.gitignore`, shell scripts, and code: Python, JavaScript/TypeScript (JS, MJS, TS, JSX, TSX), Java, Go, Rust, C/C++.

## Known gaps and limitations

Read this before relying on it.

**Content that is lost or approximate**
- **Code outlines drop function bodies** at levels 1–4. Use `-Q "your question"` to get the relevant functions in full, or `-d 5` for the whole file.
- **Non-Python outlines are pattern-based**, not parsed: unusual syntax, nested classes or macros can be missed. Python uses the real parser.
- **Data profiles drop most individual values** at levels 1–3: the record index shows up to a few hundred records (all top-level entries for lockfiles), and `-d 4` gives all data.
- **PDF tables become plain text lines**; complex layouts (multi-column, forms) may come out in a mixed order.
- **PDF outlines** (`-d 1`) come from bookmarks, else from font size, bold text and numbering. Forms and slide-style PDFs get a minimal outline; headings that wrap over two lines may appear in pieces.
- **De-hyphenation is heuristic**: a word split at a line break is rejoined when both halves look like one word; rarely a real hyphen is removed.
- **Web pages**: "main content" is found with simple rules (`<main>`, `<article>`, boilerplate class names). Unusual page layouts can lose content or keep clutter. JavaScript-rendered pages show what the server sends, not what a browser renders.
- **XML/YAML that doesn't parse** is returned in full with a note, not summarised.

**Not supported (yet)**
- **No OCR**: scanned PDFs and images give little or no text. (Planned as an optional extra.)
- **No images, audio or video**, no EPUB, no email formats. Old binary Office formats (`.doc`, `.xls`, `.ppt`) aren't supported — save them as `.docx`/`.xlsx`/`.pptx` first.
- **`--query` is keyword ranking**, not semantic search: if your question uses different words from the file ("where did the value come from" vs `get_parameter_source`), it can miss. Using the names from the file helps.

**Practical**
- **First run needs internet once**: tiktoken downloads its encoding file (~1.7 MB) and caches it. In an offline environment, set `TIKTOKEN_CACHE_DIR` to a folder that already has it.
- **Token counts are estimates** (tiktoken `cl100k_base`). Claude's tokenizer counts somewhat differently; keep a 10–20% margin near a hard limit.
- **Secret redaction is a safety net, not a scanner**: it only catches well-known formats (AWS, GitHub, GitLab, Slack, Stripe, OpenAI/Anthropic, Google, PyPI, npm keys, JWTs, private keys, passwords in URLs). Review what you paste. `--keep-secrets` turns it off.
- **Very large folders**: with `--max-tokens`, if the budget can't give every file ~100 tokens, the most deeply nested files are left out (with a note). Large repos can take tens of seconds.
- **Text that isn't UTF-8** is read as Windows-1252 (UTF-16 and BOMs are detected); other encodings may show wrong characters.
- **`convert` caches results** for an hour in `~/.token-shredder/cache` (`--no-cache` to skip); converting a `.md` file writes `name.shredded.md` so the input is never overwritten.
- **Alpha software**: tested on ~120 real files and ~200 automated tests, but not yet used widely. Windows is covered by CI only.

## HTTP API (optional)

```bash
pip install "token-shredder[api]"
uvicorn token_shredder.api:app
curl -F file=@paper.pdf "http://127.0.0.1:8000/convert?detail_level=3"
```

See [docs/API.md](docs/API.md). The API has no authentication: run it on localhost or behind your own auth.

## Development

```bash
pip install -e ".[dev]"
python -m pytest                              # unit tests
python benchmarks/robustness.py <folder>      # invariants over any folder of real files
```

Changes: [CHANGELOG.md](CHANGELOG.md). Contributing: [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
