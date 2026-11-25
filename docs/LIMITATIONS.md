# Known gaps and limitations

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
