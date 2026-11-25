"""
token_shredder - TOML Converter
Converts TOML files to markdown
"""
import pytoml
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.utils.logger import setup_logger

logger = setup_logger(__name__)


class TOMLConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.toml']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='toml',
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
                data = pytoml.load(f)

            markdown_parts.append(f"# TOML Configuration: {Path(file_path).name}")
            markdown_parts.append("")
            markdown_parts.append("## Structure")
            for section, values in data.items():
                if isinstance(values, dict):
                    markdown_parts.append(f"- **[{section}]**: {len(values)} settings")
                else:
                    markdown_parts.append(f"- **{section}**: {type(values).__name__}")

        except Exception as e:
            logger.error(f"Error reading TOML: {e}")
            markdown_parts.append(f"[Error reading TOML: {e}]")

        return "\n".join(markdown_parts)

    def _data_to_markdown(self, data, prefix="") -> str:
        md = []
        for key, value in data.items():
            md.append(f"## {key}")
            if isinstance(value, dict):
                md.append("")
                for k, v in value.items():
                    md.append(f"### {k}")
                    md.append(f"{v}")
                    md.append("")
            elif isinstance(value, list):
                md.append(f"- Items: {len(value)}")
                for i, item in enumerate(value[:10]):
                    md.append(f"  - {i+1}: {item}")
                if len(value) > 10:
                    md.append(f"  ... ({len(value) - 10} more)")
                md.append("")
            else:
                md.append(f"{value}")
                md.append("")
        return "\n".join(md)

    def get_file_info(self, file_path: str) -> dict:
        try:
            with open(file_path) as f:
                data = pytoml.load(f)
            return {'sections': len(data.keys()), 'keys': sum(len(v.keys()) if isinstance(v, dict) else 0 for v in data.values())}
        except:
            return {'sections': 0, 'keys': 0}
