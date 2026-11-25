"""
token_shredder - ENV Converter
Converts .env files to markdown
"""
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.utils.logger import setup_logger

logger = setup_logger(__name__)


class ENVConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.env', '.env.local', '.env.example']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='env',
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        markdown_parts = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()

            markdown_parts.append(f"# Environment Config: {file_path}")
            markdown_parts.append("")
            markdown_parts.append(f"## Variables ({len([l for l in lines if l.strip() and not l.startswith('#')])})")
            markdown_parts.append("")

            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                key, _, value = line.partition('=')
                masked_value = value[:20] + '...' if len(value) > 20 else value
                markdown_parts.append(f"### {key}")
                markdown_parts.append(f"Value: `{masked_value.strip()}`")
                markdown_parts.append("")

        except Exception as e:
            logger.debug(f"Error reading ENV: {e}")
            markdown_parts.append(f"[Error reading ENV: {e}]")

        return "\n".join(markdown_parts)

    def get_file_info(self, file_path: str) -> dict:
        try:
            with open(file_path, encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            return {'variables': len([l for l in lines if l.strip() and not l.startswith('#')]), 'total_lines': len(lines)}
        except:
            return {'variables': 0, 'total_lines': 0}
