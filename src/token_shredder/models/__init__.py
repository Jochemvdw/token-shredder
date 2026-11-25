"""
token_shredder - Token Shredder - Main Entry Point
A complementary token optimization tool that converts files to markdown for dramatic input token reduction.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class ConversionResult:
    markdown: str
    source_file: str
    target_file: str
    format: str

    source_tokens: int = 0
    output_tokens: int = 0
    tokens_saved: int = 0
    tokens_saved_pct: float = 0.0
    quality_score: float = 0.0

    processing_time_ms: float = 0.0
    pages: int = 0
    images_count: int = 0
    tables_count: int = 0
    warnings: list = field(default_factory=list)

    detail_level: int = 3
    preserve_images: bool = False
    
    # Per-format token savings tracking
    format_token_savings: dict = field(default_factory=dict)


@dataclass
class ConversionOptions:
    detail_level: int = 3
    preserve_images: bool = False
    embed_images: bool = False
    include_comments: bool = False
    output_format: str = "markdown"
    output_path: Optional[str] = None


@dataclass
class ProcessingOptions:
    deduplicate: bool = True
    minify_code: bool = True
    optimize_structure: bool = True
    summarize: bool = False
    count_exact: bool = False
    score_quality: bool = False
    cache_enabled: bool = True
