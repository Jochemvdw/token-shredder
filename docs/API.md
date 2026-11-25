# Token Shredder - API Reference

## REST API

### POST /convert

Convert uploaded file to markdown.

**Parameters**:
- file: UploadFile (required)
- detail_level: int (default: 3)
- preserve_images: bool (default: false)
- deduplicate: bool (default: true)

**Response:**
```json
{
  "markdown": "# Converted content...",
  "source_file": "document.pdf",
  "target_file": "document.md",
  "format": "pdf",
  "source_tokens": 8450,
  "output_tokens": 3820,
  "tokens_saved": 4630,
  "tokens_saved_pct": 54.8,
  "quality_score": 98.0,
  "processing_time_ms": 2300,
  "pages": 12,
  "images_count": 8,
  "tables_count": 3,
  "warnings": []
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "version": "0.3.0"
}
```

## Python API

### convert_file(file_path, **options)

Convert a file to markdown.

Returns: ConversionResult

### get_converter(format_type)

Get converter for format.

Returns: BaseConverter or None

### detect_file_format(file_path)

Detect format from extension.

Returns: str

### batch_convert(directory, output_dir=None, detail_level=3, workers=4, preserve_images=False, quiet=False)

Batch convert directory. Import from `token_shredder.main`.

Returns: List[ConversionResult]

### TokenCounter

- estimate(text: str) -> int
- estimate_file(file_path: str) -> int

### QualityScorer

- score(converted: str, original: str) -> float

### Deduplicator

- process(content: str, threshold: float = 0.9) -> str

### CodeMinifier

- process(content: str, language: str = 'python') -> str

### StructureOptimizer

- process(content: str) -> str
