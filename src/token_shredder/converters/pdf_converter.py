"""
token_shredder - PDF Converter
Converts PDF files to semantic markdown with streaming support
"""
import pypdf
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
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
        try:
            reader = pypdf.PdfReader(file_path)
            num_pages = len(reader.pages)

            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    markdown_parts.append(f"## Page {i+1}")
                    markdown_parts.append("")
                    markdown_parts.append(text)
                    markdown_parts.append("")

            # Handle images
            if options.preserve_images:
                markdown_parts.append("\n## Images")
                for i in range(num_pages):
                    if hasattr(reader.pages[i], '_images') and reader.pages[i]._images:
                        markdown_parts.append(f"- Page {i+1}: {len(reader.pages[i]._images)} images")

        except Exception as e:
            logger.error(f"Error reading PDF: {e}")
            markdown_parts.append(f"[Error reading PDF: {e}]")

        return "\n".join(markdown_parts)

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
