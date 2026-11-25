"""
token_shredder - API Server
"""
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
import tempfile
import os
import hashlib
from pathlib import Path

from token_shredder.converters import get_converter, detect_file_format
from token_shredder.processors import Deduplicator
from token_shredder.metrics import TokenCounter, QualityScorer
from token_shredder.utils.file_handler import FileHandler
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.config import Config, CacheManager

app = FastAPI(title="Token Shredder API", version="0.3.0")


class ConversionResponse(BaseModel):
    markdown: str
    source_file: str
    target_file: str
    format: str
    source_tokens: int
    output_tokens: int
    tokens_saved: int
    tokens_saved_pct: float
    quality_score: float
    processing_time_ms: float
    pages: int = 0
    images_count: int = 0
    tables_count: int = 0
    warnings: List[str] = []


class BatchConversionResponse(BaseModel):
    results: List[ConversionResponse]
    total_tokens_saved: int
    files_processed: int


@app.post("/convert", response_model=ConversionResponse)
async def convert_file(
    file: UploadFile = File(...),
    detail_level: int = 3,
    preserve_images: bool = False,
    deduplicate: bool = True,
    cache_enabled: bool = True,
):
    """Convert uploaded file to markdown."""
    file_handler = FileHandler()
    config = Config()
    cache_manager = config.get_cache_manager() if cache_enabled else None

    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        if not file_handler.validate_file(tmp_path):
            raise HTTPException(status_code=400, detail="Invalid file")

        file_format = detect_file_format(tmp_path)
        converter = get_converter(file_format)
        if not converter:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {file_format}")

        options = ConversionOptions(
            detail_level=detail_level,
            preserve_images=preserve_images,
        )

        result = converter.convert(tmp_path, options)

        if deduplicate:
            dedup = Deduplicator()
            result.markdown = dedup.process(result.markdown)

        token_counter = TokenCounter()
        source_md = converter.convert_to_markdown(tmp_path, options)
        result.source_tokens = token_counter.estimate(source_md)
        result.output_tokens = token_counter.estimate(result.markdown)
        result.tokens_saved = result.source_tokens - result.output_tokens
        result.tokens_saved_pct = (result.tokens_saved / result.source_tokens * 100) if result.source_tokens > 0 else 0.0

        quality_scorer = QualityScorer()
        result.quality_score = quality_scorer.score(result.markdown, source_md)

        if cache_manager:
            options_hash = hashlib.md5(f"{detail_level}{preserve_images}".encode()).hexdigest()
            with open(tmp_path, 'rb') as f:
                file_content = f.read()
            content_hash = hashlib.md5(file_content).hexdigest()[:12]
            cache_manager.set(tmp_path, options_hash, result.markdown)

        return ConversionResponse(
            markdown=result.markdown,
            source_file=file.filename,
            target_file=result.target_file,
            format=file_format,
            source_tokens=result.source_tokens,
            output_tokens=result.output_tokens,
            tokens_saved=result.tokens_saved,
            tokens_saved_pct=result.tokens_saved_pct,
            quality_score=result.quality_score,
            processing_time_ms=result.processing_time_ms,
            pages=result.pages,
            images_count=result.images_count,
            tables_count=result.tables_count,
            warnings=result.warnings,
        )

    finally:
        os.unlink(tmp_path)


@app.post("/batch", response_model=BatchConversionResponse)
async def batch_convert(
    files: List[UploadFile] = File(...),
    detail_level: int = 3,
    preserve_images: bool = False,
    workers: int = 4,
):
    """Batch convert multiple uploaded files."""
    results = []
    total_saved = 0

    for file in files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            file_handler = FileHandler()
            if not file_handler.validate_file(tmp_path):
                continue

            file_format = detect_file_format(tmp_path)
            converter = get_converter(file_format)
            if not converter:
                continue

            options = ConversionOptions(detail_level=detail_level, preserve_images=preserve_images)
            result = converter.convert(tmp_path, options)

            token_counter = TokenCounter()
            source_md = converter.convert_to_markdown(tmp_path, options)
            result.source_tokens = token_counter.estimate(source_md)
            result.output_tokens = token_counter.estimate(result.markdown)
            result.tokens_saved = result.source_tokens - result.output_tokens
            result.tokens_saved_pct = (result.tokens_saved / result.source_tokens * 100) if result.source_tokens > 0 else 0.0

            results.append(result)
            total_saved += result.tokens_saved
        finally:
            os.unlink(tmp_path)

    return BatchConversionResponse(
        results=[ConversionResponse(
            markdown=r.markdown,
            source_file=r.source_file,
            target_file=r.target_file,
            format=r.format,
            source_tokens=r.source_tokens,
            output_tokens=r.output_tokens,
            tokens_saved=r.tokens_saved,
            tokens_saved_pct=r.tokens_saved_pct,
            quality_score=r.quality_score,
            processing_time_ms=r.processing_time_ms,
            pages=r.pages,
            images_count=r.images_count,
            tables_count=r.tables_count,
            warnings=r.warnings,
        ) for r in results],
        total_tokens_saved=total_saved,
        files_processed=len(results),
    )


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.3.0"}


@app.get("/metrics")
async def metrics():
    return {"version": "0.3.0", "cache_enabled": True}
