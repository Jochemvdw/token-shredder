"""
token_shredder - PDF Converter
Converts PDF files to markdown: clean text at levels 1-4, raw extraction at 5
"""
import pypdf
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.prose import Block, build_blocks, levels_output, render_blocks, strip_running, _key
from token_shredder.utils.logger import setup_logger

logger = setup_logger(__name__)


class PDFConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.pdf']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='pdf',
            pages=self._count_pages(file_path),
            images_count=self._count_images(file_path),
            tables_count=self._count_tables(markdown),
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        markdown_parts = []
        level = options.detail_level
        try:
            reader = pypdf.PdfReader(file_path)
            num_pages = len(reader.pages)
            page_texts = [(page.extract_text() or "") for page in reader.pages]

            if level >= 5:
                # Full extraction, no clean-up.
                for i, text in enumerate(page_texts):
                    if text.strip():
                        markdown_parts.extend([f"## Page {i+1}", "", text, ""])
            else:
                body = self._prose(reader, page_texts, level)
                if body:
                    markdown_parts.append(body)
                elif not any(t.strip() for t in page_texts):
                    markdown_parts.append("[No extractable text in this PDF (scanned or image-only?)]")

            # Handle images
            if options.preserve_images and level >= 3:
                markdown_parts.append("\n## Images")
                for i in range(num_pages):
                    if hasattr(reader.pages[i], '_images') and reader.pages[i]._images:
                        markdown_parts.append(f"- Page {i+1}: {len(reader.pages[i]._images)} images")

        except Exception as e:
            logger.error(f"Error reading PDF: {e}")
            markdown_parts.append(f"[Error reading PDF: {e}]")

        return "\n".join(markdown_parts)

    @staticmethod
    def _outline(reader) -> list:
        """Bookmarks as (depth, title), empty when the PDF has none."""
        items = []

        def walk(nodes, depth):
            for node in nodes:
                if isinstance(node, list):
                    walk(node, depth + 1)
                else:
                    title = getattr(node, "title", None)
                    if title and str(title).strip():
                        items.append((depth, " ".join(str(title).split())))
        try:
            walk(reader.outline, 0)
        except Exception as e:  # damaged outline: fall back to heading detection
            logger.info(f"Could not read PDF outline: {e}")
            return []
        return items

    def _prose(self, reader, page_texts: list, level: int) -> str:
        pages = [t.split("\n") for t in page_texts]
        outline = self._outline(reader)
        known = {}
        for depth, title in outline:
            known.setdefault(_key(title), depth + 1)
        entries = strip_running(pages, mark_pages=True)
        blocks = build_blocks(entries, known, mark_pages=True)
        title = None
        try:
            title = " ".join(str((reader.metadata or {}).get("/Title") or "").split())
        except Exception:
            title = None
        if title and len(title) > 3 and title.lower() not in ("untitled", "microsoft word") \
                and not title.lower().endswith((".pdf", ".doc", ".docx", ".tex", ".dvi")) \
                and not any(b.kind == "title" for b in blocks):
            blocks.insert(0, Block("title", title, 1))
        if not blocks:
            return ""

        def render(lv: int) -> str:
            if lv == 1 and outline:
                head = [f"# {title}"] if title and len(title) > 3 else []
                return "\n".join(head + ["#" * min(d + 2, 6) + " " + t for d, t in outline])
            return render_blocks(blocks, lv)
        return levels_output(render, level)

    def get_file_info(self, file_path: str) -> dict:
        try:
            reader = pypdf.PdfReader(file_path)
            return {
                'pages': len(reader.pages),
                'images': 0,
                'tables': 0,
            }
        except Exception as e:
            return {'pages': 0, 'images': 0, 'tables': 0}

    def _count_pages(self, file_path: str) -> int:
        try:
            reader = pypdf.PdfReader(file_path)
            return len(reader.pages)
        except:
            return 0

    def _count_images(self, file_path: str) -> int:
        return 0
