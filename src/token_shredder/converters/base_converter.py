"""
token_shredder - Base Converter
"""
import re
from abc import ABC, abstractmethod
from typing import Optional
from token_shredder.models import ConversionResult, ConversionOptions


class BaseConverter(ABC):
    @abstractmethod
    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        """Convert file to markdown."""
        pass

    @abstractmethod
    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        """Convert file to markdown string."""
        pass

    @abstractmethod
    def get_file_info(self, file_path: str) -> dict:
        """Get file information without full conversion."""
        pass

    @staticmethod
    def get_supported_extensions() -> list:
        return []

    def _stream_read(self, file_path: str, chunk_size: int = 8192) -> str:
        """Stream read file for large file support."""
        parts = []
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for chunk in iter(lambda: f.read(chunk_size), ''):
                parts.append(chunk)
        return ''.join(parts)

    @staticmethod
    def _count_tables(markdown: str) -> int:
        """Count markdown tables by matching table separator rows."""
        return len(re.findall(r'^\|[-| ]+\|$', markdown, re.MULTILINE))
