"""
token_shredder - Main Entry Point
"""
import dataclasses
import logging
import re
import sys
import time
import hashlib
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from token_shredder.converters import get_converter, detect_file_format
from token_shredder.processors import Deduplicator, CodeMinifier, StructureOptimizer
from token_shredder.metrics import TokenCounter, QualityScorer
from token_shredder.utils.file_handler import FileHandler
from token_shredder.utils.logger import setup_logger, set_log_level
from token_shredder.models import ConversionResult, ConversionOptions, ProcessingOptions
from token_shredder.config import Config, CacheManager
from token_shredder.secrets import redact

console = Console()
err_console = Console(stderr=True, soft_wrap=True)
logger = setup_logger(__name__)

# Reusable processors
_dedup = Deduplicator()
_minifier = CodeMinifier()
_optimizer = StructureOptimizer()
_token_counter = TokenCounter()
_quality_scorer = QualityScorer()


BINARY_FORMATS = {'pdf', 'docx', 'pptx', 'xlsx', 'xls'}
# .env files: values are hidden at every level, the raw file is never output.
SECRET_FORMATS = {'env'}
PROSE_FORMATS = {'pdf', 'docx', 'pptx', 'txt', 'md', 'html', 'htm', 'log'}
CODE_FORMATS = {'python', 'py', 'js', 'ts', 'tsx', 'jsx', 'mjs', 'cjs', 'java', 'go', 'rs',
                'c', 'cpp', 'cc', 'cxx'}

DETAIL_LEVELS = {
    1: "Names only: headings, declarations, keys. Smallest output.",
    2: "Outline: adds signatures and structure.",
    3: "Default: outline plus docstrings/summaries; documents as clean text.",
    4: "More: full doc comments, speaker notes, JSON data minified.",
    5: "Full content, no compression (text files are passed through as-is).",
}


class ConversionError(Exception):
    """The file could not be converted; the message is meant for the user."""


class BatchError(ConversionError):
    """Some files in a batch failed; .results holds the ones that worked."""

    def __init__(self, message: str, results: list):
        super().__init__(message)
        self.results = results


def resolve_output_path(file_path: str, output_path: Optional[str]) -> Path:
    """Where the markdown goes. Never the input file itself."""
    src = Path(file_path).resolve()
    if output_path:
        out = Path(output_path)
        if out.resolve() == src:
            raise ConversionError(f"Output would overwrite the input file: {file_path}")
        return out
    out = Path(file_path).with_suffix('.md')
    if out.resolve() == src:  # converting a .md file
        out = Path(file_path).with_name(Path(file_path).stem + '.shredded.md')
    return out


