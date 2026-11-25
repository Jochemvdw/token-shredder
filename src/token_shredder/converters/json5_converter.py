"""
token_shredder - JSON5 Converter
Converts JSON5 files to markdown
"""
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.utils.logger import setup_logger
import json5

logger = setup_logger(__name__)


class JSON5Converter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.json5']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='json5',
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        markdown_parts = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                data = json5.load(f)

            markdown_parts.append(f"# JSON5: {file_path}")
            markdown_parts.append("")
            markdown_parts.append(self._data_to_markdown(data))

        except Exception as e:
            logger.debug(f"Error reading JSON5: {e}")
            markdown_parts.append(f"[Error reading JSON5: {e}]")

        return "\n".join(markdown_parts)

    def _data_to_markdown(self, data, key="") -> str:
        md = []
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, (dict, list)):
                    md.append(f"## {k}")
                    md.append("")
                    md.append(self._data_to_markdown(v, k))
                    md.append("")
                else:
                    md.append(f"### {k}")
                    md.append(f"{v}")
                    md.append("")
        elif isinstance(data, list):
            md.append(f"- Items: {len(data)}")
            if data and isinstance(data[0], dict):
                md.append("")
                for i, item in enumerate(data[:20]):
                    md.append(f"#### Item {i+1}")
                    for k, v in item.items():
                        md.append(f"- {k}: {v}")
                    md.append("")
                if len(data) > 20:
                    md.append(f"... ({len(data) - 20} more items)")
                    md.append("")
        return "\n".join(md)

    def get_file_info(self, file_path: str) -> dict:
        try:
            with open(file_path, encoding='utf-8', errors='replace') as f:
                data = json5.load(f)
            return {'type': type(data).__name__, 'size': str(len(str(data)))}
        except:
            return {'type': 'unknown', 'size': 0}
