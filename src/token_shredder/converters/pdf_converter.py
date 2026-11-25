"""
token_shredder - PDF Converter
Converts PDF files to markdown: clean text at levels 1-4, raw extraction at 5
"""
import math
import re
from collections import Counter
import pypdf
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.prose import Block, build_blocks, numbered_heading, _KNOWN_HEADS, levels_output, render_blocks, strip_running, _key
from token_shredder.utils.logger import setup_logger

logger = setup_logger(__name__)

_BOLD_RE = re.compile(r"bold|black|heavy|semibold|demi", re.I)
_LARGER = 1.15          # a line this much bigger than body text is a heading candidate
_MAX_HEAD_WORDS = 12


def _scale(m) -> float:
    return math.sqrt(abs(m[0] * m[3] - m[1] * m[2]))


class _RunCollector:
    """pypdf visitor_text callback: groups text runs into visual lines with size and boldness."""

    def __init__(self):
        self.lines = []      # per line: [y, [(text, size, bold)]]
        self.failed = False

    def __call__(self, text, cm, tm, font_dict, font_size):
        try:
            if not text or not text.strip():
                return
            size = float(font_size or 0) * _scale(tm) * _scale(cm)
            y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
            name = str((font_dict or {}).get("/BaseFont", ""))
            bold = bool(_BOLD_RE.search(name))
            if self.lines and abs(self.lines[-1][0] - y) < 1.5 and "\n" not in text:
                self.lines[-1][1].append((text, size, bold))
            else:
                self.lines.append([y, [(text, size, bold)]])
        except Exception:
            self.failed = True


def collect_lines(collector: "_RunCollector") -> list:
    """[(text, size, bold)] per visual line; size = the size covering most characters."""
    out = []
    for _, runs in collector.lines:
        text = "".join(r[0] for r in runs).replace("\n", " ")
        text = " ".join(text.split())
        if not text:
            continue
        by_size = Counter()
        for t, sz, _b in runs:
            by_size[round(sz * 2) / 2] += len(t.strip())
        size = by_size.most_common(1)[0][0]
        bold = all(b for t, _sz, b in runs if t.strip())
        out.append((text, size, bold))
    return out


