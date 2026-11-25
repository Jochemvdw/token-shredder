"""
token_shredder - CSV Converter
Converts CSV files to markdown tables with analysis
"""
import csv
import os
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.profiling import summarize_table
from token_shredder.utils.logger import setup_logger

logger = setup_logger(__name__)


class CSVConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.csv', '.tsv']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='csv',
            tables_count=self._count_tables(markdown),
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        """Levels 1-3: a profile of the table. Level 4+: all data as CSV (smaller than a
        markdown table, so sizes stay monotonic across levels)."""
        try:
            csv.field_size_limit(2 ** 24)
            size = os.path.getsize(file_path)
            with open(file_path, 'r', encoding='utf-8', errors='replace', newline='') as f:
                head = f.read(65536)
                f.seek(0)
                delimiter = self._sniff_delimiter(head, file_path)
                if options.detail_level >= 4:
                    return f"```csv\n{f.read().rstrip()}\n```\n"
                reader = csv.reader(f, delimiter=delimiter)
                headers = next(reader, None)
                while headers is not None and not headers:
                    headers = next(reader, None)
                if headers is None:
                    return ""
                rows = (r for r in reader if r)
                body = "\n" + summarize_table(headers, rows, options.detail_level)
            if size < 1_000_000:
                # Never return a lossy summary that is longer than the data itself.
                with open(file_path, 'r', encoding='utf-8', errors='replace', newline='') as f:
                    full = f"```csv\n{f.read().rstrip()}\n```\n"
                if len(body) >= len(full):
                    return full
            return body
        except Exception as e:
            logger.error(f"Error reading CSV: {e}")
            return f"[Error reading CSV: {e}]"

    @staticmethod
    def _sniff_delimiter(head: str, file_path: str) -> str:
        if file_path.lower().endswith('.tsv'):
            return '\t'
        try:
            return csv.Sniffer().sniff(head[:16384], delimiters=',;\t|').delimiter
        except csv.Error:
            return ','

    def get_file_info(self, file_path: str) -> dict:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace', newline='') as f:
                reader = csv.reader(f)
                rows = list(reader)
            return {'rows': len(rows) - 1, 'columns': len(rows[0]) if rows else 0}
        except:
            return {'rows': 0, 'columns': 0}
