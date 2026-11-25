"""
token_shredder - SQL Converter
Converts SQL files to markdown
"""
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.utils.logger import setup_logger

logger = setup_logger(__name__)


class SQLConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.sql']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='sql',
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        markdown_parts = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            if options.detail_level >= 5:
                return content

            markdown_parts.append(f"# SQL Script: {Path(file_path).name}")
            markdown_parts.append("")

            statements = self._split_statements(content)

            for stmt in statements[:20]:
                stmt = stmt.strip()
                if not stmt:
                    continue
                stmt_type = self._get_statement_type(stmt)
                markdown_parts.append(f"## {stmt_type}")
                markdown_parts.append(f"```sql\n{stmt[:500]}\n```")
                markdown_parts.append("")

            if len(statements) > 20:
                markdown_parts.append(f"... ({len(statements) - 20} more statements)")
                markdown_parts.append("")

        except Exception as e:
            logger.error(f"Error reading SQL: {e}")
            markdown_parts.append(f"[Error reading SQL: {e}]")

        return "\n".join(markdown_parts)

    def _split_statements(self, content: str) -> list:
        statements = []
        current = []
        in_string = False
        string_char = None

        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('--'):
                if current:
                    current.append(line)
                continue

            for i, char in enumerate(line):
                if char in ("'", '"') and (i == 0 or line[i-1] != '\\'):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False

            if not in_string and line.upper().startswith(('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'GRANT', 'REVOKE', 'BEGIN', 'COMMIT', 'ROLLBACK')):
                if current:
                    statements.append('\n'.join(current))
                current = [line]
            elif current:
                current.append(line)

        if current:
            statements.append('\n'.join(current))

        return statements

    def _get_statement_type(self, stmt: str) -> str:
        stmt_upper = stmt.strip().upper().split()[0]
        type_map = {
            'SELECT': 'SELECT Query',
            'INSERT': 'INSERT Statement',
            'UPDATE': 'UPDATE Statement',
            'DELETE': 'DELETE Statement',
            'CREATE': 'CREATE Statement',
            'ALTER': 'ALTER Statement',
            'DROP': 'DROP Statement',
            'GRANT': 'GRANT Statement',
            'REVOKE': 'REVOKE Statement',
        }
        return type_map.get(stmt_upper, 'SQL Statement')

    def get_file_info(self, file_path: str) -> dict:
        try:
            with open(file_path, encoding='utf-8', errors='replace') as f:
                content = f.read()
            statements = self._split_statements(content)
            return {'statements': len(statements), 'lines': len(content.splitlines())}
        except:
            return {'statements': 0, 'lines': 0}