def rank_typography_headings(page_lines: list) -> dict:
    """page_lines: per page [(text, size, bold)]. Returns {key: depth} (depth 0 = top heading level),
    or {} when sizes are unusable."""
    allines = [l for page in page_lines for l in page]
    chars = Counter()
    for text, size, _b in allines:
        if size > 0:
            chars[size] += len(text)
    if not chars:
        return {}
    body = chars.most_common(1)[0][0]
    if body < 3:
        return {}
    anchor = None   # first line on page 1 that is clearly a section heading
    if page_lines:
        for i, (text, _sz, _b) in enumerate(page_lines[0]):
            if numbered_heading(text) is not None or text.lower().rstrip(":") in _KNOWN_HEADS:
                anchor = i
                break
    top0 = max((l[1] for l in page_lines[0]), default=0) if page_lines else 0
    cands = []   # (text, size or None for bold-only)
    for pi, page in enumerate(page_lines):
        for li, (text, size, bold) in enumerate(page):
            if pi == 0 and anchor is not None and li < anchor and size < top0 - 0.01:
                continue  # author / affiliation lines between the title and the abstract
            words = text.split()
            if (not words or len(words) > _MAX_HEAD_WORDS or len(text) > 110 or len(text) < 3
                    or text.endswith((".", ",", ";")) or sum(c.isalpha() for c in text) < 3
                    or not (text[0].isupper() or text[0].isdigit())
                    or re.fullmatch(r"[\d\s.,:/()-]+", text)):
                continue
            if bold and size < body * _LARGER and pi == 0 and numbered_heading(text) is None \
                    and text.lower().rstrip(":") not in _KNOWN_HEADS:
                continue  # bold names/affiliations on the first page
            if size >= body * _LARGER:
                cands.append((pi, text, size))
            elif bold and size >= body * 0.9:
                cands.append((pi, text, 0.0))
    # Forms (tax forms, applications) are full of short bold/large labels ("Sign", "Here",
    # "Tax and"): if most candidates are 1–2 word fragments that aren't numbered or known
    # section names, typography says "form", not "headings".
    fragments = [c for c in cands
                 if len(c[1].split()) <= 2 and numbered_heading(c[1]) is None
                 and c[1].lower().rstrip(":") not in _KNOWN_HEADS]
    if len(cands) >= 8 and len(fragments) > 0.4 * len(cands):
        return {}
    total = sum(len(p) for p in page_lines)
    if total and len(cands) > max(8, 0.1 * total):
        return {}  # forms and slides: typography is not a reliable heading signal
    # Only treat a size as a level if it recurs or is the title-like top size
    sizes = Counter(c[2] for c in cands if c[2] > 0)
    level_sizes = sorted((s for s, n in sizes.items()), reverse=True)
    # a size seen on one page only once and larger than all others is the document title
    title_sizes = set()
    if level_sizes and sizes[level_sizes[0]] <= 2 and len(level_sizes) > 1 \
            and all(c[0] == 0 for c in cands if c[2] == level_sizes[0]):
        title_sizes.add(level_sizes[0])
    level_sizes = [s for s in level_sizes if s not in title_sizes][:3]
    has_bold = any(c[2] == 0.0 for c in cands)
    bold_depth = min(len(level_sizes), 2)
    if any(c[2] == 0.0 and (numbered_heading(c[1]) or (0,))[0] == 1 and numbered_heading(c[1]) for c in cands):
        bold_depth = 0  # bold unnumbered lines sit beside bold "1. Section" lines
    out = {}
    for _pi, text, size in cands:
        if size in title_sizes:
            continue
        if size > 0:
            # nearest level size at or below
            depth = next((i for i, s in enumerate(level_sizes) if size >= s - 0.01), None)
            if depth is None:
                continue
        else:
            depth = bold_depth
        k = _key(text)
        if k and k not in out:
            out[k] = depth
    # bold-only lines that repeat many times are labels, not headings
    if has_bold:
        bold_counts = Counter(_key(c[1]) for c in cands if c[2] == 0.0)
        for k, n in bold_counts.items():
            if n > 3 and k in out:
                del out[k]
    # numbered headings keep their own depth
    for c in cands:
        if numbered_heading(c[1]) is not None:
            out.pop(_key(c[1]), None)
    return out


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
            page_texts = []
            page_lines = []
            for page in reader.pages:
                if level >= 5:
                    page_texts.append(page.extract_text() or "")
                    continue
                col = _RunCollector()
                try:
                    page_texts.append(page.extract_text(visitor_text=col) or "")
                except Exception:
                    col = _RunCollector()
                    col.failed = True
                    page_texts.append(page.extract_text() or "")
                page_lines.append([] if col.failed else collect_lines(col))
            self._typo_lines = page_lines

            if level >= 5:
                # Full extraction, no clean-up.
                for i, text in enumerate(page_texts):
                    if text.strip():
                        markdown_parts.extend([f"## Page {i+1}", "", text, ""])
            else:
                body = self._prose(reader, page_texts, level, getattr(self, '_typo_lines', None))
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
            logger.debug(f"Error reading PDF: {e}")
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

    def _prose(self, reader, page_texts: list, level: int, typo_lines=None) -> str:
        pages = [t.split("\n") for t in page_texts]
        outline = self._outline(reader)
        known = {}
        for depth, title in outline:
            known.setdefault(_key(title), depth + 1)
        typo = {}
        if not outline and typo_lines:
            try:
                typo = rank_typography_headings(typo_lines)
            except Exception as e:
                logger.info(f"Typography heading detection failed: {e}")
                typo = {}
            for k, depth in typo.items():
                known.setdefault(k, depth + 1)
        entries = strip_running(pages, mark_pages=True)
        blocks = build_blocks(entries, known, mark_pages=True, loose_headings=False if typo else None)
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
