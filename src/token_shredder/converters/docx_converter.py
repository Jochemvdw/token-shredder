"""
token_shredder - DOCX Converter
Converts Word documents to markdown with streaming support
"""
from docx import Document
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.utils.logger import setup_logger

logger = setup_logger(__name__)


class DOCXConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.docx']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='docx',
            images_count=self._count_images(file_path),
            tables_count=self._count_tables(markdown),
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        markdown_parts = []
        try:
            doc = Document(file_path)

            for para in doc.paragraphs:
                style = para.style.name.lower() if para.style else ""

                if 'heading' in style:
                    level = int(style.replace('heading ', ''))
                    text = para.text
                    if text:
                        markdown_parts.append(f"{'#' * level} {text}")
                        markdown_parts.append("")
                elif para.text.strip():
                    markdown_parts.append(para.text)
                    markdown_parts.append("")

            # Tables
            for table in doc.tables:
                markdown_parts.append(self._table_to_markdown(table))
                markdown_parts.append("")

        except Exception as e:
            logger.error(f"Error reading DOCX: {e}")
            markdown_parts.append(f"[Error reading DOCX: {e}]")

        return "\n".join(markdown_parts)

    def get_file_info(self, file_path: str) -> dict:
        try:
            doc = Document(file_path)
            return {
                'paragraphs': len(doc.paragraphs),
                'tables': len(doc.tables),
                'images': len(doc.inline_shapes),
            }
        except Exception as e:
            return {'paragraphs': 0, 'tables': 0, 'images': 0}

    def _table_to_markdown(self, table) -> str:
        if not table.rows:
            return ""

        md = []
        # Header
        header = [cell.text.strip() for cell in table.rows[0].cells]
        md.append("| " + " | ".join(header) + " |")
        md.append("| " + " | ".join(["---"] * len(header)) + " |")

        # Rows
        for row in table.rows[1:]:
            cells = [cell.text.strip() for cell in row.cells]
            md.append("| " + " | ".join(cells) + " |")

        return "\n".join(md)

    def _count_images(self, file_path: str) -> int:
        try:
            doc = Document(file_path)
            return len(doc.inline_shapes)
        except:
            return 0
