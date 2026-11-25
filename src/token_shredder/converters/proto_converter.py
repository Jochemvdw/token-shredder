"""
token_shredder - Protocol Buffer Converter
Converts .proto files to markdown
"""
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.utils.logger import setup_logger
import re

logger = setup_logger(__name__)


class ProtoConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.proto']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='proto',
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        markdown_parts = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            markdown_parts.append(f"# Protocol Buffer: {Path(file_path).name}")
            markdown_parts.append("")

            # Extract package
            package = re.search(r'package (\w+);', content)
            if package:
                markdown_parts.append(f"## Package: `{package.group(1)}`")
                markdown_parts.append("")

            # Extract messages
            messages = re.findall(r'message (\w+) \\{([^}]+)\\}', content, re.DOTALL)
            if messages:
                markdown_parts.append("## Messages")
                for name, body in messages:
                    fields = re.findall(r'(\w+) (\w+) = \\d+;', body)
                    markdown_parts.append(f"### {name}")
                    markdown_parts.append(f"Fields: {len(fields)}")
                    if options.detail_level >= 3:
                        for field_name, field_type in fields[:10]:
                            markdown_parts.append(f"  - {field_type} {field_name}")
                    markdown_parts.append("")

            # Extract services
            services = re.findall(r'service (\w+) \\{([^}]+)\\}', content, re.DOTALL)
            if services:
                markdown_parts.append("## Services")
                for name, body in services:
                    rpcs = re.findall(r'rpc (\w+) \\((\w+)\\) returns \\((\w+)\\);', body)
                    markdown_parts.append(f"### {name}")
                    markdown_parts.append(f"RPCs: {len(rpcs)}")
                    markdown_parts.append("")

            # Extract enums
            enums = re.findall(r'enum (\w+) \\{([^}]+)\\}', content, re.DOTALL)
            if enums:
                markdown_parts.append("## Enums")
                for name, values in enums:
                    markdown_parts.append(f"- `{name}`: {len(values.split(','))} values")
                markdown_parts.append("")

        except Exception as e:
            logger.debug(f"Error reading proto: {e}")
            markdown_parts.append(f"[Error reading proto: {e}]")

        return "\n".join(markdown_parts)

    def get_file_info(self, file_path: str) -> dict:
        try:
            with open(file_path, encoding='utf-8', errors='replace') as f:
                content = f.read()
            return {'messages': len(re.findall(r'message \\w+', content)), 'size': len(content)}
        except:
            return {'messages': 0, 'size': 0}
