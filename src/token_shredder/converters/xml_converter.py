"""
token_shredder - XML Converter
Converts XML files to markdown
"""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.utils.logger import setup_logger

logger = setup_logger(__name__)


class XMLConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.xml']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='xml',
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        markdown_parts = []
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            markdown_parts.append(f"# XML Document: {file_path}")
            markdown_parts.append(f"- Root: {root.tag}")
            markdown_parts.append("")

            markdown_parts.append(self._element_to_markdown(root, ""))

        except Exception as e:
            logger.error(f"Error reading XML: {e}")
            markdown_parts.append(f"[Error reading XML: {e}]")

        return "\n".join(markdown_parts)

    def _element_to_markdown(self, elem, prefix="") -> str:
        md = []
        indent = "  "
        md.append(f"## {elem.tag}")
        if elem.attrib:
            md.append(f"Attributes: {elem.attrib}")
        md.append("")

        # Text content
        text = (elem.text or '').strip()
        if text:
            md.append(f"{indent}Content: {text}")
            md.append("")

        # Children
        for child in elem:
            md.append(self._element_to_markdown(child, prefix + indent))

        return "\n".join(md)

    def get_file_info(self, file_path: str) -> dict:
        try:
            tree = ET.parse(file_path)
            return {'root': tree.getroot().tag, 'elements': len(list(tree.getroot().iter()))}
        except:
            return {'root': 'unknown', 'elements': 0}
