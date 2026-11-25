"""
token_shredder - Input sources other than local files: URLs and stdin.

Both are written to a temporary file with the right extension, so the normal
converters handle them. Callers must call cleanup() when done.
"""
import os
import re
import shutil
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024
USER_AGENT = "token-shredder (+https://github.com/Jochemvdw/token-shredder)"

_CONTENT_TYPES = {
    "text/html": "html", "application/xhtml+xml": "html",
    "application/pdf": "pdf",
    "application/json": "json", "application/x-ndjson": "jsonl",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "text/csv": "csv", "text/markdown": "md", "text/plain": "txt",
    "application/xml": "xml", "text/xml": "xml", "application/yaml": "yaml",
    "text/yaml": "yaml", "application/toml": "toml",
}


class SourceError(Exception):
    pass


_BINARY = {"pdf", "docx", "pptx", "xlsx", "xls"}


def is_url(source: str) -> bool:
    return bool(re.match(r"^https?://", source, re.IGNORECASE))


def _looks_binary(head: bytes) -> bool:
    if b"\x00" in head:
        return True
    control = sum(1 for b in head if b < 9 or 13 < b < 32)
    return bool(head) and control / len(head) > 0.1


def sniff_format(head: bytes) -> str:
    """Guess a format from the first bytes when there is no name or content type."""
    text = head.lstrip()[:512]
    if text.startswith(b"%PDF"):
        return "pdf"
    if text.startswith(b"PK"):
        return "docx"  # zip-based Office file; DOCX is the most common
    low = text.lower()
    if low.startswith((b"<!doctype html", b"<html")) or b"<body" in low:
        return "html"
    if text.startswith((b"{", b"[")):
        lines = [ln for ln in head.splitlines() if ln.strip()][:3]
        if len(lines) > 1 and all(ln.strip().startswith(b"{") for ln in lines):
            return "jsonl"
        return "json"
    if text.startswith(b"<?xml") or text.startswith(b"<"):
        return "xml"
    return "txt"


class Materialized:
    def __init__(self, path: str, name: str, file_format: str, tmp_dir: str):
        self.path, self.name, self.format, self._tmp_dir = path, name, file_format, tmp_dir

    def cleanup(self) -> None:
        shutil.rmtree(self._tmp_dir, ignore_errors=True)


def _write_tmp(data: bytes, file_format: str, stem: str) -> tuple:
    tmp_dir = tempfile.mkdtemp(prefix="token-shredder-")
    safe = re.sub(r"[^\w.-]", "_", stem)[:60] or "input"
    path = os.path.join(tmp_dir, f"{safe}.{file_format}")
    with open(path, "wb") as f:
        f.write(data)
    return path, tmp_dir


def fetch_url(url: str, file_format: Optional[str] = None, timeout: int = 30) -> Materialized:
    """Download url (http/https only, max 50 MB) to a temp file."""
    if not is_url(url):
        raise SourceError(f"Not an http(s) URL: {url}")
    import time
    deadline = time.monotonic() + timeout * 2  # total time, not just per read
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            chunks, total = [], 0
            while total <= MAX_DOWNLOAD_BYTES:
                chunk = resp.read(65536)
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if time.monotonic() > deadline:
                    raise SourceError(f"Download of {url} took longer than {timeout * 2} s")
            data = b"".join(chunks)
            content_type = (resp.headers.get_content_type() or "").lower()
            charset = resp.headers.get_content_charset()
            final_url = resp.geturl()
    except SourceError:
        raise
    except Exception as e:
        raise SourceError(f"Could not download {url}: {e}") from e
    if len(data) > MAX_DOWNLOAD_BYTES:
        raise SourceError(f"{url} is larger than 50 MB")
    path_part = urlparse(final_url).path
    suffix = Path(path_part).suffix.lower().lstrip(".")
    fmt = (file_format or _CONTENT_TYPES.get(content_type)
           or (suffix if suffix and len(suffix) <= 5 else None) or sniff_format(data[:4096]))
    stem = Path(path_part).stem or urlparse(final_url).netloc
    if charset and fmt not in _BINARY and charset.lower().replace("_", "-") not in ("utf-8", "utf8"):
        try:
            data = data.decode(charset, errors="replace").encode("utf-8")
        except LookupError:
            pass  # unknown charset name: keep the bytes, the converter will cope
    path, tmp_dir = _write_tmp(data, fmt, stem)
    return Materialized(path, url, fmt, tmp_dir)


def read_stdin(stream, file_format: Optional[str] = None) -> Materialized:
    data = stream.read(MAX_DOWNLOAD_BYTES + 1)
    if len(data) > MAX_DOWNLOAD_BYTES:
        raise SourceError("stdin input is larger than 50 MB")
    if not data.strip():
        raise SourceError("stdin is empty")
    fmt = file_format or sniff_format(data[:4096])
    if fmt == "txt" and _looks_binary(data[:4096]):
        raise SourceError("stdin looks like binary data of an unknown type; pass --type (e.g. --type pdf)")
    path, tmp_dir = _write_tmp(data, fmt, "stdin")
    return Materialized(path, "stdin", fmt, tmp_dir)
