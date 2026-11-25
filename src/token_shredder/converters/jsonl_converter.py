"""
token_shredder - JSONL / NDJSON Converter
Profiles line-delimited JSON records (streaming).
"""
import json
from pathlib import Path
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.profiling import Profile, render_profile, clamp_levels
from token_shredder.utils.logger import setup_logger

logger = setup_logger(__name__)


class JSONLConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.jsonl', '.ndjson']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='jsonl',
            tables_count=0,
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        level = options.detail_level
        try:
            profile = Profile()
            bad = 0
            other = 0
            data_lines = []
            full_len = 0
            keep = level >= 4
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        bad += 1
                        continue
                    mini = json.dumps(rec, ensure_ascii=False, separators=(",", ":"))
                    full_len += len(mini) + 1
                    if keep:
                        data_lines.append(mini)
                    if isinstance(rec, dict):
                        if level < 4:
                            profile.add(rec)
                    else:
                        other += 1

            notes = []
            if bad:
                notes.append(f"{bad:,} line{'s' if bad != 1 else ''} could not be parsed")
            if other:
                notes.append(f"{other:,} line{'s' if other != 1 else ''} are not JSON objects")
            note_text = ("\n\n_" + "; ".join(notes) + "._") if notes else ""

            name = Path(file_path).name
            if level >= 4:
                return f"```jsonl\n" + "\n".join(data_lines) + "\n```" + note_text

            def render(lv: int) -> str:
                return (f"# JSONL File: {name}\n\n" + render_profile(profile, lv) + note_text
                        + "\n\n_Profile only; use `--detail-level 4` for the data._")

            # Never longer than the full data, never smaller than the level below.
            if full_len == 0:
                return render(level)
            return clamp_levels(render, level, self._full(file_path, note_text))
        except Exception as e:
            logger.debug(f"Error reading JSONL: {e}")
            return f"[Error: {e}]"

    def _full(self, file_path: str, note_text: str) -> str:
        lines = []
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    lines.append(json.dumps(json.loads(line), ensure_ascii=False, separators=(",", ":")))
                except ValueError:
                    pass
        return "```jsonl\n" + "\n".join(lines) + "\n```" + note_text

    def get_file_info(self, file_path: str) -> dict:
        try:
            with open(file_path, encoding='utf-8', errors='replace') as f:
                return {'rows': sum(1 for line in f if line.strip())}
        except Exception:
            return {'rows': 0}
