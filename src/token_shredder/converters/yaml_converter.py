"""
token_shredder - YAML Converter
Converts YAML files to markdown
"""
import yaml
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.utils.logger import setup_logger

logger = setup_logger(__name__)


class YAMLConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.yaml', '.yml']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='yaml',
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        markdown_parts = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            markdown_parts.append(f"# YAML Document: {file_path}")
            markdown_parts.append("")

            if data is None:
                markdown_parts.append("_(Empty file)_")
                return "\n".join(markdown_parts)

            markdown_parts.append(self._data_to_markdown(data, "Content"))

        except Exception as e:
            logger.error(f"Error reading YAML: {e}")
            markdown_parts.append(f"[Error reading YAML: {e}]")

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
            with open(file_path) as f:
                data = yaml.safe_load(f)
            return {'type': type(data).__name__, 'keys': len(data.keys()) if isinstance(data, dict) else 0}
        except:
            return {'type': 'unknown', 'keys': 0}
