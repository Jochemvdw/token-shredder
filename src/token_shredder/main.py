"""
token_shredder - Main Entry Point
"""
import logging
import re
import sys
import time
import hashlib
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console
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

console = Console()
err_console = Console(stderr=True)
logger = setup_logger(__name__)

# Reusable processors
_dedup = Deduplicator()
_minifier = CodeMinifier()
_optimizer = StructureOptimizer()
_token_counter = TokenCounter()
_quality_scorer = QualityScorer()


BINARY_FORMATS = {'pdf', 'docx', 'pptx', 'xlsx', 'xls'}
CODE_FORMATS = {'python', 'py', 'js', 'ts', 'tsx', 'jsx', 'mjs', 'cjs', 'java', 'go', 'rs',
                'c', 'cpp', 'cc', 'cxx'}

DETAIL_LEVELS = {
    1: "Names only: headings, declarations, keys. Smallest output.",
    2: "Outline: adds signatures and structure.",
    3: "Default: outline plus docstrings/summaries; documents as clean text.",
    4: "More: full doc comments, speaker notes, JSON data minified.",
    5: "Full content, no compression (text files are passed through as-is).",
}


def _read_text(file_path: str) -> str:
    return Path(file_path).read_text(encoding='utf-8', errors='replace')


def full_text_markdown(file_path: str, file_format: str) -> str:
    """The whole text file, fenced as code unless it is already prose/markdown."""
    text = _read_text(file_path)
    if file_format in ('md', 'txt', 'log', ''):
        return text
    return f"```{file_format}\n{text.rstrip()}\n```\n"


def convert_file(
    file_path: str,
    output_path: Optional[str] = None,
    detail_level: int = 3,
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
) -> ConversionResult:
    """Convert a file to markdown.

    detail_level runs from 1 (smallest: names and structure only) to 5 (full
    content, no compression); 3 is the default. See DETAIL_LEVELS.
    """
    if not 1 <= detail_level <= 5:
        raise ValueError(f"detail_level must be 1-5, got {detail_level}")
    start_time = time.time()
    file_handler = FileHandler()
    config = Config()
    options = ConversionOptions(
        detail_level=detail_level,
        preserve_images=preserve_images,
        embed_images=embed_images,
        include_comments=include_comments,
    )
    processing_options = ProcessingOptions(
        deduplicate=deduplicate,
        minify_code=minify_code,
        optimize_structure=optimize_structure,
        cache_enabled=cache_enabled,
    )

    problem = file_handler.check_file(file_path)
    if problem:
        err_console.print(f"[red]{problem}[/red]")
        raise typer.Exit(1)

    file_format = detect_file_format(file_path)
    logger.info(f"Detected format: {file_format}")

    converter = get_converter(file_format)
    if not converter:
        err_console.print(f"[red]Unsupported format: {file_format}[/red]")
        raise typer.Exit(1)

    file_size = Path(file_path).stat().st_size
    if confirm_large and file_size > 1_000_000:
        logger.info(f"Large file ({file_size:,} bytes); this may take a few seconds")

    cache_manager = None
    options_hash = hashlib.md5(
        f"{detail_level}{preserve_images}{embed_images}{include_comments}"
        f"{deduplicate}{minify_code}{optimize_structure}".encode()
    ).hexdigest()
    if processing_options.cache_enabled:
        cache_manager = config.get_cache_manager()
        cached = cache_manager.get(file_path, options_hash)
        if cached:
            logger.info(f"Using cache for {file_path}")
            result = ConversionResult(
                markdown=cached,
                source_file=file_path,
                target_file=output_path or str(Path(file_path).with_suffix('.md')),
                format=file_format,
            )
            result.output_tokens = _token_counter.estimate(cached)
            if file_format not in BINARY_FORMATS:
                result.source_tokens = _token_counter.estimate(_read_text(file_path))
                result.tokens_saved = result.source_tokens - result.output_tokens
                if result.source_tokens:
                    result.tokens_saved_pct = result.tokens_saved / result.source_tokens * 100
            result.processing_time_ms = (time.time() - start_time) * 1000
            if write_output:
                Path(result.target_file).write_text(cached)
            if show_metrics:
                display_report(result)
            return result

    if detail_level >= 5 and file_format not in BINARY_FORMATS:
        # Level 5 = full content: the file itself, untouched.
        result = ConversionResult(
            markdown=full_text_markdown(file_path, file_format),
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format=file_format,
            detail_level=detail_level,
        )
    else:
        result = converter.convert(file_path, options)
    raw_markdown = result.markdown

    if detail_level < 5:
        if deduplicate:
            result.markdown = _dedup.process(result.markdown)

        if minify_code and file_format in CODE_FORMATS:
            result.markdown = _minify_code_blocks(result.markdown, file_format)

        if optimize_structure:
            result.markdown = _optimizer.process(result.markdown)

    # Compare with what you would otherwise paste: the raw file for text
    # formats, the converter's full extracted text for PDF/DOCX/PPTX/XLSX.
    baseline = raw_markdown if file_format in BINARY_FORMATS else _read_text(file_path)
    result.source_tokens = _token_counter.estimate(baseline)
    result.output_tokens = _token_counter.estimate(result.markdown)
    result.tokens_saved = result.source_tokens - result.output_tokens
    result.tokens_saved_pct = (result.tokens_saved / result.source_tokens * 100) if result.source_tokens > 0 else 0.0
    result.processing_time_ms = (time.time() - start_time) * 1000
    result.quality_score = _quality_scorer.score(result.markdown, baseline)

    if processing_options.cache_enabled and cache_manager:
        cache_manager.set(file_path, options_hash, result.markdown)

    if output_path:
        output_file = Path(output_path)
    else:
        output_file = Path(file_path).with_suffix('.md')

    if write_output:
        output_file.write_text(result.markdown)
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


