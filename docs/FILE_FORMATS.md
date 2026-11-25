# Token Shredder - Supported Formats

## Converters

### PDF (.pdf)
- Extracts text via pypdf, then cleans it: split words healed, wrapped lines joined into paragraphs, running headers/footers and page numbers removed
- Headings come from the PDF bookmarks when there are any, else from numbered headings ("3.2 Scaled Dot-Product Attention")
- Level 1 = outline only, 2 = + first sentence of each paragraph, 3 = full text, 4 = + page markers, 5 = raw extraction
- Tables come out as plain text lines; no OCR

### DOCX (.docx)
- Parses via python-docx, body in document order (paragraphs and tables interleaved)
- Heading styles become `#` headings, list styles become lists, tables become markdown tables
- Level 1 = headings, 2 = + first sentence of each paragraph, 3 = full text, 4 = + header/footer text

### PPTX (.pptx)
- Parses via python-pptx (text boxes, tables and grouped shapes)
- Each slide is a `## Slide N: title` heading; bullets are kept
- Level 1 = slide titles, 2 = + first line of each text box, 3 = all slide text, 4 = + speaker notes

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
- A dict with many keys and similar values (npm `packages`, OpenAPI `paths`, `dependencies`) is described as a "map of N entries" with example keys and a profile of its values instead of being listed key by key
- Constant fields show as `= value`; URLs, ids and long text get one example, short text up to three
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

### XML (.xml)
- Level 1: element outline (tags with counts); 2: + attribute names and a profile of repeated elements; 3: + values, with repeated records (RSS `<item>`, Maven `<dependency>`) as one line each (`groupId:artifactId:version`); 4: all values, compact
- Namespaces are shown as `prefix:name`. Output is never larger than the file; a file that does not parse is returned as is

### YAML (.yaml, .yml)
- Multi-document files (`---`) are read in full; Kubernetes documents are labelled by `kind` and name
- Level 1: top-level keys per document; 2: nested key outline; 3: compact YAML with values (short collections inline, long strings cut, long lists of mappings profiled); 4: all values
- `on:`/`yes`/`no` stay text (not booleans), unknown tags such as `!Ref` are accepted. Never larger than the file

### TOML (.toml)
- Levels 1-2: tables and key names; 3: + short values; 4: + long values. Never larger than the file

### HTML (.html)
- Parses via BeautifulSoup
- Removes scripts, styles, navigation, header/footer, forms
- Keeps headings, paragraphs, lists and tables in page order
- Link URLs and citation markers only at `-d 4`

### Text (.txt)
- Cleans plain text and RFC-style documents: healed hyphenation, joined wrapped lines, removed page headers/footers, collapsed spaces; no file path is added to the output
- Detects numbered section headings for level 1 and 2; lists, code and tables are never joined with prose

### Markdown (.md)
- Levels 1-3 remove badges, images, HTML comments and tags (their text stays), link URLs (the link text stays) and reference definitions; code blocks and tables are untouched
- Level 1 = headings, 2 = + first sentence of each paragraph, 4 = the original with whitespace normalised, 5 = the original file

## Detail Levels

See [DETAIL_LEVELS.md](DETAIL_LEVELS.md).

## Output Format

Markdown (.md). There is no `--format` option.

See [BENCHMARKS.md](BENCHMARKS.md) for measured numbers.
