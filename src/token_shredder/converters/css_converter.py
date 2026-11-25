"""
token_shredder - CSS Converter
Converts CSS files to semantic markdown
"""
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.utils.logger import setup_logger

logger = setup_logger(__name__)


class CSSConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.css']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='css',
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        markdown_parts = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            markdown_parts.append(f"# CSS Stylesheet: {file_path}")
            markdown_parts.append("")

            # Parse CSS rules
            lines = content.splitlines()
            current_selector = None
            current_properties = []

            for line in lines:
                line = line.strip()
                if not line or line.startswith(('/*', '*', '*/')):
                    continue

                # Check for selector
                if line.endswith(':') and not line.startswith((' ', '\t')):
                    # Save previous rule
                    if current_selector:
                        markdown_parts.append(f"## {current_selector}")
                        for prop in current_properties:
                            markdown_parts.append(f"- {prop}")
                        markdown_parts.append("")
                    current_selector = line.rstrip(':').strip()
                    current_properties = []
                elif current_selector and line:
                    # Property
                    if '{' in line or '}' in line:
                        continue
                    if ':' in line:
                        current_properties.append(line)

            # Save last rule
            if current_selector:
                markdown_parts.append(f"## {current_selector}")
                for prop in current_properties:
                    markdown_parts.append(f"- {prop}")
                markdown_parts.append("")

        except Exception as e:
            logger.error(f"Error reading CSS: {e}")
            markdown_parts.append(f"[Error reading CSS: {e}]")

        return "\n".join(markdown_parts)

    def get_file_info(self, file_path: str) -> dict:
        try:
            with open(file_path) as f:
                content = f.read()
            selectors = content.count('{')
            return {'selectors': selectors, 'lines': len(content.splitlines())}
        except:
            return {'selectors': 0, 'lines': 0}