def _write(path: Path, text: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
    except OSError as e:
        raise ConversionError(f"Cannot write {path}: {e.strerror or e}") from e


def _version() -> str:
    from importlib.metadata import PackageNotFoundError, version
    try:
        return version('token-shredder')
    except PackageNotFoundError:
        return '0'


def _read_text(file_path: str) -> str:
    return Path(file_path).read_text(encoding='utf-8', errors='replace')


def full_text_markdown(file_path: str, file_format: str) -> str:
    """The whole text file, fenced as code unless it is already prose/markdown."""
    text = _read_text(file_path)
    if file_format in ('md', 'txt', 'log', ''):
        return text
    return f"```{file_format}\n{text.rstrip()}\n```\n"


def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    """Cut text to at most max_tokens (cl100k), at a line break, with a visible note."""
    note = f"\n\n[... truncated to fit {max_tokens:,} tokens]\n"
    enc = _token_counter.encoding
    budget = max(max_tokens - _token_counter.estimate(note), 0)
    if enc is None:
        cut = text[: budget * 4]
    else:
        cut = enc.decode(enc.encode(text, disallowed_special=())[:budget])
    if "\n" in cut[len(cut) // 2:]:
        cut = cut[: cut.rindex("\n")]
    return cut.rstrip() + note


_TEMP_DIRS: List[str] = []


def _cleanup_temp_dirs() -> None:
    import shutil
    for d in _TEMP_DIRS:
        shutil.rmtree(d, ignore_errors=True)


def _as_utf8(file_path: str) -> str:
    """Path to a UTF-8 version of a text file.

    Files that already are UTF-8 (without BOM) are used as-is. Otherwise a BOM is
    dropped, UTF-16 is decoded, and other bytes are read as Windows-1252 (the usual
    encoding of non-UTF-8 text from Windows/Excel), into a temporary copy.
    """
    import atexit
    import tempfile
    data = Path(file_path).read_bytes()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        text, how = data.decode("utf-16", errors="replace"), "UTF-16"
    elif data.startswith(b"\xef\xbb\xbf"):
        text, how = data[3:].decode("utf-8", errors="replace"), "UTF-8 with BOM"
    else:
        try:
            data.decode("utf-8")
            return file_path
        except UnicodeDecodeError:
            text, how = data.decode("cp1252", errors="replace"), "Windows-1252"
    if not _TEMP_DIRS:
        atexit.register(_cleanup_temp_dirs)
    tmp_dir = tempfile.mkdtemp(prefix="token-shredder-")
    _TEMP_DIRS.append(tmp_dir)
    out = Path(tmp_dir) / Path(file_path).name
    out.write_text(text, encoding="utf-8")
    logger.info(f"{file_path}: not UTF-8, read as {how}")
    return str(out)


class _Source:
    """A file, prepared for conversion: format, converter, cache key parts."""

    def __init__(self, file_path: str, display_name: Optional[str] = None,
                 file_format: Optional[str] = None):
        problem = FileHandler().check_file(file_path)
        if problem:
            raise ConversionError(problem)
        self.path = file_path        # may be swapped for a UTF-8 temp copy below
        self.original = file_path
        self.name = display_name or file_path
        self.format = file_format or detect_file_format(file_path)
        logger.info(f"Detected format: {self.format}")
        self.converter = get_converter(self.format)
        if not self.converter:
            raise ConversionError(
                f"Unsupported file type '{Path(file_path).suffix or '(no extension)'}': {self.name}. "
                "See docs/FILE_FORMATS.md for the supported types."
            )
        size = Path(file_path).stat().st_size
        if size == 0:
            raise ConversionError(f"File is empty: {self.name}")
        if size > 1_000_000:
            logger.info(f"Large file ({size:,} bytes); this may take a few seconds")
        if self.format not in BINARY_FORMATS:
            self.path = _as_utf8(file_path)
        self._baseline_tokens: Optional[int] = None
        self._results: dict = {}

    def baseline_tokens(self, raw_markdown: str) -> int:
        # Compare with what you would otherwise paste: the raw file for text
        # formats, the converter's full extracted text for PDF/DOCX/PPTX/XLSX.
        if self._baseline_tokens is None:
            base = raw_markdown if self.format in BINARY_FORMATS else _read_text(self.path)
            self._baseline_tokens = _token_counter.estimate(base)
        return self._baseline_tokens


def _convert_at_level(src: _Source, level: int, opts: dict, cache_enabled: bool) -> ConversionResult:
    """Convert src at one detail level (memoised per source). No writing, no report."""
    if level in src._results:
        return src._results[level]
    options = ConversionOptions(
        detail_level=level,
        preserve_images=opts["preserve_images"],
        embed_images=opts["embed_images"],
        include_comments=opts["include_comments"],
    )
    key = "|".join(f"{k}={opts[k]}" for k in sorted(opts)) + f"|{level}|{src.format}|{_version()}"
    options_hash = hashlib.md5(key.encode()).hexdigest()
    cache_manager = Config().get_cache_manager() if cache_enabled else None
    cached = cache_manager.get(src.path, options_hash) if cache_manager else None

    if cached is not None:
        logger.info(f"Using cache for {src.name}")
        result = ConversionResult(markdown=cached, source_file=src.name, target_file="",
                                  format=src.format, detail_level=level)
        raw_markdown = cached
    else:
        if level >= 5 and src.format not in BINARY_FORMATS and src.format not in SECRET_FORMATS:
            # Level 5 = full content: the file itself, untouched.
            result = ConversionResult(markdown=full_text_markdown(src.path, src.format),
                                      source_file=src.name, target_file="",
                                      format=src.format, detail_level=level)
        else:
            try:
                result = src.converter.convert(src.path, options)
            except Exception as e:  # converter bug or unreadable file
                raise ConversionError(f"Could not convert {src.name}: {e}") from e
            # Converters report read/parse failures as "[Error ...]" text.
            if result.markdown.lstrip().startswith("[Error"):
                raise ConversionError(f"Could not convert {src.name}: {result.markdown.strip()}")
        result.markdown = result.markdown.replace("\r\n", "\n")  # Windows line endings
        raw_markdown = result.markdown
        if level < 5:
            # Repeated lines are redundancy in prose (page furniture, boilerplate) but
            # data in code outlines and data profiles, so only prose is deduplicated.
            if opts["deduplicate"] and src.format in PROSE_FORMATS:
                result.markdown = _dedup.process(result.markdown)
            if opts["minify_code"] and src.format in CODE_FORMATS:
                result.markdown = _minify_code_blocks(result.markdown, src.format)
            if opts["optimize_structure"]:
                result.markdown = _optimizer.process(result.markdown)
        if opts.get("redact", True):
            # Output goes to an AI model: replace well-known credential formats.
            result.markdown, found = redact(result.markdown)
            if found:
                result.warnings = list(result.warnings) + [f"redacted: {', '.join(found)}"]
        if cache_manager:
            cache_manager.set(src.path, options_hash, result.markdown)

    result.source_file = src.name
    result.target_file = ""
    result.detail_level = level
    result.source_tokens = src.baseline_tokens(raw_markdown)
    result.output_tokens = _token_counter.estimate(result.markdown)
    text_check = (src.format not in BINARY_FORMATS
                  and len(result.markdown) >= 0.7 * Path(src.path).stat().st_size)
    # Documents: cleaned text can end up a few tokens longer than the raw extraction
    # (list markers, table pipes). Compare for small files, where it is cheap.
    doc_check = (src.format in BINARY_FORMATS and level >= 3
                 and Path(src.path).stat().st_size <= 2_000_000)
    if (level < 5 and src.format not in SECRET_FORMATS and (text_check or doc_check)):
        # Never worse than pasting the file itself: if a summary is not smaller
        # than the full content (level 5), give the full content.
        full = _convert_at_level(src, 5, opts, cache_enabled)
        if result.output_tokens >= full.output_tokens:
            result.markdown = full.markdown
            result.output_tokens = full.output_tokens
    _set_savings(result)
    src._results[level] = result
    return result


def _set_savings(result: ConversionResult) -> None:
    result.tokens_saved = result.source_tokens - result.output_tokens
    result.tokens_saved_pct = (result.tokens_saved / result.source_tokens * 100
                               if result.source_tokens > 0 else 0.0)


def _fit_budget(src: _Source, max_level: int, max_tokens: int, opts: dict,
                cache_enabled: bool) -> ConversionResult:
    """The most useful output within max_tokens, at most max_level.

    Normally the highest level that fits. But if that level uses less than a quarter
    of the budget (e.g. a web page: headings only, while the next level is the
    article), the next level up is truncated to the budget instead. If even level 1
    is too big, level 1 is truncated.
    """
    fitting = None
    for level in range(max_level, 0, -1):
        result = _convert_at_level(src, level, opts, cache_enabled)
        if result.output_tokens <= max_tokens:
            fitting = result
            break
    if fitting is not None and (fitting.output_tokens * 4 >= max_tokens
                                or fitting.detail_level >= max_level):
        return fitting
    base_level = fitting.detail_level + 1 if fitting is not None else 1
    result = _convert_at_level(src, base_level, opts, cache_enabled)
    truncated = dataclasses.replace(result)
    truncated.markdown = _truncate_to_tokens(result.markdown, max_tokens)
    truncated.output_tokens = _token_counter.estimate(truncated.markdown)
    truncated.warnings = list(result.warnings) + [
        f"level {base_level} truncated to fit {max_tokens:,} tokens"]
    _set_savings(truncated)
    return truncated


QUERY_DEFAULT_TOKENS = 6000   # relevant-parts budget per file when no --max-tokens is given
QUERY_SHARE = 0.65            # with --max-tokens: share of the budget for relevant parts


def _full_text(src: "_Source", opts: dict, cache_enabled: bool) -> str:
    """A file's full content for query chunking: the file itself for text formats,
    the full extraction (level 4) for documents and web pages."""
    if src.format in BINARY_FORMATS or src.format in ("html", "htm", "txt"):
        # Level 4 = full content, cleaned, with headings (plain-text RFCs get their
        # numbered sections as headings), which gives better sections to rank.
        # No dedup here: "[See above]" markers would replace real content in a chunk.
        return _convert_at_level(src, 4, {**opts, "deduplicate": False}, cache_enabled).markdown
    if src.format in SECRET_FORMATS:
        return ""
    return _read_text(src.path)


def _query_chunks(src: "_Source", query: str, opts: dict, cache_enabled: bool) -> list:
    from token_shredder import query as q
    chunks = q.chunk_file(_full_text(src, opts, cache_enabled), src.format)
    ranked = q.rank(chunks, query)
    for c in ranked:
        c.source = src.original
        if opts.get("redact", True):
            c.text, _found = redact(c.text)
    return ranked


def _with_relevant(outline: ConversionResult, chosen: list, query: str, ranked_count: int,
                   with_source: bool = False) -> ConversionResult:
    from token_shredder import query as q
    result = dataclasses.replace(outline)
    result.markdown = outline.markdown.rstrip() + "\n" + q.render(chosen, query, with_source)
    result.output_tokens = _token_counter.estimate(result.markdown)
    result.warnings = list(outline.warnings) + [
        f'query "{query}": {len(chosen)} part(s) included in full'
        + ("" if ranked_count else ", nothing matched")]
    _set_savings(result)
    return result


def _convert_with_query(src: "_Source", query: str, detail_level: Optional[int],
                        max_tokens: Optional[int], opts: dict, cache_enabled: bool) -> ConversionResult:
    from token_shredder import query as q
    ranked = _query_chunks(src, query, opts, cache_enabled)
    # The rest of the file is shown as an outline: for prose that's the headings
    # (level 1; level 3 would already be the full text), for code and data level 3.
    base_level = detail_level or (1 if src.format in PROSE_FORMATS else 3)
    if max_tokens is None:
        chosen = q.select(ranked, QUERY_DEFAULT_TOKENS, _token_counter.estimate)
        outline = _convert_at_level(src, base_level, opts, cache_enabled)
    else:
        chosen = q.select(ranked, int(max_tokens * QUERY_SHARE), _token_counter.estimate)
        header = _token_counter.estimate(q.render(chosen, query)) if chosen else 30
        outline = _fit_budget(src, detail_level or (2 if src.format in PROSE_FORMATS else 5),
                              max(max_tokens - header, 50), opts, cache_enabled)
    result = _with_relevant(outline, chosen, query, len(ranked))
    if max_tokens is not None and result.output_tokens > max_tokens:
        result.markdown = _truncate_to_tokens(result.markdown, max_tokens)
        result.output_tokens = _token_counter.estimate(result.markdown)
    # Never more than the whole file: then the whole file is the better answer.
    if src.format not in BINARY_FORMATS and src.format not in SECRET_FORMATS:
        full = _convert_at_level(src, 5, opts, cache_enabled)
        if result.output_tokens >= full.output_tokens and (
                max_tokens is None or full.output_tokens <= max_tokens):
            full = dataclasses.replace(full)
            full.warnings = list(full.warnings) + [f'query "{query}": whole file is smaller']
            return full
    return result


def convert_file(
    file_path: str,
    output_path: Optional[str] = None,
    detail_level: Optional[int] = None,
    preserve_images: bool = False,
    embed_images: bool = False,
    include_comments: bool = False,
    deduplicate: bool = True,
    minify_code: bool = True,
    optimize_structure: bool = True,
    show_metrics: bool = True,
    cache_enabled: bool = True,
    confirm_large: bool = True,
    write_output: bool = True,
    max_tokens: Optional[int] = None,
    display_name: Optional[str] = None,
    file_format: Optional[str] = None,
    redact_secrets: bool = True,
    query: Optional[str] = None,
) -> ConversionResult:
    """Convert a file to markdown.

    With query, the parts of the file that best match the question (functions,
    sections, records) are added in full after the outline; see query.py.

    detail_level runs from 1 (smallest: names and structure only) to 5 (full
    content, no compression); default 3. With max_tokens, the highest level that
    fits is chosen (up to detail_level, default 5); if even level 1 is too big it
    is truncated. See DETAIL_LEVELS.
    """
    if detail_level is not None and not 1 <= detail_level <= 5:
        raise ValueError(f"detail_level must be 1-5, got {detail_level}")
    if max_tokens is not None and max_tokens < 50:
        raise ValueError("max_tokens must be at least 50")
    start_time = time.time()
    src = _Source(file_path, display_name, file_format)
    output_file = resolve_output_path(file_path, output_path) if write_output else None
    opts = dict(preserve_images=preserve_images, embed_images=embed_images,
                include_comments=include_comments, deduplicate=deduplicate,
                minify_code=minify_code, optimize_structure=optimize_structure,
                redact=redact_secrets)

    if query and query.strip():
        result = _convert_with_query(src, query.strip(), detail_level, max_tokens, opts,
                                     cache_enabled)
    elif max_tokens is not None:
        result = _fit_budget(src, detail_level or 5, max_tokens, opts, cache_enabled)
    else:
        result = _convert_at_level(src, detail_level or 3, opts, cache_enabled)

    result.processing_time_ms = (time.time() - start_time) * 1000
    if output_file is not None:
        _write(output_file, result.markdown)
        result.target_file = str(output_file)
    if show_metrics:
        display_report(result)
    return result


_FENCE_RE = re.compile(r"(```[^\n]*\n)(.*?)(\n```)", re.DOTALL)


def _minify_code_blocks(markdown: str, file_format: str) -> str:
    """Minify only the fenced code blocks inside the markdown.

    Converters return markdown (headings, docstrings, fenced code). Running the
    code minifier over the whole document would treat "## Classes" etc. as
    comments and strip every heading, so it is applied to fenced blocks only.
    """
    return _FENCE_RE.sub(
        lambda m: m.group(1) + _minifier.process(m.group(2), file_format) + m.group(3),
        markdown,
    )


def display_report(result: ConversionResult, out: Optional[Console] = None):
    """Display conversion report (on stdout, or on `out`, e.g. stderr when piping)."""
    table = Table(title="TOKEN SHREDDER REPORT", show_lines=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Input", result.source_file)
    table.add_row("Output", result.target_file or "-")
    table.add_row("Format", result.format)
    table.add_row("Detail level", str(result.detail_level))
    table.add_row("", "")
    table.add_row("Source Tokens", f"{result.source_tokens:,}")
    table.add_row("Output Tokens", f"{result.output_tokens:,}")
    table.add_row("Tokens Saved", f"{result.tokens_saved:,} ({result.tokens_saved_pct:.1f}%)")
    table.add_row("", "")
    table.add_row("Processing Time", f"{result.processing_time_ms:.1f}ms")
    for w in result.warnings:
        table.add_row("Note", w)

    (out or console).print(Panel(table, border_style="blue"))


SUPPORTED_SUFFIXES = {
    '.pdf', '.docx', '.pptx', '.xlsx', '.py', '.js', '.mjs', '.cjs', '.ts', '.tsx', '.jsx',
    '.java', '.go', '.rs', '.json', '.json5', '.jsonl', '.ndjson', '.csv', '.tsv', '.html', '.htm', '.md', '.txt', '.css',
    '.yaml', '.yml', '.xml', '.sql', '.toml', '.env', '.log', '.ini', '.cfg', '.conf', '.svg',
    '.graphql', '.gql', '.proto', '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd',
    '.dockerfile', '.mk', '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hh', '.hxx',
}
SUPPORTED_NAMES = {'dockerfile', 'makefile', '.gitignore', '.dockerignore'}
# Folders that hold dependencies, environments or build output, not the user's files.
SKIP_DIRS = {'node_modules', 'venv', 'env', '__pycache__', 'site-packages', 'dist', 'build',
             'target', 'vendor', 'bower_components', '.venv', '.tox', '.mypy_cache',
             '.pytest_cache', '.git', '.hg', '.svn'}


_SECRET_NAME = re.compile(r"secret|credential|service[-_]?account|passw|private[-_]?key|token",
                          re.IGNORECASE)


def looks_secret(name: str) -> bool:
    """File names that usually hold credentials; batch skips them."""
    return bool(_SECRET_NAME.search(name)) or name.lower().endswith(".env")


def find_batch_files(directory: str, skipped: Optional[list] = None) -> List[Path]:
    """Supported files under directory (recursive), skipping hidden folders,
    dependency/build folders (node_modules, venv, dist, ...) and earlier batch output."""
    import os
    files = []
    for root, dirs, names in os.walk(directory):  # does not follow symlinked folders
        dirs[:] = sorted(d for d in dirs
                         if not d.startswith('.') and d.lower() not in SKIP_DIRS
                         and not d.endswith('.egg-info'))
        for name in sorted(names):
            f = Path(root) / name
            if name.startswith('.') and name.lower() not in SUPPORTED_NAMES:
                continue
            suffixes = [x.lower() for x in f.suffixes]
            if suffixes[-2:-1] and suffixes[-1] == '.md' and suffixes[-2] in SUPPORTED_SUFFIXES:
                continue  # "report.pdf.md": output of an earlier batch run
            if not (f.suffix.lower() in SUPPORTED_SUFFIXES or name.lower() in SUPPORTED_NAMES):
                continue
            try:
                if f.stat().st_size == 0:
                    continue  # empty files (__init__.py, .gitkeep-style) have nothing to say
            except OSError:
                continue
            if looks_secret(name):
                if skipped is not None:
                    skipped.append(f)
                continue
            if f.is_file():
                files.append(f)
    return files


def _waterfill(needs: List[int], budget: int) -> List[int]:
    """Max-min fair split: small needs are met in full, big ones share the rest equally."""
    alloc = [0] * len(needs)
    remaining = budget
    order = sorted(range(len(needs)), key=lambda i: needs[i])
    for k, i in enumerate(order):
        share = remaining // (len(needs) - k)
        alloc[i] = min(needs[i], share)
        remaining -= alloc[i]
    return alloc


def _allocate_budget(sources: list, max_tokens: int, max_level: int, opts: dict,
                     cache_enabled: bool, header_tokens: int) -> List[ConversionResult]:
    """Share max_tokens across files.

    Each file "needs" its size at max_level. Small files get everything they need;
    large files split the rest equally (water-filling) and each gets the highest
    detail level that fits its share (truncated level 1 if nothing fits). Unused
    budget is then offered once more to the files that are still below their need.
    """
    # Too many files for the budget (each needs ~100 tokens to say anything): keep the
    # shallowest files (README, top-level modules) and leave the rest out, with a note.
    per_file = 100 + header_tokens
    if max_tokens < per_file * len(sources):
        keep = max_tokens // per_file
        if keep == 0:
            raise ConversionError(f"--max-tokens {max_tokens:,} is too small for any file")
        ranked = sorted(sources, key=lambda s: (len(Path(s.original).parts), s.original))
        dropped = len(sources) - keep
        sources[:] = ranked[:keep]
        err_console.print(
            f"Budget fits about {keep} of {keep + dropped} files: left out the {dropped} most "
            "deeply nested. Use a bigger --max-tokens or a subfolder to include them.",
            markup=False, highlight=False)
    budget = max_tokens - header_tokens * len(sources)
    need = [_convert_at_level(s, max_level, opts, cache_enabled).output_tokens for s in sources]
    alloc = [max(a, 50) for a in _waterfill(need, budget)]
    results = [_fit_budget(s, max_level, a, opts, cache_enabled) for s, a in zip(sources, alloc)]
    leftover = budget - sum(r.output_tokens for r in results)
    if leftover > 0:
        extra_need = [max(n - r.output_tokens, 0) for n, r in zip(need, results)]
        extra = _waterfill(extra_need, leftover)
        results = [_fit_budget(s, max_level, r.output_tokens + e, opts, cache_enabled) if e else r
                   for s, r, e in zip(sources, results, extra)]
    return results


def combine_results(results: List[ConversionResult], root: Path) -> str:
    """One document with a <file> block per file (for --output - / --copy).

    XML-style tags keep file boundaries unambiguous for the model, even when the
    files themselves contain markdown headings.
    """
    parts = []
    for r in results:
        try:
            name = Path(r.source_file).relative_to(root).as_posix()
        except ValueError:
            name = r.source_file
        parts.append(f'<file path="{name}" detail_level="{r.detail_level}">\n'
                     f'{r.markdown.strip()}\n</file>\n')
    return "\n".join(parts)


def batch_convert(
    directory: str,
    output_dir: Optional[str] = None,
    detail_level: Optional[int] = None,
    workers: int = 4,
    preserve_images: bool = False,
    quiet: bool = False,
    max_tokens: Optional[int] = None,
    write_output: bool = True,
    cache_enabled: bool = True,
    redact_secrets: bool = True,
    query: Optional[str] = None,
) -> List[ConversionResult]:
    """Convert every supported file under directory.

    Output keeps the original name plus ".md" ("report.pdf" -> "report.pdf.md"), so
    "a.py" and "a.txt" never overwrite each other. With output_dir the folder
    structure is mirrored there; otherwise files are written next to the originals.
    With max_tokens the budget is shared across all files (see _allocate_budget).
    Raises ConversionError at the end if any file failed.
    """
    from concurrent.futures import ThreadPoolExecutor

    root = Path(directory)
    skipped: list = []
    files = find_batch_files(directory, skipped)
    for f in skipped:
        err_console.print(f"skipped {f.relative_to(root)} (name suggests secrets)", markup=False,
                          highlight=False)
    if not files:
        err_console.print(f"[yellow]No supported files found in {directory}[/yellow]")
        return []

    def target(f: Path) -> Path:
        rel = f.relative_to(root)
        base = Path(output_dir) / rel if output_dir else f
        return base.with_name(base.name + '.md')

    opts = dict(preserve_images=preserve_images, embed_images=False, include_comments=False,
                deduplicate=True, minify_code=True, optimize_structure=True,
                redact=redact_secrets)
    failures = []

    def prepare(f: Path):
        try:
            src = _Source(str(f))
            # Warm the memo at the starting level in parallel.
            _convert_at_level(src, 1 if max_tokens else (detail_level or 3), opts, cache_enabled)
            return src
        except Exception as e:
            failures.append(f)
            err_console.print(f"[red]{escape(str(e))}[/red]")
            return None

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                  console=err_console, disable=quiet, transient=True) as progress:
        progress.add_task(f"Converting {len(files)} files...", total=None)
        with ThreadPoolExecutor(max_workers=workers) as executor:
            sources = [s for s in executor.map(prepare, files) if s is not None]
        chosen_by_file: dict = {}
        outline_budget = max_tokens
        if query and query.strip() and sources:
            # Rank the parts of all files together: the folder's best matches win,
            # wherever they are. Outlines of all files share what's left.
            from token_shredder import query as q
            pool = [c for s in sources for c in _query_chunks(s, query.strip(), opts, cache_enabled)]
            pool.sort(key=lambda c: -c.score)
            rel_budget = (int(max_tokens * QUERY_SHARE) if max_tokens is not None
                          else QUERY_DEFAULT_TOKENS * 2)
            for c in q.select(pool, rel_budget, _token_counter.estimate):
                chosen_by_file.setdefault(c.source, []).append(c)
            if max_tokens is not None:
                used = sum(c.tokens for cs in chosen_by_file.values() for c in cs)
                outline_budget = max(max_tokens - used - 40 * len(chosen_by_file), 50 * len(sources))
        if outline_budget is not None and sources:
            header = _token_counter.estimate('<file path="some/folder/file_name.ext" '
                                             'detail_level="3">\n\n</file>\n')
            results = _allocate_budget(sources, outline_budget, detail_level or 5, opts,
                                       cache_enabled, header)
        else:
            results = [_convert_at_level(s, detail_level or 3, opts, cache_enabled)
                       for s in sources]
        if query and query.strip():
            results = [_with_relevant(r, chosen_by_file.get(s.original, []), query.strip(), 1)
                       if chosen_by_file.get(s.original) else r
                       for s, r in zip(sources, results)]

    for src, r in zip(sources, results):
        r.source_file = src.original
        if write_output:
            out = target(Path(src.original))
            _write(out, r.markdown)
            r.target_file = str(out)
        if not quiet:
            err_console.print(f"{Path(src.original).relative_to(root)} -> {r.target_file or '(combined)'} "
                              f"(level {r.detail_level}{', truncated' if any('truncated' in w for w in r.warnings) else ''}, {r.source_tokens:,} -> "
                              f"{r.output_tokens:,} tokens)", markup=False, highlight=False)

    if not quiet:
        src_total = sum(r.source_tokens for r in results)
        out_total = sum(r.output_tokens for r in results)
        err_console.print(f"\n{len(results)} converted, {len(failures)} failed. "
                          f"Tokens: {src_total:,} -> {out_total:,}")
    if failures:
        raise BatchError(f"{len(failures)} file(s) failed", results)
    return results


def analyze_file(file_path: str):
    """Analyze file without converting."""
    file_handler = FileHandler()
    problem = file_handler.check_file(file_path)
    if problem:
        err_console.print(f"[red]{problem}[/red]")
        raise typer.Exit(1)

    file_format = detect_file_format(file_path)
    console.print(f"File: {file_path}")
    console.print(f"Format: {file_format}")
    console.print(f"Size: {Path(file_path).stat().st_size:,} bytes")

    converter = get_converter(file_format)
    if converter:
        info = converter.get_file_info(file_path)
        for k, v in info.items():
            console.print(f"{k.capitalize()}: {v}")


app = typer.Typer(
    name="token-shredder",
    help="Convert files to markdown. Shred tokens. Feed Claude lean.",
    no_args_is_help=True,
)


DETAIL_HELP = "Detail level: 1 = names only (smallest) ... 3 = default ... 5 = full content"


def _detail_option(default: int = 3):
    return typer.Option(default, '--detail-level', '-d', min=1, max=5, help=DETAIL_HELP)


def _set_verbosity(quiet: bool, verbose: bool) -> None:
    if quiet:
        set_log_level(logging.ERROR)
    elif verbose:
        set_log_level(logging.INFO)


def _copy_to_clipboard(text: str) -> None:
    import shutil
    import subprocess
    for cmd in (["pbcopy"], ["wl-copy"], ["xclip", "-selection", "clipboard"],
                ["xsel", "--clipboard", "--input"], ["clip"]):
        if shutil.which(cmd[0]):
            subprocess.run(cmd, input=text.encode("utf-8"), check=True)
            return
    raise ConversionError("No clipboard tool found (pbcopy, wl-copy, xclip, xsel or clip)")


def _emit(results: List[ConversionResult], combined: str, *, to_stdout: bool, copy: bool,
          as_json: bool) -> None:
    """Send converted text to stdout and/or the clipboard."""
    if as_json:
        import json
        payload = [{"source": r.source_file, "format": r.format, "detail_level": r.detail_level,
                    "source_tokens": r.source_tokens, "output_tokens": r.output_tokens,
                    "notes": r.warnings, "output_file": r.target_file or None,
                    "markdown": r.markdown} for r in results]
        text = json.dumps(payload[0] if len(payload) == 1 else payload, ensure_ascii=False,
                          indent=2) + "\n"
    else:
        text = combined
    if copy:
        _copy_to_clipboard(text)
    if to_stdout:
        out = text if text.endswith("\n") else text + "\n"
        buffer = getattr(sys.stdout, "buffer", None)
        if buffer is not None:
            # Always UTF-8, also on Windows consoles/pipes that default to cp1252.
            sys.stdout.flush()
            buffer.write(out.encode("utf-8"))
            buffer.flush()
        else:
            sys.stdout.write(out)
            sys.stdout.flush()


@app.command()
def convert(
    source: str = typer.Argument(..., help="File, http(s) URL, or - for stdin"),
    output: Optional[str] = typer.Option(
        None, '--output', '-o',
        help="Output file, or - for stdout. Default: stdout when piped or for URL/stdin input, "
             "else FILE.md next to the input"),
    detail_level: Optional[int] = typer.Option(
        None, '--detail-level', '-d', min=1, max=5,
        help=DETAIL_HELP + " (with --max-tokens: the highest level to try)"),
    max_tokens: Optional[int] = typer.Option(
        None, '--max-tokens', '-t', min=50,
        help="Token budget: use the highest detail level that fits, truncate if nothing fits"),
    copy: bool = typer.Option(False, '--copy', '-c', help="Copy the result to the clipboard"),
    as_json: bool = typer.Option(False, '--json', help="Output JSON (markdown + token counts)"),
    input_type: Optional[str] = typer.Option(
        None, '--type', help="Input format for stdin/URLs when it can't be detected, e.g. json"),
    preserve_images: bool = typer.Option(False, '--preserve-images', help='PDF: list how many images each page has'),
    no_deduplicate: bool = typer.Option(False, '--no-deduplicate', help='Skip deduplication'),
    no_minify: bool = typer.Option(False, '--no-minify', help='Skip code minification'),
    quiet: bool = typer.Option(False, '--quiet', '-q', help='Print nothing except errors'),
    verbose: bool = typer.Option(False, '--verbose', '-v', help='Show progress messages'),
    no_cache: bool = typer.Option(False, '--no-cache', help='Disable caching'),
    keep_secrets: bool = typer.Option(
        False, '--keep-secrets', help="Don't redact API keys, tokens and private keys"),
    query: Optional[str] = typer.Option(
        None, '--query', '-Q',
        help="A question: the best-matching functions/sections/records are added in full"),
):
    """Convert a file, URL or stdin to compact markdown."""
    from token_shredder.sources import SourceError, fetch_url, is_url, read_stdin

    _set_verbosity(quiet, verbose)
    materialized = None
    try:
        if source == "-":
            materialized = read_stdin(sys.stdin.buffer, input_type)
        elif is_url(source):
            materialized = fetch_url(source, input_type)
    except SourceError as e:
        err_console.print(f"[red]{escape(str(e))}[/red]")
        raise typer.Exit(1)

    try:
        piped = not sys.stdout.isatty()
        to_stdout = output == "-" or (output is None and not copy and (piped or materialized))
        write_file = output not in (None, "-") or (output is None and not to_stdout and not copy)
        result = _run_cli(
            convert_file,
            materialized.path if materialized else source,
            output_path=output if write_file else None,
            detail_level=detail_level,
            max_tokens=max_tokens,
            preserve_images=preserve_images,
            deduplicate=not no_deduplicate,
            minify_code=not no_minify,
            show_metrics=False,
            cache_enabled=not no_cache and materialized is None,
            write_output=write_file,
            display_name=materialized.name if materialized else None,
            file_format=materialized.format if materialized else None,
            redact_secrets=not keep_secrets,
            query=query,
        )
        _run_cli(_emit, [result], result.markdown, to_stdout=to_stdout, copy=copy, as_json=as_json)
        if not quiet:
            # Keep stdout clean for the content when it carries the output.
            display_report(result, out=err_console if to_stdout else None)
            if copy:
                err_console.print(f"Copied {result.output_tokens:,} tokens to the clipboard.")
    finally:
        if materialized:
            materialized.cleanup()


@app.command()
def batch(
    directory: str = typer.Argument(..., help="Directory to process (recursive)"),
    output: Optional[str] = typer.Option(
        None, '--output', '-o',
        help="Output directory, or - for one combined document on stdout"),
    detail_level: Optional[int] = typer.Option(
        None, '--detail-level', '-d', min=1, max=5,
        help=DETAIL_HELP + " (with --max-tokens: the highest level to try)"),
    max_tokens: Optional[int] = typer.Option(
        None, '--max-tokens', '-t', min=50,
        help="Total token budget shared by all files"),
    copy: bool = typer.Option(False, '--copy', '-c',
                              help="Copy one combined document to the clipboard"),
    as_json: bool = typer.Option(False, '--json', help="Output JSON instead of markdown"),
    workers: int = typer.Option(4, '--workers', '-w', min=1, max=64, help='Parallel workers'),
    preserve_images: bool = typer.Option(False, '--preserve-images', help='PDF: list how many images each page has'),
    quiet: bool = typer.Option(False, '--quiet', '-q', help='Print nothing except errors'),
    verbose: bool = typer.Option(False, '--verbose', '-v', help='Show progress messages'),
    no_cache: bool = typer.Option(False, '--no-cache', help='Disable caching'),
    keep_secrets: bool = typer.Option(
        False, '--keep-secrets', help="Don't redact API keys, tokens and private keys"),
    query: Optional[str] = typer.Option(
        None, '--query', '-Q',
        help="A question: the best-matching functions/sections/records are added in full"),
):
    """Convert all supported files in a folder, optionally within one token budget."""
    _set_verbosity(quiet, verbose)
    if not Path(directory).is_dir():
        err_console.print(f"[red]Not a directory: {directory}[/red]")
        raise typer.Exit(1)
    to_stdout = output == "-"
    combined_mode = to_stdout or copy or as_json
    failed = False
    try:
        results = _run_cli(
            _batch_keep_partial,
            directory,
            output_dir=None if combined_mode else output,
            detail_level=detail_level,
            workers=workers,
            preserve_images=preserve_images,
            quiet=quiet,
            max_tokens=max_tokens,
            write_output=not combined_mode,
            cache_enabled=not no_cache,
            redact_secrets=not keep_secrets,
            query=query,
        )
    except _PartialBatch as e:  # some files failed: still output the rest, then exit 1
        results, failed = e.results, True
    if combined_mode and results:
        root = Path(directory).resolve()
        for r in results:
            r.source_file = str(Path(r.source_file).resolve())
        combined = combine_results(results, root)
        _run_cli(_emit, results, combined, to_stdout=to_stdout or (as_json and not copy),
                 copy=copy, as_json=as_json)
        if copy and not quiet:
            err_console.print(f"Copied {_token_counter.estimate(combined):,} tokens to the clipboard.")
    if failed:
        raise typer.Exit(1)


@app.command()
def analyze(
    file_path: str = typer.Argument(..., help="File to analyze", exists=True),
):
    """Analyze file without converting."""
    analyze_file(file_path)


@app.command()
def version():
    """Show version."""
    from importlib.metadata import version as _v
    console.print(f"Token Shredder v{_v('token-shredder')}")


class _PartialBatch(Exception):
    def __init__(self, results):
        self.results = results


def _batch_keep_partial(*args, **kwargs):
    """batch_convert, but a BatchError becomes _PartialBatch so the CLI can still
    output the files that worked."""
    try:
        return batch_convert(*args, **kwargs)
    except BatchError as e:
        raise _PartialBatch(e.results) from e


def _run_cli(func, *args, **kwargs):
    """Run a library call; show ConversionError as a one-line message and exit 1."""
    try:
        return func(*args, **kwargs)
    except ConversionError as e:
        # batch_convert already printed each failed file; its summary error is enough.
        if not str(e).endswith("file(s) failed"):
            err_console.print(f"[red]{escape(str(e))}[/red]")
        raise typer.Exit(1)


def _dry_run(file_path: str, detail_level: int) -> ConversionResult:
    return _run_cli(convert_file, file_path, detail_level=detail_level, show_metrics=False,
                    cache_enabled=False, write_output=False)


@app.command()
def preview(
    file_path: str = typer.Argument(..., help="File to preview", exists=True),
    detail_level: int = _detail_option(),
):
    """Preview conversion without writing a file."""
    result = _dry_run(file_path, detail_level)
    console.print(f"\nInput: {result.source_tokens:,} tokens")
    console.print(f"Output: {result.output_tokens:,} tokens")
    console.print(f"Saved: {result.tokens_saved_pct:.1f}%\n")
    console.print(result.markdown[:1000], markup=False)
    if len(result.markdown) > 1000:
        console.print("... (truncated)")


@app.command()
def quality(
    file_path: str = typer.Argument(..., help="File to analyze", exists=True),
    detail_level: int = _detail_option(),
):
    """Show token counts and a quality score without writing a file."""
    result = _dry_run(file_path, detail_level)
    full = _dry_run(file_path, 5)
    result.quality_score = _quality_scorer.score(result.markdown, full.markdown)
    console.print(f"\n[bold]File Analysis: {Path(file_path).name}[/bold]")
    console.print(f"Format: {result.format}")
    console.print(f"Input tokens: {result.source_tokens:,}")
    console.print(f"Output tokens: {result.output_tokens:,}")
    console.print(f"Saved: {result.tokens_saved_pct:.1f}%")
    console.print(f"Quality score: {result.quality_score:.1f}/100")


if __name__ == "__main__":
    app()
