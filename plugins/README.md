# Token Shredder - Custom Plugins

## Creating Custom Converters

Extend the BaseConverter class to create custom converters.

```python
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions


class MyFormatConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.myformat']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        with open(file_path) as f:
            content = f.read()
        return ConversionResult(
            markdown=self._process(content),
            source_file=file_path,
            target_file=file_path.replace('.myformat', '.md'),
            format='myformat',
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        with open(file_path) as f:
            return self._process(f.read())

    def get_file_info(self, file_path: str) -> dict:
        return {'custom': True}

    def _process(self, content: str) -> str:
        # Your processing logic
        return f"# Converted\n{content}"
```

## Creating Custom Processors

Extend the processor base classes.

```python
from token_shredder.processors.deduplicator import Deduplicator


class MyProcessor(Deduplicator):
    def process(self, content: str) -> str:
        # Custom processing
        return super().process(content)
```

## Registering Plugins

Plugins are automatically discovered if placed in the plugins directory.
