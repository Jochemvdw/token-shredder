"""
token_shredder - HTML Converter
Converts HTML to markdown
"""
import re

from bs4 import BeautifulSoup, NavigableString, Tag
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.utils.logger import setup_logger

logger = setup_logger(__name__)


class HTMLConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.html', '.htm']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='html',
            tables_count=self._count_tables(markdown),
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    # Detail levels for HTML:
    #   1  headings only
    #   2  + paragraphs, lists, quotes, code blocks
    #   3  + tables (default)
    #   4  + link URLs and citation markers
    #   5  raw HTML (handled in main.convert_file)
    _DROP = ['script', 'style', 'noscript', 'nav', 'footer', 'header', 'aside', 'form',
             'button', 'svg', 'iframe', 'template']
    _BLOCKS = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'pre', 'table', 'blockquote',
               'dt', 'dd']
    _INLINE = {'a', 'abbr', 'b', 'bdi', 'cite', 'em', 'i', 'kbd', 'mark', 'q', 's', 'samp', 'small',
               'span', 'strong', 'sub', 'sup', 'time', 'u', 'var'}
    _CONTAINERS = {'li', 'table', 'blockquote', 'pre', 'dd', 'dt', 'p'}

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        level = options.detail_level
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
        except Exception as e:
            logger.error(f"Error reading HTML: {e}")
            return f"[Error reading HTML: {e}]"

        for tag in soup(self._DROP):
            tag.decompose()
        for tag in soup.find_all(attrs={'role': ['navigation', 'banner', 'contentinfo', 'search']}):
            tag.decompose()
        if level < 4:
            for sup in soup.find_all('sup'):
                if re.fullmatch(r'\s*\[[^\]]{1,12}\]\s*', sup.get_text()):
                    sup.decompose()

        parts = []
        title = soup.find('title')
        if title and title.get_text(strip=True):
            parts += [f"# {title.get_text(strip=True)}", ""]

        root = self._main_content(soup) if level <= 4 else (soup.body or soup)
        if level <= 4:
            for tag in root.find_all(self._is_boilerplate):
                if not tag.decomposed:
                    tag.decompose()
        emitted = set()
        for el in root.find_all(self._BLOCKS):
            containers = self._CONTAINERS - {'li'} if el.name == 'li' else self._CONTAINERS
            if any(id(p) in emitted for p in el.parents if p.name in containers):
                continue
            name = el.name
            if name[0] == 'h' and name[1:].isdigit():
                text = self._inline(el, level)
                if text:
                    parts += ["", f"{'#' * int(name[1])} {text}"]
                continue
            if level < 2:
                continue
            if name == 'table':
                if level >= 3:
                    md = self._table_to_markdown(el, level)
                    if md:
                        parts += ["", md, ""]
                emitted.add(id(el))
                continue
            if name == 'pre':
                parts += ["```", el.get_text().rstrip(), "```"]
            elif name == 'li':
                text = self._inline(el, level)
                if text:
                    depth = len([p for p in el.parents if p.name in ('ul', 'ol')]) - 1
                    parts.append(f"{'  ' * max(depth, 0)}- {text}")
            else:
                text = self._inline(el, level)
                if text:
                    prefix = "> " if name == 'blockquote' else ""
                    parts += ["", prefix + text]
            emitted.add(id(el))

        return re.sub(r'\n{3,}', '\n\n', "\n".join(parts)).strip() + "\n"

    _BOILERPLATE = {'nav', 'navbar', 'navbox', 'menu', 'sidebar', 'breadcrumb', 'breadcrumbs',
                    'cookie', 'cookies', 'consent', 'banner', 'advert', 'advertisement', 'ads',
                    'promo', 'newsletter', 'share', 'sharing', 'social', 'related', 'comments',
                    'footer', 'toc', 'skip', 'popup', 'modal', 'subscribe', 'mw-editsection'}

    def _is_boilerplate(self, tag) -> bool:
        if not isinstance(tag, Tag) or tag.name in ('html', 'body', 'main', 'article'):
            return False
        words = set()
        for value in (tag.get('id') or '', *(tag.get('class') or [])):
            words.update(w for w in re.split(r'[\s_-]+', str(value).lower()) if w)
            words.add(str(value).lower())
        return bool(words & self._BOILERPLATE)

    @staticmethod
    def _main_content(soup):
        """The page's main content: <main>, role=main, or the biggest <article>."""
        main = soup.find('main') or soup.find(attrs={'role': 'main'})
        if main and len(main.get_text(strip=True)) > 200:
            return main
        articles = soup.find_all('article')
        if articles:
            best = max(articles, key=lambda a: len(a.get_text(strip=True)))
            if len(best.get_text(strip=True)) > 200:
                return best
        return soup.body or soup

    def _inline(self, el, level: int, top: bool = True) -> str:
        """Text of el in reading order, skipping nested lists/tables/code blocks."""
        out = []
        for child in el.children:
            if type(child) is NavigableString:  # skips comments, CDATA, doctype
                out.append(str(child))
            elif not isinstance(child, Tag):
                continue
            elif child.name in ('ul', 'ol', 'table', 'pre'):
                continue
            elif child.name == 'a' and level >= 4 and child.get('href', '').startswith('http'):
                text = self._inline(child, level)
                out.append(f" [{text}]({child['href']}) " if text else "")
            elif child.name == 'br':
                out.append(" ")
            elif child.name == 'code':
                out.append(f"`{child.get_text()}`")
            elif child.name in self._INLINE:
                out.append(self._inline(child, level, top=False))
            else:
                # div, p, etc. inside cells or items: keep words apart.
                out.append(" " + self._inline(child, level, top=False) + " ")
        text = re.sub(r'\s+', ' ', "".join(out))
        return text.strip() if top else text

    def get_file_info(self, file_path: str) -> dict:
        try:
            with open(file_path, encoding='utf-8', errors='replace') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            return {
                'headings': len(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])),
                'tables': len(soup.find_all('table')),
                'links': len(soup.find_all('a')),
            }
        except:
            return {'headings': 0, 'tables': 0, 'links': 0}

    def _table_to_markdown(self, table, level: int = 3) -> str:
        rows = table.find_all('tr')
        if not rows:
            return ""

        md = []
        cell = lambda c: self._inline(c, level).replace('|', '\\|')
        headers = [cell(th) for th in rows[0].find_all(['th', 'td'])]
        md.append("| " + " | ".join(headers) + " |")
        md.append("| " + " | ".join(["---"] * len(headers)) + " |")

        for row in rows[1:]:
            cells = [cell(td) for td in row.find_all(['th', 'td'])]
            md.append("| " + " | ".join(cells) + " |")

        return "\n".join(md)
