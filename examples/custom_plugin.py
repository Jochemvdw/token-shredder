"""
token_shredder - Custom Plugin Example
"""
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions


class CustomConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.custom']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        with open(file_path) as f:
            content = f.read()
        return ConversionResult(
            markdown=f"# Custom Format\n{content}",
            source_file=file_path,
            target_file=file_path.replace('.custom', '.md'),
            format='custom',
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        with open(file_path) as f:
            return f.read()

    def get_file_info(self, file_path: str) -> dict:
        return {'lines': 0}


# Register and use
from token_shredder.converters import get_converter
# get_converter will automatically use CustomConverter for .custom files
