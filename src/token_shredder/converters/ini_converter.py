"""
token_shredder - INI Config Converter
Converts INI config files to markdown
"""
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.utils.logger import setup_logger

logger = setup_logger(__name__)


class INIConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.ini', '.cfg', '.conf']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='ini',
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        if options.detail_level >= 5:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception:
                pass

        markdown_parts = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            markdown_parts.append(f"# Config File: {Path(file_path).name}")
            markdown_parts.append("")
            markdown_parts.append("## Structure")

            sections = {}
            current_section = None

            for line in lines:
                line = line.strip()
                if not line or line.startswith(';') or line.startswith('#'):
                    continue
                if line.startswith('[') and line.endswith(']'):
                    current_section = line[1:-1]
                    sections[current_section] = []
                elif current_section:
                    key, _, value = line.partition('=')
                    sections[current_section].append((key.strip(), value.strip()))

            for section, items in sections.items():
                markdown_parts.append(f"- **[{section}]**: {len(items)} settings")

        except Exception as e:
            logger.error(f"Error reading INI: {e}")
            markdown_parts.append(f"[Error reading INI: {e}]")

        return "\n".join(markdown_parts)

    def get_file_info(self, file_path: str) -> dict:
        try:
            with open(file_path) as f:
                lines = f.readlines()
            sections = len([l for l in lines if l.strip().startswith('[')])
            return {'sections': sections, 'lines': len(lines)}
        except:
            return {'sections': 0, 'lines': 0}
