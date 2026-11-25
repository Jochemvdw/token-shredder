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
- Default detail level 3: schema (keys, types, one example value per key); every list of objects is profiled once (presence counts, number ranges, string lengths, examples, enums)
- `--detail-level 4` gives all the data, minified; `5` the original file

### JSONL / NDJSON (.jsonl, .ndjson)
- Streamed line by line; level 3 gives a per-field profile (types, ranges, examples, enums) of all rows
- Blank lines are skipped; lines that are not valid JSON are counted and reported, not fatal
- `--detail-level 4`: one minified object per line; `5`: the original file

### CSV / TSV (.csv, .tsv)
- Default level 3: row/column counts, a per-column profile and the first 5 rows as a table, however large the file is
- `--detail-level 1` column names only, `2` adds types and ranges, `4` and `5` all data as CSV. Delimiter (`,` `;` tab `|`) is detected

### Excel (.xlsx)
- Same levels as CSV, applied per sheet (header = first non-empty row); `-d 4` and `-d 5` give full tables for every sheet
- Uncalculated formulas fall back to their formula text

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
