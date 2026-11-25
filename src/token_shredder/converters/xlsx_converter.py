"""
token_shredder - XLSX Converter
Converts Excel spreadsheets to markdown tables
"""
from openpyxl import load_workbook
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.utils.logger import setup_logger

logger = setup_logger(__name__)


class XLSXConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.xlsx', '.xls']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='xlsx',
            tables_count=self._count_tables(markdown),
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        markdown_parts = []
        try:
            wb = load_workbook(file_path, data_only=True)

            markdown_parts.append(f"# Excel Spreadsheet: {file_path}")
            markdown_parts.append(f"- Sheets: {len(wb.sheetnames)}")
            markdown_parts.append("")

            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                markdown_parts.append(f"## Sheet: {sheet_name}")
                markdown_parts.append(f"- Rows: {ws.max_row}, Columns: {ws.max_column}")
                markdown_parts.append("")

                if ws.max_row == 0 or ws.max_column == 0:
                    markdown_parts.append("_(Empty sheet)_")
                    markdown_parts.append("")
                    continue

                markdown_parts.append(self._sheet_to_markdown(ws))
                markdown_parts.append("")

        except Exception as e:
            logger.error(f"Error reading XLSX: {e}")
            markdown_parts.append(f"[Error reading XLSX: {e}]")

        return "\n".join(markdown_parts)

    def _sheet_to_markdown(self, ws) -> str:
        md = []
        for row_idx, row in enumerate(ws.iter_rows(values_only=True), 1):
            if row_idx > 50:
                md.append(f"... ({ws.max_row - 50} more rows)")
                break
            cells = [str(cell) if cell is not None else '' for cell in row]
            if all(c == '' for c in cells):
                continue
            md.append("| " + " | ".join(cells) + " |")

        if not md:
            return "_(No data)_"

        header = md[0] if md else ""
        separator = "| " + " | ".join(["---"] * (len(header.split('|')) - 2)) + " |"
        return '\n'.join([header, separator] + md[1:])

    def get_file_info(self, file_path: str) -> dict:
        try:
            wb = load_workbook(file_path, data_only=True)
            total_rows = sum(ws.max_row for ws in wb.worksheets)
            total_cols = sum(ws.max_column for ws in wb.worksheets)
            return {
                'sheets': len(wb.sheetnames),
                'total_rows': total_rows,
                'total_columns': total_cols,
            }
        except:
            return {'sheets': 0, 'total_rows': 0, 'total_columns': 0}