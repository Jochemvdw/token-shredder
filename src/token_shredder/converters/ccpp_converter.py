"""
token_shredder - C/C++/Header Converter
Converts C, C++, and header files to markdown
"""
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.utils.logger import setup_logger
import re

logger = setup_logger(__name__)


class CCppConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hh', '.hxx']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='cpp' if file_path.endswith(('.cpp', '.cc', '.cxx')) else 'c',
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        markdown_parts = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            markdown_parts.append(f"# {file_path}")
            markdown_parts.append("")

            # Extract includes
            includes = re.findall(r'#include\\s*[<\"]([^>\"]+)[>\"]', content)
            if includes:
                markdown_parts.append("## Includes")
                for inc in includes:
                    markdown_parts.append(f"- `{inc}`")
                markdown_parts.append("")

            # Extract functions
            functions = re.findall(r'(?:^|\n)(?:static\\s+)?(?:inline\\s+)?(?:void|int|char|float|double|bool|size_t|uint32_t|uint64_t|long|short)\\s+(\\w+)\\s*\\([^)]*\\)\\s*(?:const)?(?:\\s*noexcept)?(?:\\s*override)?(?:\\s*final)?\\s*\\{', content, re.MULTILINE)
            if functions:
                markdown_parts.append("## Functions")
                for f in functions[:20]:
                    markdown_parts.append(f"- `{f}()`")
                markdown_parts.append("")

            # Extract classes
            classes = re.findall(r'class\\s+(\\w+)', content)
            if classes:
                markdown_parts.append("## Classes")
                for c in classes:
                    markdown_parts.append(f"- `{c}`")
                markdown_parts.append("")

            # Extract macros
            macros = re.findall(r'#define\\s+(\\w+)', content)
            if macros:
                markdown_parts.append("## Macros")
                for m in macros[:20]:
                    markdown_parts.append(f"- `{m}`")
                markdown_parts.append("")

            # Extract namespaces
            namespaces = re.findall(r'namespace\\s+(\\w+)', content)
            if namespaces:
                markdown_parts.append("## Namespaces")
                for n in namespaces:
                    markdown_parts.append(f"- `{n}`")
                markdown_parts.append("")

        except Exception as e:
            logger.debug(f"Error reading C/C++ file: {e}")
            markdown_parts.append(f"[Error reading file: {e}]")

        return "\n".join(markdown_parts)

    def get_file_info(self, file_path: str) -> dict:
        try:
            with open(file_path, encoding='utf-8', errors='ignore') as f:
                content = f.read()
            functions = re.findall(r'\\w+\\s*\\([^)]*\\)\\s*\\{', content, re.MULTILINE)
            return {'lines': len(content.splitlines()), 'functions': len(functions)}
        except:
            return {'lines': 0, 'functions': 0}
