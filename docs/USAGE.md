# Usage Guide

## Command Line Interface

### Convert a File

```bash
token-shredder convert myfile.py

# Specify output file
token-shredder convert input.pdf --output output.md

# Adjust detail level (1-5)
token-shredder convert code.py --detail-level 3

# Preview without writing
token-shredder preview myfile.py

# Show token counts and a quality score
token-shredder quality myfile.py
```

### Batch Convert

```bash
token-shredder batch ./documents --output ./output
```

### Analyze a File

```bash
token-shredder analyze myfile.py
```

## Python API

```python
from token_shredder import convert_file

# Basic usage
result = convert_file("document.pdf")
print(result.markdown)
print(f"Tokens saved: {result.tokens_saved}")

# With options (keyword arguments)
result = convert_file(
    "code.py",
    detail_level=3,
    preserve_images=False,
    embed_images=False,
    include_comments=True,
)
```

## Detail Levels

1 = smallest (names only), 3 = default, 5 = full content. Higher always means more content, for every format. Per-format details: [DETAIL_LEVELS.md](DETAIL_LEVELS.md).

## Supported Formats

| Format | Extension | What you get |
|--------|-----------|--------------|
| Python | .py | An outline: imports, classes, methods, functions with signatures and the first docstring paragraph. No function bodies, so not for editing or debugging (use `-d 5`). |
| JavaScript/TypeScript, Java, Go, Rust | .js, .ts, .tsx, .jsx, ... | Declaration lines with the first doc-comment line. Pattern-based, not a full parser. |
| HTML | .html | Page text in order (headings, paragraphs, lists, tables); navigation, scripts and link URLs removed. |
| PDF | .pdf | Plain text with light markdown structure; about the same token count as plain extracted text. |
| DOCX | .docx | Same as PDF. |
| PPTX | .pptx | Same as PDF. |
| JSON | .json | At the default level 3, a schema with one example value per key. `-d 4` gives all data minified, `-d 5` the original file. |

Other formats (CSS, YAML, Markdown, SQL, INI/TOML and more) are also handled; output for those is not described here. See [BENCHMARKS.md](BENCHMARKS.md) for measured numbers.

## New Features

### Preview Command
Preview conversion without writing files:
```bash
token-shredder preview myfile.py
```

### Quality Analysis
Analyze expected savings before conversion:
```bash
token-shredder quality myfile.py
```

This shows:
- Input/output token counts
- Token reduction for that file
- Quality score (0-100): a rough heuristic based on structure, not a measure of how much meaning survived
- File metadata (lines, functions, classes)
