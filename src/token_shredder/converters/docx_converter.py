"""
token_shredder - DOCX Converter
Converts Word documents to markdown with streaming support
"""
import re
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.prose import Block, levels_output, render_blocks
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
        level = options.detail_level
        try:
            doc = Document(file_path)
            blocks = self._blocks(doc)
            if not blocks:
                return "[No text content found in this document]"
            blocks_all = blocks + self._extras(doc)
            if level >= 5:
                return render_blocks(blocks_all, 4, raw=True) + "\n"
            return levels_output(lambda lv: render_blocks(blocks_all, lv), level) + "\n"
        except Exception as e:
            logger.error(f"Error reading DOCX: {e}")
            return f"[Error reading DOCX: {e}]"

    def _blocks(self, doc) -> list:
        blocks = []
        has_title = False
        for child in doc.element.body.iterchildren():
            tag = child.tag.rsplit('}', 1)[-1]
            if tag == 'tbl':
                md_table = self._table_to_markdown(Table(child, doc))
                if md_table:
                    blocks.append(Block('table', md_table))
                continue
            if tag != 'p':
                continue
            para = Paragraph(child, doc)
            text = para.text
            if not text.strip():
                continue
            style = para.style.name.lower() if para.style is not None and para.style.name else ""
            head = style.replace('heading', '').strip()
            if style.startswith('heading') and head.isdigit():
                blocks.append(Block('heading', text.strip(), max(1, int(head))))
            elif style == 'title':
                blocks.append(Block('title', text.strip(), 1))
                has_title = True
            elif style.startswith('list'):
                indent = ''
                m = re.search(r'(\d+)$', style)
                if m and int(m.group(1)) > 1:
                    indent = '  ' * (int(m.group(1)) - 1)
                marker = '1.' if 'number' in style else '-'
                blocks.append(Block('list', f"{indent}{marker} {text.strip()}"))
            else:
                blocks.append(Block('para', text.strip()))
        if not has_title:
            try:
                title = (doc.core_properties.title or "").strip()
            except Exception:
                title = ""
            if title and not any(b.kind in ('heading', 'para') and b.text == title for b in blocks):
                blocks.insert(0, Block('title', title, 1))
        return blocks

    @staticmethod
    def _extras(doc) -> list:
        """Page headers and footers: dropped below level 4."""
        seen, parts = set(), []
        try:
            for section in doc.sections:
                for part in (section.header, section.footer):
                    text = "\n".join(p.text.strip() for p in part.paragraphs if p.text.strip())
                    if text and text not in seen:
                        seen.add(text)
                        parts.append(text)
        except Exception as e:
            logger.info(f"Could not read DOCX headers/footers: {e}")
        return [Block('extra', "Header/footer: " + " | ".join(parts))] if parts else []

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
