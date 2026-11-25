"""
token_shredder - SVG Converter
Converts SVG files to markdown description
"""
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.utils.logger import setup_logger
import re

logger = setup_logger(__name__)


class SVGConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.svg']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='svg',
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        markdown_parts = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            markdown_parts.append(f"# SVG: {file_path}")
            markdown_parts.append("")

            # Extract basic info
            width = re.search(r'width=["\']([^"\']+)["\']', content)
            height = re.search(r'height=["\']([^"\']+)["\']', content)
            viewBox = re.search(r'viewBox=["\']([^"\']+)["\']', content)

            markdown_parts.append("## Properties")
            if width:
                markdown_parts.append(f"- Width: {width.group(1)}")
            if height:
                markdown_parts.append(f"- Height: {height.group(1)}")
            if viewBox:
                markdown_parts.append(f"- ViewBox: {viewBox.group(1)}")
            markdown_parts.append("")

            # Count elements
            elements = re.findall(r'<([a-zA-Z]+)', content)
            element_counts = {}
            for elem in elements:
                if elem not in ['svg', 'xmlns']:
                    element_counts[elem] = element_counts.get(elem, 0) + 1

            markdown_parts.append("## Elements")
            for elem, count in sorted(element_counts.items(), key=lambda x: -x[1]):
                markdown_parts.append(f"- `<{elem}>`: {count}")
            markdown_parts.append("")

            # Extract paths/important elements
            if options.detail_level >= 3:
                markdown_parts.append("## Structure")
                for elem, count in element_counts.items():
                    if count <= 5:  # Only show elements with few instances
                        matches = re.findall(f'<{elem}[^>]*>', content)
                        for m in matches[:3]:
                            attrs = re.findall(r'[\w-]+=["\'][^"\']+["\']', m)
                            markdown_parts.append(f"  - {m[:100]}..." if len(m) > 100 else f"  - {m}")
                markdown_parts.append("")

        except Exception as e:
            logger.debug(f"Error reading SVG: {e}")
            markdown_parts.append(f"[Error reading SVG: {e}]")

        return "\n".join(markdown_parts)

    def get_file_info(self, file_path: str) -> dict:
        try:
            with open(file_path, encoding='utf-8', errors='replace') as f:
                content = f.read()
            elements = re.findall(r'<([a-zA-Z]+)', content)
            return {'elements': len(elements), 'size': len(content)}
        except:
            return {'elements': 0, 'size': 0}
