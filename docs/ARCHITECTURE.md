# Token Shredder - Architecture

## High-Level Architecture

```
File Input (PDF, DOCX, PPTX, Python, JSON, etc)
    ↓
Format Detection & Routing
    ↓
Converter (format-specific extraction)
    ↓
Processors (dedup, minify, optimize)
    ↓
Markdown Generation
    ↓
Metrics Calculation
    ↓
Output + Report
```

## Components

### Converters (`src/token_shredder/converters/`)
- Format-specific extraction logic
- Each implements BaseConverter interface
- Output: Raw extracted content

### Processors (`src/token_shredder/processors/`)
- Post-processing on extracted content
- Deduplication, minification, optimization
- Composable: chain multiple processors

### Metrics (`src/token_shredder/metrics/`)
- Token counting via tiktoken
- Quality scoring
- Performance analytics

### API Layer (`src/token_shredder/api.py`)
- FastAPI REST server
- Async processing
- File upload support

### CLI (`src/token_shredder/main.py`)
- Typer-based CLI
- Batch processing
- Configuration support

## Data Models

### ConversionResult
- markdown: Output content
- source_file, target_file: Paths
- source_tokens, output_tokens: Token counts
- tokens_saved, tokens_saved_pct: Savings
- quality_score: Semantic preservation
- processing_time_ms: Performance
- pages, images_count, tables_count: Metadata

### ConversionOptions
- detail_level: 1-5
- preserve_images: bool
- embed_images: bool
- include_comments: bool

## Configuration

Config file: `~/.token-shredder/config.yaml`

```yaml
defaults:
  detail_level: 3
  preserve_images: false

performance:
  max_workers: 4
  cache_enabled: true
```

## Error Handling

- Critical: File unreadable, unsupported format → exit with error
- Warning: Partial extraction → log & continue
- Info: Format tips → log & include in report
