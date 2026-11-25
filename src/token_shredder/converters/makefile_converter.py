"""
token_shredder - Makefile Converter
Converts Makefiles to markdown
"""
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.utils.logger import setup_logger
import re

logger = setup_logger(__name__)


class MakefileConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.makefile', '.mk', 'Makefile', 'makefile']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='makefile',
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        markdown_parts = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            markdown_parts.append(f"# Makefile: {file_path}")
            markdown_parts.append("")

            # Extract targets and their dependencies
            targets = re.findall(r'^(\\w+):([^=]+?)(?=^\\w+:|$)', content, re.MULTILINE | re.DOTALL)

            markdown_parts.append("## Targets")
            for target, deps_body in targets[:20]:  # Limit
                deps = [d.strip() for d in deps_body.split('$') if d.strip() and not d.strip().startswith('#')]
                markdown_parts.append(f"### {target}")
                if deps:
                    markdown_parts.append(f"Dependencies: {', '.join(deps[:5])}")
                markdown_parts.append("")

            # Extract variables
            variables = re.findall(r'^(\\w+)\\s*=\\s*(.+?)(?=^\\w+\\s*=|$)', content, re.MULTILINE | re.DOTALL)
            if variables:
                markdown_parts.append("## Variables")
                for var, value in variables[:15]:
                    value = value.strip().split('\n')[0][:100]
                    markdown_parts.append(f"- `{var}` = `{value}`")
                markdown_parts.append("")

        except Exception as e:
            logger.error(f"Error reading Makefile: {e}")
            markdown_parts.append(f"[Error reading Makefile: {e}]")

        return "\n".join(markdown_parts)

    def get_file_info(self, file_path: str) -> dict:
        try:
            with open(file_path, encoding='utf-8', errors='replace') as f:
                content = f.read()
            targets = re.findall(r'^\\w+:', content, re.MULTILINE)
            return {'targets': len(targets), 'lines': len(content.splitlines())}
        except:
            return {'targets': 0, 'lines': 0}