def display_report(result: ConversionResult):
    """Display conversion report."""
    table = Table(title="TOKEN SHREDDER REPORT", show_lines=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Input File", result.source_file)
    table.add_row("Output File", result.target_file)
    table.add_row("Format", result.format)
    table.add_row("", "")
    table.add_row("Source Tokens", f"{result.source_tokens:,}")
    table.add_row("Output Tokens", f"{result.output_tokens:,}")
    table.add_row("Tokens Saved", f"{result.tokens_saved:,} ({result.tokens_saved_pct:.1f}%)")
    table.add_row("", "")
    table.add_row("Quality Score", f"{result.quality_score:.1f}%")
    table.add_row("Processing Time", f"{result.processing_time_ms:.1f}ms")
    table.add_row("Images", str(result.images_count))
    table.add_row("Tables", str(result.tables_count))
    table.add_row("Pages", str(result.pages))

    console.print(Panel(table, border_style="blue"))


def batch_convert(
    directory: str,
    output_dir: Optional[str] = None,
    detail_level: int = 3,
    workers: int = 4,
    preserve_images: bool = False,
    quiet: bool = False,
) -> List[ConversionResult]:
    """Batch convert all supported files in a directory."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from token_shredder.config import Config

    path = Path(directory)
    files = []
    patterns = ['*.pdf', '*.docx', '*.pptx', '*.py', '*.js', '*.ts', '*.tsx',
                '*.jsx', '*.java', '*.go', '*.rs', '*.json', '*.json5', '*.csv',
                '*.html', '*.htm', '*.md', '*.txt', '*.css', '*.xlsx', '*.xls',
                '*.yaml', '*.yml', '*.xml', '*.sql', '*.toml', '*.env', '*.log',
                '*.ini', '*.cfg', '*.conf', '*.gitignore', '*.dockerignore',
                '*.svg', '*.graphql', '*.gql', '*.proto', '*.sh', '*.bash',
                '*.zsh', '*.fish', '*.ps1', '*.bat', '*.cmd', '*.dockerfile',
                'Dockerfile', '*.makefile', '*.mk', 'Makefile',
                '*.c', '*.cpp', '*.cc', '*.cxx', '*.h', '*.hpp', '*.hh', '*.hxx']
    seen = set()
    for pattern in patterns:
        for f in list(path.glob(pattern)) + list(path.glob(pattern.upper())):
            if f.resolve() not in seen:
                seen.add(f.resolve())
                files.append(f)

    config = Config()
    cache_manager = config.get_cache_manager()

    results = []
    Path(output_dir).mkdir(parents=True, exist_ok=True) if output_dir else None
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {}
        for f in files:
            if output_dir:
                out_path = str(Path(output_dir) / f.name.replace(f.suffix, '.md'))
            else:
                out_path = None
            future = executor.submit(
                convert_file,
                str(f),
                output_path=out_path,
                detail_level=detail_level,
                preserve_images=preserve_images,
                show_metrics=not quiet,
                cache_enabled=True,
            )
            futures[future] = f.name

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            disable=quiet,
        ) as progress:
            task = progress.add_task("Converting files...", total=len(files))
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                    if not quiet:
                        console.print(f"[green]Converted: {futures[future]}[/green]")
                except Exception as e:
                    err_console.print(f"[red]Error converting {futures[future]}: {e}[/red]")
                progress.advance(task)

    total_saved = sum(r.tokens_saved for r in results)
    if not quiet:
        console.print(f"\n[bold]Batch Complete:[/bold] {len(results)} files converted")
        console.print(f"Total tokens saved: {total_saved:,}")

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


@app.command()
def convert(
    file_path: str = typer.Argument(..., help="File to convert", exists=True),
    output: Optional[str] = typer.Option(None, '--output', '-o', help='Output file path'),
    detail_level: int = _detail_option(),
    preserve_images: bool = typer.Option(False, '--preserve-images', help='Preserve images'),
    embed_images: bool = typer.Option(False, '--embed-images', help='Embed images as base64'),
    include_comments: bool = typer.Option(False, '--include-comments', help='Include code comments'),
    no_deduplicate: bool = typer.Option(False, '--no-deduplicate', help='Skip deduplication'),
    no_minify: bool = typer.Option(False, '--no-minify', help='Skip code minification'),
    quiet: bool = typer.Option(False, '--quiet', '-q', help='Print nothing except errors'),
    verbose: bool = typer.Option(False, '--verbose', '-v', help='Show progress messages'),
    no_cache: bool = typer.Option(False, '--no-cache', help='Disable caching'),
):
    """Convert a file to markdown."""
    _set_verbosity(quiet, verbose)
    convert_file(
        file_path,
        output_path=output,
        detail_level=detail_level,
        preserve_images=preserve_images,
        embed_images=embed_images,
        include_comments=include_comments,
        deduplicate=not no_deduplicate,
        minify_code=not no_minify,
        show_metrics=not quiet,
        cache_enabled=not no_cache,
    )


@app.command()
def batch(
    directory: str = typer.Argument(..., help="Directory to process", exists=True),
    output: Optional[str] = typer.Option(None, '--output', '-o', help='Output directory'),
    detail_level: int = _detail_option(),
    workers: int = typer.Option(4, '--workers', '-w', help='Parallel workers'),
    preserve_images: bool = typer.Option(False, '--preserve-images', help='Preserve images'),
    quiet: bool = typer.Option(False, '--quiet', '-q', help='Print nothing except errors'),
    verbose: bool = typer.Option(False, '--verbose', '-v', help='Show progress messages'),
):
    """Batch convert all supported files in a directory."""
    _set_verbosity(quiet, verbose)
    batch_convert(
        directory,
        output_dir=output,
        detail_level=detail_level,
        workers=workers,
        preserve_images=preserve_images,
        quiet=quiet,
    )


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


def _dry_run(file_path: str, detail_level: int) -> ConversionResult:
    return convert_file(file_path, detail_level=detail_level, show_metrics=False,
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
    console.print(f"\n[bold]File Analysis: {Path(file_path).name}[/bold]")
    console.print(f"Format: {result.format}")
    console.print(f"Input tokens: {result.source_tokens:,}")
    console.print(f"Output tokens: {result.output_tokens:,}")
    console.print(f"Saved: {result.tokens_saved_pct:.1f}%")
    console.print(f"Quality score: {result.quality_score:.1f}/100")


if __name__ == "__main__":
    app()
