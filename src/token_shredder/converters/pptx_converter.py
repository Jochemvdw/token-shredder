"""
token_shredder - PPTX Converter
Converts PowerPoint files to markdown with streaming support
"""
from pptx import Presentation
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.prose import Block, first_sentence, levels_output, tidy
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
        level = options.detail_level
        try:
            prs = Presentation(file_path)
            blocks = []
            notes_blocks = []
            for i, slide in enumerate(prs.slides):
                title = ""
                try:
                    if slide.shapes.title is not None:
                        title = " ".join(slide.shapes.title.text.split())
                except Exception:
                    title = ""
                head = f"Slide {i+1}: {title}" if title else f"Slide {i+1}"
                blocks.append(Block('heading', head, 2 if title else 3))  # untitled slides sit lower
                for shape in self._iter_shapes(slide.shapes):
                    if slide.shapes.title is not None and shape.shape_id == slide.shapes.title.shape_id:
                        continue
                    for text, is_table in self._shape_text(shape):
                        if is_table:
                            blocks.append(Block('table', text))
                            continue
                        lines = [l.strip() for l in text.split('\n') if l.strip()]
                        items = []
                        for line in lines:
                            if line.startswith(('•', '-', '*')):
                                items.append(f"- {line[1:].strip()}")
                            else:
                                items.append(line)
                        if items:
                            blocks.append(Block('list', "\n".join(items)))
                try:
                    notes = slide.notes_slide.notes_text_frame.text if slide.has_notes_slide else ""
                except Exception:
                    notes = ""
                if notes.strip():
                    notes_blocks.append(Block('extra', f"### Slide {i+1} Notes\n{notes.strip()}"))
            if not blocks:
                return "[No text content found in this presentation]"
            if notes_blocks:
                blocks = blocks + [Block('extra', "## Speaker Notes")] + notes_blocks
            if level >= 5:
                return self._render_full(blocks)
            return levels_output(lambda lv: self._render(blocks, lv), level)
        except Exception as e:
            logger.debug(f"Error reading PPTX: {e}")
            return f"[Error reading PPTX: {e}]"

    @staticmethod
    def _render(blocks: list, level: int) -> str:
        """Levels: 1 slide titles, 2 + first line of each text box, 3 all slide text, 4 + notes."""
        out = []
        for b in blocks:
            if b.kind == 'heading':
                out.append(("#" * b.level) + " " + b.text)
            elif b.kind == 'list':
                lines = b.text.split("\n")
                if level == 2:
                    out.append(first_sentence(lines[0].lstrip("- "), 200) if not lines[0].startswith("- ")
                               else "- " + first_sentence(lines[0][2:], 200))
                elif level >= 3:
                    out.append("\n".join(tidy(l) if not l.startswith("- ") else "- " + tidy(l[2:]) for l in lines))
            elif b.kind == 'table' and level >= 3:
                out.append(b.text)
            elif b.kind == 'extra' and level >= 4:
                out.append(b.text)
        if level == 1:
            titled = [b for b in blocks if b.kind == 'heading' and ": " in b.text]
            if not titled:
                # no slide has a title: use the first line of text on each slide
                out, slide = [], None
                for b in blocks:
                    if b.kind == 'heading':
                        out.append(("#" * b.level) + " " + b.text)
                        slide = b
                    elif b.kind == 'list' and slide is not None:
                        out.append("- " + first_sentence(b.text.split("\n")[0].lstrip("- "), 120))
                        slide = None
        return "\n\n".join(o for o in out if o.strip()) if level >= 2 else "\n".join(o for o in out if o.strip())

    @staticmethod
    def _render_full(blocks: list) -> str:
        out = []
        for b in blocks:
            if b.kind == 'heading':
                out.append(("#" * b.level) + " " + b.text)
            else:
                out.append(b.text)
        return "\n\n".join(out)

    def _iter_shapes(self, shapes):
        for shape in shapes:
            if getattr(shape, "shape_type", None) == 6 and hasattr(shape, "shapes"):  # group
                yield from self._iter_shapes(shape.shapes)
            else:
                yield shape

    @staticmethod
    def _shape_text(shape):
        """(text, is_table) pairs for a shape: text frames and tables."""
        if getattr(shape, "has_table", False) and shape.has_table:
            rows = []
            esc = lambda t: " ".join(t.split()).replace('|', '\\|')
            for r_i, row in enumerate(shape.table.rows):
                cells = [esc(c.text) for c in row.cells]
                rows.append("| " + " | ".join(cells) + " |")
                if r_i == 0:
                    rows.append("| " + " | ".join(["---"] * len(cells)) + " |")
            return [("\n".join(rows), True)] if rows else []
        if getattr(shape, "has_text_frame", False) and shape.has_text_frame and shape.text_frame.text.strip():
            return [(shape.text_frame.text.strip(), False)]
        return []

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
