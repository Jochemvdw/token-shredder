"""
token_shredder - HTTP API

Run with:  pip install "token-shredder[api]"  &&  uvicorn token_shredder.api:app
Uses the same conversion pipeline as the CLI (token_shredder.main.convert_file).
"""
import os
import tempfile
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from token_shredder.main import ConversionError, _version, convert_file

MAX_UPLOAD_BYTES = 100 * 1024 * 1024

app = FastAPI(title="Token Shredder API", version=_version())


class ConversionResponse(BaseModel):
    markdown: str
    source_file: str
    format: str
    source_tokens: int
    output_tokens: int
    tokens_saved: int
    tokens_saved_pct: float
    processing_time_ms: float
    pages: int = 0
    images_count: int = 0
    tables_count: int = 0
    warnings: List[str] = []


class BatchConversionResponse(BaseModel):
    results: List[ConversionResponse]
    errors: List[str]
    total_tokens_saved: int
    files_processed: int


async def _convert_upload(file: UploadFile, detail_level: int, preserve_images: bool,
                          deduplicate: bool) -> ConversionResponse:
    name = Path(file.filename or "upload").name
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"{name}: larger than 100 MB")
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Keep the original name so the format is detected from its extension.
        tmp_path = os.path.join(tmp_dir, name)
        with open(tmp_path, "wb") as tmp:
            tmp.write(content)
        try:
            r = convert_file(tmp_path, detail_level=detail_level, preserve_images=preserve_images,
                             deduplicate=deduplicate, show_metrics=False, cache_enabled=False,
                             write_output=False)
        except ConversionError as e:
            raise HTTPException(status_code=422, detail=str(e).replace(tmp_dir + os.sep, ""))
    return ConversionResponse(
        markdown=r.markdown, source_file=name, format=r.format,
        source_tokens=r.source_tokens, output_tokens=r.output_tokens,
        tokens_saved=r.tokens_saved, tokens_saved_pct=r.tokens_saved_pct,
        processing_time_ms=r.processing_time_ms, pages=r.pages,
        images_count=r.images_count, tables_count=r.tables_count, warnings=r.warnings,
    )


@app.post("/convert", response_model=ConversionResponse)
async def convert(
    file: UploadFile = File(...),
    detail_level: int = Query(3, ge=1, le=5),
    preserve_images: bool = False,
    deduplicate: bool = True,
):
    """Convert one uploaded file to markdown."""
    return await _convert_upload(file, detail_level, preserve_images, deduplicate)


@app.post("/batch", response_model=BatchConversionResponse)
async def batch(
    files: List[UploadFile] = File(...),
    detail_level: int = Query(3, ge=1, le=5),
    preserve_images: bool = False,
):
    """Convert several uploaded files; failures are listed in `errors`."""
    results, errors = [], []
    for f in files:
        try:
            results.append(await _convert_upload(f, detail_level, preserve_images, True))
        except HTTPException as e:
            errors.append(str(e.detail))
    return BatchConversionResponse(
        results=results, errors=errors,
        total_tokens_saved=sum(r.tokens_saved for r in results), files_processed=len(results),
    )


@app.get("/health")
async def health():
    return {"status": "ok", "version": _version()}
