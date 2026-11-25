"""
token_shredder - CSV Converter
Converts CSV files to markdown tables with analysis
"""
import csv
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.utils.logger import setup_logger

logger = setup_logger(__name__)


class CSVConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.csv']

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
        markdown_parts = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)

            if not rows:
                return ""

            headers = rows[0]
            markdown_parts.append("| " + " | ".join(headers) + " |")
            markdown_parts.append("| " + " | ".join(["---"] * len(headers)) + " |")
            for row in rows[1:51]:
                markdown_parts.append("| " + " | ".join(str(c) for c in row) + " |")
            if len(rows) > 51:
                markdown_parts.append(f"... ({len(rows) - 51} more rows)")

        except Exception as e:
            logger.error(f"Error reading CSV: {e}")
            markdown_parts.append(f"[Error reading CSV: {e}]")

        return "\n".join(markdown_parts)

    def get_file_info(self, file_path: str) -> dict:
        try:
            with open(file_path) as f:
                reader = csv.reader(f)
                rows = list(reader)
            return {'rows': len(rows) - 1, 'columns': len(rows[0]) if rows else 0}
        except:
            return {'rows': 0, 'columns': 0}
