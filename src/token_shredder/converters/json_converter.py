"""
token_shredder - JSON Converter
Converts JSON files to markdown
"""
import json
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.utils.logger import setup_logger

logger = setup_logger(__name__)


class JSONConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.json']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='json',
            tables_count=self._count_tables(markdown),
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            data = json.loads(content)

            level = options.detail_level
            minified = "```json\n" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n```"
            if level >= 4:
                # All the data, minified: lossless and usually much smaller
                # than pretty-printed JSON.
                return minified

            lines = [f"# JSON File: {Path(file_path).name}", ""]
            lines.append(f"Top level: {self._type_name(data)}")
            # 1 = top-level keys only, 2 = nested keys, 3 = nested keys + example values
            max_depth = 1 if level == 1 else 3
            self._schema(data, lines, indent=0, depth=1, max_depth=max_depth, examples=level >= 3)
            lines.append("")
            lines.append("_Schema only; use `--detail-level 4` for the data._")
            schema = "\n".join(lines)
            # Never return a lossy schema that is longer than the full data.
            return minified if len(schema) >= len(minified) else schema

        except Exception as e:
            logger.error(f"Error reading JSON: {e}")
            return f"[Error: {e}]"

    def _schema(self, data, lines, indent, depth, max_depth, examples):
        pad = "  " * indent
        if isinstance(data, list):
            objects = [x for x in data if isinstance(x, dict)]
            if objects:
                # Union of keys across items, first example wins.
                merged = {}
                for item in objects:
                    for k, v in item.items():
                        merged.setdefault(k, v)
                lines.append(f"{pad}- each item ({len(data)} items):")
                self._schema(merged, lines, indent + 1, depth, max_depth, examples)
            return
        if not isinstance(data, dict):
            return
        for key, value in data.items():
            line = f"{pad}- `{key}`: {self._type_name(value)}"
            if examples and not isinstance(value, (dict, list)):
                line += f" = {self._example(value)}"
            lines.append(line)
            if depth < max_depth and isinstance(value, (dict, list)):
                self._schema(value, lines, indent + 1, depth + 1, max_depth, examples)

    @staticmethod
    def _example(value) -> str:
        text = json.dumps(value, ensure_ascii=False)
        return text if len(text) <= 28 else text[:25] + '..."'

    def _type_name(self, value) -> str:
        if isinstance(value, dict):
            return f"object({len(value)} keys)"
        elif isinstance(value, list):
            return f"array({len(value)} items)"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, bool):
            return "boolean"
        elif isinstance(value, (int, float)):
            return "number"
        elif value is None:
            return "null"
        return type(value).__name__

    def get_file_info(self, file_path: str) -> dict:
        try:
            with open(file_path) as f:
                data = json.load(f)
            return {
                'type': 'dict' if isinstance(data, dict) else 'list',
                'keys': len(data.keys()) if isinstance(data, dict) else 0,
                'items': len(data) if isinstance(data, list) else 0,
            }
        except:
            return {'type': 'unknown', 'keys': 0, 'items': 0}
