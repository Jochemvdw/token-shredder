"""
token_shredder - Text Converter
Converts plain text files to optimized markdown
"""
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.utils.logger import setup_logger

logger = setup_logger(__name__)


class TextConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.txt']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='text',
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        markdown_parts = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()

            lines = text.splitlines()
            markdown_parts.append(f"# {file_path}")
            markdown_parts.append("")

            # Try to detect structure
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue

                # Detect potential headings (short lines ending with :)
                if len(line) < 60 and line.endswith(':'):
                    markdown_parts.append(f"## {line[:-1]}")
                # Detect numbered lists
                elif line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                    markdown_parts.append(line)
                # Detect bullet points
                elif line.startswith(('- ', '* ', '• ')):
                    markdown_parts.append(line)
                else:
                    markdown_parts.append(line)
                markdown_parts.append("")

        except Exception as e:
            logger.error(f"Error reading text: {e}")
            markdown_parts.append(f"[Error: {e}]")

        return "\n".join(markdown_parts)

    def get_file_info(self, file_path: str) -> dict:
        try:
            with open(file_path, encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            return {
                'lines': len(lines),
                'words': sum(len(l.split()) for l in lines),
            }
        except:
            return {'lines': 0, 'words': 0}
