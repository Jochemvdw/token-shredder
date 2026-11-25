# Token Shredder - Advanced Usage

## Custom Processors

Processors are plain classes with a `process(content)` method (see `src/token_shredder/processors/`).

```python
class CustomProcessor:
    def process(self, content: str) -> str:
        # Custom processing logic
        return content
```

## Custom Converters

Create custom converters by extending BaseConverter.

```python
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions

class CustomConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.custom']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        # Custom conversion logic
        return ConversionResult(...)
```

## Configuration

### Config File

Location: `~/.token-shredder/config.yaml`

```yaml
defaults:
  detail_level: 3
  preserve_images: false

performance:
  max_workers: 4
  cache_enabled: true

api:
  port: 8000
```

### Environment Variables

```bash
export TOKEN_SHREDDER_DETAIL=3
export TOKEN_SHREDDER_WORKERS=4
export TOKEN_SHREDDER_CACHE=true
```

## Caching

Enable caching for repeated conversions:

```bash
token-shredder convert document.pdf --cache
```

## Performance Tuning

- Increase workers for batch: `--workers 8`
- Lower detail level for speed: `--detail-level 2`
- Disable processors: `--no-deduplicate --no-minify`
