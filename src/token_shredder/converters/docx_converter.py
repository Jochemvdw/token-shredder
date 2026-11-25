"""
token_shredder - DOCX Converter
Converts Word documents to markdown with streaming support
"""
import re
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

            prev_list = False
            for para in doc.paragraphs:
                style = para.style.name.lower() if para.style else ""
                is_list = style.startswith('list') and bool(para.text.strip())
                if prev_list and not is_list:
                    markdown_parts.append("")
                prev_list = is_list

                if style.startswith('heading') and style.replace('heading', '').strip().isdigit():
                    level = int(style.replace('heading', '').strip())
                    text = para.text
                    if text:
                        markdown_parts.append(f"{'#' * level} {text}")
                        markdown_parts.append("")
                elif para.text.strip() and style.startswith('list'):
                    indent = ''
                    m = re.search(r'(\d+)$', style)
                    if m and int(m.group(1)) > 1:
                        indent = '  ' * (int(m.group(1)) - 1)
                    marker = '1.' if 'number' in style else '-'
                    markdown_parts.append(f"{indent}{marker} {para.text.strip()}")
                elif para.text.strip():
                    markdown_parts.append(para.text)
                    markdown_parts.append("")

            if prev_list:
                markdown_parts.append("")

            # Tables
            for table in doc.tables:
                md_table = self._table_to_markdown(table)
                if md_table:
                    markdown_parts.append("")
                    markdown_parts.append(md_table)
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
        esc = lambda t: t.strip().replace('\r', ' ').replace('\n', ' ').replace('|', '\\|')
        header = [esc(cell.text) for cell in table.rows[0].cells]
        md.append("| " + " | ".join(header) + " |")
        md.append("| " + " | ".join(["---"] * len(header)) + " |")

        # Rows
        for row in table.rows[1:]:
            cells = [esc(cell.text) for cell in row.cells]
            md.append("| " + " | ".join(cells) + " |")

        return "\n".join(md)

    def _count_images(self, file_path: str) -> int:
        try:
            doc = Document(file_path)
            return len(doc.inline_shapes)
        except:
            return 0
