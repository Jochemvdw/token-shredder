"""
token_shredder - TOML Converter
Converts TOML files to markdown
"""
import io
try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.profiling import clamp_levels
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
        try:
            with open(file_path, 'rb') as f:
                raw = f.read()
            text = raw.decode('utf-8', errors='replace')
            full = f"```toml\n{text.rstrip()}\n```\n"
            if options.detail_level >= 5:
                return text
            try:
                data = tomllib.load(io.BytesIO(raw))
            except UnicodeDecodeError:
                data = tomllib.loads(text)
        except Exception as e:
            logger.error(f"Error reading TOML: {e}")
            return f"[Error reading TOML: {e}]"

        name = Path(file_path).name

        def render(lv: int) -> str:
            head = f"# TOML Configuration: {name}\n\n## Structure\n"
            return head + "\n".join(self._structure(data, level=lv))

        # 1 = tables, 2 = + key names, 3 = + short values, 4 = + long values; never longer than the file
        return clamp_levels(render, min(options.detail_level, 4), full)

    @staticmethod
    def _short(value, limit: int = 40) -> str:
        text = repr(value) if not isinstance(value, str) else f'"{value}"'
        text = text.replace('\n', ' ')
        return text if len(text) <= limit else ''

    def _structure(self, data: dict, path: str = "", depth: int = 0, level: int = 3) -> list:
        lines = []
        indent = "  " * depth
        limit = 300 if level >= 4 else 40
        if level <= 2:
            # one line per table: its name and, from level 2, its keys
            scalars = [k for k, v in data.items() if not isinstance(v, dict)]
            if scalars or not path:
                keys = ", ".join(f"{k}[{len(data[k])}]" if isinstance(data[k], list) else k for k in scalars)
                if level == 2 and keys:
                    lines.append(f"{indent}- {'[' + path + ']' if path else '(top level)'}: {keys}")
                elif path:
                    lines.append(f"{indent}- [{path}]: {len(scalars)} {'setting' if len(scalars) == 1 else 'settings'}")
            for key, value in data.items():
                if isinstance(value, dict):
                    lines.extend(self._structure(value, f"{path}.{key}" if path else key, depth, level))
            return lines
        for key, value in data.items():
            if isinstance(value, dict):
                sub = f"{path}.{key}" if path else key
                nkeys = len(value)
                lines.append(f"{indent}- **[{sub}]**: {nkeys} {'setting' if nkeys == 1 else 'settings'}")
                lines.extend(self._structure(value, sub, depth + 1, level))
            elif isinstance(value, list) and value and all(isinstance(x, dict) for x in value):
                fields = list(dict.fromkeys(k for x in value for k in x))
                lines.append(f"{indent}- {key}: {len(value)} tables with {', '.join(fields)}")
                if level >= 4:
                    for x in value:
                        lines.append(f"{indent}  - " + ", ".join(f"{k}={self._short(v, limit) or type(v).__name__}"
                                                                 for k, v in x.items()))
            elif isinstance(value, list):
                shown = self._short(value, limit)
                lines.append(f"{indent}- {key}: {shown or f'list ({len(value)} items)'}")
            else:
                lines.append(f"{indent}- {key}: {self._short(value, limit) or type(value).__name__}")
        return lines

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
            with open(file_path, 'rb') as f:
                data = tomllib.load(f)
            return {'sections': len(data.keys()), 'keys': sum(len(v.keys()) if isinstance(v, dict) else 0 for v in data.values())}
        except:
            return {'sections': 0, 'keys': 0}
