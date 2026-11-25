"""
token_shredder - Script Converter
Converts shell/batch scripts to markdown
"""
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.utils.logger import setup_logger
import re

logger = setup_logger(__name__)


class ScriptConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='script',
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        markdown_parts = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            markdown_parts.append(f"# Script: {file_path}")
            markdown_parts.append("")

            # Extract shebang
            shebang = re.match(r'#!.*', content)
            if shebang:
                markdown_parts.append(f"## Shebang")
                markdown_parts.append(f"```\n{shebang.group(0)}\n```")
                markdown_parts.append("")

            # Extract functions
            functions = re.findall(r'(?:^|\n)(\w+)\s*\([^)]*\)\s*\{', content, re.MULTILINE)
            if functions:
                markdown_parts.append("## Functions")
                for f in functions:
                    markdown_parts.append(f"- `{f}()`")
                markdown_parts.append("")

            # Extract commands
            commands = re.findall(r'^\s*(?:export|echo|cd|ls|mkdir|rm|cp|mv|git|npm|pip|python|java|curl|wget|chmod|chown|sudo|systemctl|docker|kubectl)\b', content, re.MULTILINE)
            if commands:
                markdown_parts.append("## Commands Used")
                cmd_counts = {}
                for cmd in commands:
                    cmd_counts[cmd] = cmd_counts.get(cmd, 0) + 1
                for cmd, count in sorted(cmd_counts.items(), key=lambda x: -x[1]):
                    markdown_parts.append(f"- `{cmd}`: {count} times")
                markdown_parts.append("")

            # Extract environment variables
            env_vars = re.findall(r'(?:^|\n)export\s+(\w+)=', content, re.MULTILINE)
            if env_vars:
                markdown_parts.append("## Environment Variables")
                for v in env_vars:
                    markdown_parts.append(f"- `{v}`")
                markdown_parts.append("")

        except Exception as e:
            logger.error(f"Error reading script: {e}")
            markdown_parts.append(f"[Error reading script: {e}]")

        return "\n".join(markdown_parts)

    def get_file_info(self, file_path: str) -> dict:
        try:
            with open(file_path, encoding='utf-8', errors='ignore') as f:
                content = f.read()
            functions = re.findall(r'\w+\s*\([^)]*\)\s*\{', content, re.MULTILINE)
            return {'lines': len(content.splitlines()), 'functions': len(functions)}
        except:
            return {'lines': 0, 'functions': 0}
