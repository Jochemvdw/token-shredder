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
from token_shredder.profiling import record_index, minify_json_text, profile_records, render_fields, example, map_kind, describe_map, clamp_levels, is_id_like

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
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            data = json.loads(content)

            level = options.detail_level
            minified = "```json\n" + minify_json_text(content.strip()) + "\n```"
            if level >= 4:
                # All the data, minified: lossless and usually much smaller
                # than pretty-printed JSON.
                return minified
            name = Path(file_path).name

            def render(lv: int) -> str:
                lines = [f"# JSON File: {name}", ""]
                lines.append(f"Top level: {self._type_name(data)}")
                # 1 = top-level keys only, 2 = nested keys, 3 = nested keys + example values
                self._schema(data, lines, indent=0, depth=1, max_depth=1 if lv == 1 else 3,
                             examples=lv >= 3, level=lv)
                lines.append("")
                lines.append("_Summary; use `--detail-level 4` for the data._")
                return "\n".join(lines)

            # Never longer than the minified data, never smaller than the level below.
            return clamp_levels(render, level, minified)

        except Exception as e:
            logger.debug(f"Error reading JSON: {e}")
            return f"[Error: {e}]"

    MAX_KEYS = 40

    def _schema(self, data, lines, indent, depth, max_depth, examples, level=3):
        pad = "  " * indent
        if isinstance(data, list):
            self._profile_list(data, lines, indent, level)
            return
        if not isinstance(data, dict):
            return
        kind = map_kind(data)
        if kind:
            if indent == 0:
                lines.append(f"- map of {len(data):,} entries")
                indent = 1
            self._map(data, kind, lines, indent, level)
            return
        for i, (key, value) in enumerate(data.items()):
            if i >= self.MAX_KEYS:
                lines.append(f"{pad}- ... {len(data) - i:,} more keys")
                break
            line = f"{pad}- `{key}`: {self._type_name(value)}"
            if examples and not isinstance(value, (dict, list)):
                line += f" = {self._example(value)}"
            lines.append(line)
            if isinstance(value, list) and any(isinstance(x, dict) for x in value):
                self._profile_list(value, lines, indent + 1, level)
            elif depth < max_depth and isinstance(value, (dict, list)):
                sub_level = level
                if key == "dependencies" and isinstance(data.get("packages"), dict) \
                        and "lockfileVersion" in data:
                    sub_level = min(level, 2)  # npm v2 lockfile: legacy copy of "packages"
                self._schema(value, lines, indent + 1, depth + 1, max_depth, examples, sub_level)

    @staticmethod
    def _map(data, kind, lines, indent, level):
        """A dict used as id -> record lookup: describe it like a list of records."""
        if level < 2:
            return
        pad = "  " * indent
        for ml in describe_map(data, kind, level):
            lines.append(pad + "  " + ml)

    @staticmethod
    def _profile_list(data, lines, indent, level):
        """Describe a list of objects with the streaming profiler."""
        objects = [x for x in data if isinstance(x, dict)]
        if not objects:
            return
        pad = "  " * indent
        profile = profile_records(objects)
        lines.append(f"{pad}- each item ({len(data):,} items):")
        for fl in render_fields(profile, level):
            lines.append(pad + "  " + fl)
        if level >= 3:
            for il in record_index(list(enumerate(data))):
                lines.append(pad + "  " + il)

    @staticmethod
    def _example(value) -> str:
        """A real value of this object (not one example of many): keep human text
        readable (up to 120 chars); cut URLs, ids and hashes short."""
        if isinstance(value, str) and not is_id_like(value):
            text = json.dumps(value, ensure_ascii=False)
            return text if len(text) <= 120 else text[:117] + '..."'
        return example(value)

    def _type_name(self, value) -> str:
        if isinstance(value, dict):
            if map_kind(value):
                return f"map({len(value):,} entries)"
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
            with open(file_path, encoding='utf-8', errors='replace') as f:
                data = json.load(f)
            return {
                'type': 'dict' if isinstance(data, dict) else 'list',
                'keys': len(data.keys()) if isinstance(data, dict) else 0,
                'items': len(data) if isinstance(data, list) else 0,
            }
        except:
            return {'type': 'unknown', 'keys': 0, 'items': 0}
