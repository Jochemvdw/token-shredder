"""A converter class, used directly.

There is no plugin registration: token-shredder finds converters through the
CONVERTERS dict in token_shredder/converters/__init__.py. To make `convert` and
`batch` handle a new extension, add a module to the package and an entry there
(see CONTRIBUTING.md). This file only shows the interface and calls it by hand.
"""
import sys

from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionOptions, ConversionResult


class CustomConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.custom']

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        with open(file_path, encoding="utf-8") as f:
            return f"# Custom Format\n{f.read()}"

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        return ConversionResult(
            markdown=self.convert_to_markdown(file_path, options),
            source_file=file_path,
            target_file=file_path.replace('.custom', '.md'),
            format='custom',
        )

    def get_file_info(self, file_path: str) -> dict:
        with open(file_path, encoding="utf-8") as f:
            return {'lines': len(f.readlines())}


if __name__ == "__main__":
    path = sys.argv[1]  # any text file
    result = CustomConverter().convert(path, ConversionOptions(detail_level=3))
    print(result.markdown)
