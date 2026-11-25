# Token Shredder - CLI Examples

## Basic CLI Usage

```bash
# Install
pip install token-shredder

# Convert a PDF
token-shredder convert document.pdf

# Convert with options
token-shredder convert document.pdf --detail-level 2 --output output.md

# Batch convert
token-shredder batch ./documents --output ./converted

# Analyze file
token-shredder analyze document.pdf

# Version
token-shredder version
```

## Python API Usage

```python
from token_shredder import convert_file, get_converter, detect_file_format

# Convert a file
result = convert_file(
    "document.pdf",
    output_path="output.md",
    detail_level=3,
    preserve_images=False
)

print(f"Tokens saved: {result.tokens_saved} ({result.tokens_saved_pct}%)")
print(f"Quality: {result.quality_score}")
```

## REST API

```bash
# Start server
uvicorn token_shredder.api:app --reload

# Convert via API
curl -X POST "http://localhost:8000/convert" \\
  -F "file=@document.pdf" \\
  -F "detail_level=3"
```

## Batch Processing

```bash
# Convert supported files in a directory
token-shredder batch ./reports --output ./converted --workers 4

# Lowest detail level (names and headings only)
token-shredder batch ./docs --detail-level 1 --output ./summary
```

## Caveman Integration

```bash
# Step 1: Shred the file
token-shredder convert presentation.pptx --output pres.md

# Step 2: In Claude Code, enable caveman
# /caveman

# Step 3: Paste the markdown
# Caveman shortens Claude's replies; Shredder shortens the input. See docs/BENCHMARKS.md for numbers.
```
