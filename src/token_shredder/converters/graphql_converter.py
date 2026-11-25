"""
token_shredder - GraphQL Converter
Converts GraphQL schema files to markdown
"""
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.utils.logger import setup_logger
import re

logger = setup_logger(__name__)


class GraphQLConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.graphql', '.gql']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='graphql',
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        markdown_parts = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            markdown_parts.append(f"# GraphQL Schema: {file_path}")
            markdown_parts.append("")

            # Extract types
            types = re.findall(r'type (\w+)', content)
            inputs = re.findall(r'input (\w+)', content)
            interfaces = re.findall(r'interface (\w+)', content)
            enums = re.findall(r'enum (\w+)', content)
            mutations = re.findall(r'type (\w+) \\{[^}]*mutation', content, re.DOTALL)

            if types:
                markdown_parts.append("## Types")
                for t in types:
                    markdown_parts.append(f"- `{t}`")
                markdown_parts.append("")

            if inputs:
                markdown_parts.append("## Inputs")
                for i in inputs:
                    markdown_parts.append(f"- `{i}`")
                markdown_parts.append("")

            if interfaces:
                markdown_parts.append("## Interfaces")
                for i in interfaces:
                    markdown_parts.append(f"- `{i}`")
                markdown_parts.append("")

            if enums:
                markdown_parts.append("## Enums")
                for e in enums:
                    pattern = re.compile(re.escape(e) + r'\s*\{\s*([^}]+)\}', re.DOTALL)
                    enum_values = pattern.findall(content)
                    markdown_parts.append(f"- `{e}`: {len(enum_values)} values")
                markdown_parts.append("")

            if mutations:
                markdown_parts.append("## Mutations")
                for m in mutations:
                    markdown_parts.append(f"- `{m}`")
                markdown_parts.append("")

            # Extract queries
            queries = re.findall(r'type Query \\{([^}]+)\\}', content, re.DOTALL)
            if queries:
                markdown_parts.append("## Queries")
                for q in queries:
                    fields = re.findall(r'(\w+)\\s*:', q)
                    for f in fields:
                        markdown_parts.append(f"- `{f}`")
                markdown_parts.append("")

        except Exception as e:
            logger.error(f"Error reading GraphQL: {e}")
            markdown_parts.append(f"[Error reading GraphQL: {e}]")

        return "\n".join(markdown_parts)

    def get_file_info(self, file_path: str) -> dict:
        try:
            with open(file_path) as f:
                content = f.read()
            return {'types': len(re.findall(r'type \\w+', content)), 'size': len(content)}
        except:
            return {'types': 0, 'size': 0}
