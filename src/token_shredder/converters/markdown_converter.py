"""
token_shredder - Markdown Converter
Cleans markdown files: badges, images, HTML and link URLs go at levels 1-3
"""
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.prose import markdown_level
from token_shredder.utils.logger import setup_logger

logger = setup_logger(__name__)


class MarkdownConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.md']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=file_path,
            format='md',
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            if options.detail_level >= 5:
                return content
            return markdown_level(content, options.detail_level)
        except Exception as e:
            logger.error(f"Error reading MD: {e}")
            return f"[Error reading MD: {e}]"

    def get_file_info(self, file_path: str) -> dict:
        try:
            with open(file_path, encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            return {'lines': len(lines), 'words': sum(len(l.split()) for l in lines)}
        except:
            return {'lines': 0, 'words': 0}
