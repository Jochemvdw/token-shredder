# Token Shredder - Supported Formats

## Converters

### PDF (.pdf)
- Extracts text via pypdf
- Preserves heading hierarchy
- Converts tables to markdown
- References images by page

### DOCX (.docx)
- Parses via python-docx
- Preserves headings, bold, italic
- Converts tables to markdown
- References images

### PPTX (.pptx)
- Parses via python-pptx
- Each slide as level 2 heading
- Extracts speaker notes
- Preserves bullet points

### Python (.py)
- Parses via ast module
- Outline: imports, classes with their methods, functions, signatures and the first docstring paragraph (default level 3)
- Function bodies are dropped; not suitable when the model must edit or debug the code (use `-d 5` for the full file)
- Option to include comments (`--include-comments`)

### JavaScript/TypeScript, Java, Go, Rust (.js, .mjs, .ts, .tsx, .jsx, .java, .go, .rs)
- Outline: declaration lines (functions, classes, methods, arrow functions) with the first line of the doc comment above them
- Found by pattern matching, not a full parser, so unusual syntax can be missed
- Function bodies are dropped; use `-d 5` for the full file

### JSON (.json)
- Default detail level 3: schema (keys, types, one example value per key); lists of objects are described once with the union of their keys
- `--detail-level 4` gives all the data, minified; `5` the original file

### CSV (.csv)
- Converts to markdown tables
- Includes row/column counts

### HTML (.html)
- Parses via BeautifulSoup
- Removes scripts, styles, navigation, header/footer, forms
- Keeps headings, paragraphs, lists and tables in page order
- Link URLs and citation markers only at `-d 4`

### Text (.txt, .md)
- Optimizes plain text
- Detects structure
- Removes excessive blank lines

## Detail Levels

See [DETAIL_LEVELS.md](DETAIL_LEVELS.md).

## Output Format

Markdown (.md). There is no `--format` option.

See [BENCHMARKS.md](BENCHMARKS.md) for measured numbers.
