"""
token_shredder - Gitignore Converter
Converts .gitignore files to markdown
"""
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.utils.logger import setup_logger

logger = setup_logger(__name__)


class GitignoreConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.gitignore', '.dockerignore', '.gitattributes']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='gitignore',
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        markdown_parts = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()

            markdown_parts.append(f"# {file_path}")
            markdown_parts.append("")

            # Categorize patterns
            negations = []
            directories = []
            files = []
            patterns = []

            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith('!'):
                    negations.append(line)
                elif '**' in line or '/' in line:
                    directories.append(line)
                elif '.' in line:
                    files.append(line)
                else:
                    patterns.append(line)

            if negations:
                markdown_parts.append("## Negations (!)")
                for p in negations:
                    markdown_parts.append(f"- `{p}`")
                markdown_parts.append("")

            if directories:
                markdown_parts.append("## Directory Patterns")
                for p in directories:
                    markdown_parts.append(f"- `{p}`")
                markdown_parts.append("")

            if files:
                markdown_parts.append("## File Patterns")
                for p in files:
                    markdown_parts.append(f"- `{p}`")
                markdown_parts.append("")

            if patterns:
                markdown_parts.append("## General Patterns")
                for p in patterns:
                    markdown_parts.append(f"- `{p}`")
                markdown_parts.append("")

        except Exception as e:
            logger.error(f"Error reading gitignore: {e}")
            markdown_parts.append(f"[Error reading gitignore: {e}]")

        return "\n".join(markdown_parts)

    def get_file_info(self, file_path: str) -> dict:
        try:
            with open(file_path, encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            patterns = [l for l in lines if l.strip() and not l.strip().startswith('#')]
            return {'patterns': len(patterns), 'total_lines': len(lines)}
        except:
            return {'patterns': 0, 'total_lines': 0}
