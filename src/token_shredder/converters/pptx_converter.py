"""
token_shredder - PPTX Converter
Converts PowerPoint files to markdown with streaming support
"""
from pptx import Presentation
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.utils.logger import setup_logger

logger = setup_logger(__name__)


class PPTXConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.pptx']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='pptx',
            pages=self._count_slides(file_path),
            images_count=self._count_images(file_path),
            tables_count=self._count_tables(markdown),
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        markdown_parts = []
        try:
            prs = Presentation(file_path)

            for i, slide in enumerate(prs.slides):
                markdown_parts.append(f"## Slide {i+1}")

                # Title
                if slide.shapes.title:
                    title_text = slide.shapes.title.text.strip()
                    if title_text:
                        markdown_parts.append(f"### {title_text}")

                # Content
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        if shape != slide.shapes.title:
                            text = shape.text.strip()
                            if text:
                                # Bullet points
                                for line in text.split('\n'):
                                    line = line.strip()
                                    if line:
                                        if line.startswith(('•', '-', '*')):
                                            markdown_parts.append(f"- {line[1:].strip()}")
                                        else:
                                            markdown_parts.append(line)
                markdown_parts.append("")

            # Speaker notes
            if options.detail_level >= 4:
                markdown_parts.append("## Speaker Notes")
                for i, slide in enumerate(prs.slides):
                    notes = slide.notes_slide.notes_text_frame.text if slide.notes_slide else ""
                    if notes.strip():
                        markdown_parts.append(f"### Slide {i+1} Notes")
                        markdown_parts.append(notes)
                        markdown_parts.append("")

        except Exception as e:
            logger.error(f"Error reading PPTX: {e}")
            markdown_parts.append(f"[Error reading PPTX: {e}]")

        return "\n".join(markdown_parts)

    def get_file_info(self, file_path: str) -> dict:
        try:
            prs = Presentation(file_path)
            return {
                'slides': len(prs.slides),
                'images': sum(1 for s in prs.slides for shape in s.shapes if hasattr(shape, 'image')),
                'tables': 0,
            }
        except Exception as e:
            return {'slides': 0, 'images': 0, 'tables': 0}

    def _count_slides(self, file_path: str) -> int:
        try:
            prs = Presentation(file_path)
            return len(prs.slides)
        except:
            return 0

    def _count_images(self, file_path: str) -> int:
        try:
            prs = Presentation(file_path)
            return sum(1 for s in prs.slides for shape in s.shapes if hasattr(shape, 'image'))
        except:
            return 0
