"""
token_shredder - LOG Converter
Converts log files to markdown
"""
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.utils.logger import setup_logger

logger = setup_logger(__name__)


class LOGConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.log']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='log',
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        markdown_parts = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            markdown_parts.append(f"# Log File: {file_path}")
            markdown_parts.append(f"- Total lines: {len(lines)}")
            markdown_parts.append("")

            errors = []
            warnings = []
            info = []

            for line in lines[:200]:  # Limit for performance
                line = line.strip()
                if not line:
                    continue
                if 'ERROR' in line or 'error' in line or 'FATAL' in line:
                    errors.append(line)
                elif 'WARN' in line or 'warning' in line:
                    warnings.append(line)
                else:
                    info.append(line)

            if errors:
                markdown_parts.append("## Errors")
                for e in errors[:10]:
                    markdown_parts.append(f"- {e}")
                markdown_parts.append("")

            if warnings:
                markdown_parts.append("## Warnings")
                for w in warnings[:10]:
                    markdown_parts.append(f"- {w}")
                markdown_parts.append("")

            if info:
                markdown_parts.append("## Info")
                for i in info[:20]:
                    markdown_parts.append(f"- {i}")
                markdown_parts.append("")

        except Exception as e:
            logger.error(f"Error reading LOG: {e}")
            markdown_parts.append(f"[Error reading LOG: {e}]")

        return "\n".join(markdown_parts)

    def get_file_info(self, file_path: str) -> dict:
        try:
            with open(file_path, encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            return {'lines': len(lines)}
        except:
            return {'lines': 0}
