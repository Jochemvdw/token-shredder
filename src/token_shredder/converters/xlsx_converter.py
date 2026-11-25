"""
token_shredder - XLSX Converter
Converts Excel spreadsheets to markdown tables
"""
from openpyxl import load_workbook
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.profiling import summarize_table
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
            try:
                wb_formulas = load_workbook(file_path, data_only=False)
            except Exception:
                wb_formulas = None

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

                ws_f = wb_formulas[sheet_name] if wb_formulas is not None else None
                markdown_parts.append(self._sheet_to_markdown(ws, ws_f, options.detail_level))
                markdown_parts.append("")

        except Exception as e:
            logger.debug(f"Error reading XLSX: {e}")
            markdown_parts.append(f"[Error reading XLSX: {e}]")

        return "\n".join(markdown_parts)

    @staticmethod
    def _cell_text(value) -> str:
        if value is None:
            return ''
        return str(value)

    def _sheet_to_markdown(self, ws, ws_formulas=None, level: int = 3) -> str:
        formula_rows = ws_formulas.iter_rows(values_only=True) if ws_formulas is not None else None

        def rows():
            for row in ws.iter_rows(values_only=True):
                frow = next(formula_rows, None) if formula_rows is not None else None
                values = list(row)
                if frow is not None:
                    # No cached value (never calculated): fall back to formula text
                    for i, v in enumerate(values):
                        if v is None and i < len(frow) and isinstance(frow[i], str) and frow[i].startswith('='):
                            values[i] = frow[i]
                cells = [self._cell_text(c) for c in values]
                if all(c == '' for c in cells):
                    continue
                yield cells

        it = rows()
        header = next(it, None)  # first non-empty row
        if header is None:
            return "_(No data)_"
        return summarize_table(header, it, level)

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