"""
token_shredder - YAML Converter

Summarises YAML (Kubernetes manifests, CI workflows, OpenAPI, docker-compose,
multi-document files) at four detail levels:

1. top-level keys per document (documents are labelled by `kind` and name when present)
2. + nested key outline, lists of mappings merged
3. + values in compact YAML: short collections inline, long strings cut, long lists and
   many-entry maps described by the profiler
4. + all values, nothing cut (comments and formatting dropped)

A summary that is not smaller than the file is replaced by the file.
"""
import datetime
import json
import re
import yaml
from pathlib import Path
from typing import Optional

from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.profiling import (
    clamp_levels, map_kind, describe_map, profile_records, render_fields, MAP_MIN_RECORDS,
)
from token_shredder.utils.logger import setup_logger

logger = setup_logger(__name__)

MAX_NODES = 300_000     # guard against alias bombs ("billion laughs")
MAX_DOCS_SHOWN = 60
OUTLINE_DEPTH = 7
LONG_LIST = 25          # level 3: lists of mappings longer than this are profiled
FLOW_LEN = 100          # level 3: inline `{a: 1, b: 2}` form up to this many characters
STR_LEN = 120           # level 3: strings are cut to this many characters
MAX_LINES_L3 = 400
SCALARS = (str, int, float, bool, type(None), datetime.date, datetime.datetime)


class _TooBig(Exception):
    pass


class _Loader(yaml.SafeLoader):
    """SafeLoader that also accepts unknown tags (`!Ref`, `!include`) as plain data."""


def _unknown_tag(loader, suffix, node):
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node, deep=True)
    return loader.construct_mapping(node, deep=True)


_Loader.add_multi_constructor("", _unknown_tag)
# YAML 1.1 reads `on:` / `yes` / `no` as booleans, which turns a GitHub Actions `on:` key into
# `true`. Only true/false are booleans here, so keys and values keep their spelling.
_BOOL = "tag:yaml.org,2002:bool"
_Loader.yaml_implicit_resolvers = {
    ch: [(tag, rx) for tag, rx in resolvers if tag != _BOOL]
    for ch, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_Loader.add_implicit_resolver(_BOOL, re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"), list("tTfF"))


# --- text helpers -------------------------------------------------------------

def _is_scalar(v) -> bool:
    return isinstance(v, SCALARS)


def _plain(s: str) -> str:
    """A string as YAML would write it: bare when unambiguous, else JSON-quoted."""
    if s == "" or s != s.strip() or s.lower() in ("true", "false", "null", "yes", "no", "on", "off", "~"):
        return json.dumps(s, ensure_ascii=False)
    if s[0] in "[]{}&*!|>'\"%@`-?:,#" and not (s[0] == "-" and len(s) > 1 and s[1] not in " -"):
        return json.dumps(s, ensure_ascii=False)
    if ": " in s or " #" in s or s.endswith(":"):
        return json.dumps(s, ensure_ascii=False)
    try:
        float(s)
        return json.dumps(s)
    except ValueError:
        return s


def _scalar(v, full: bool) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    if isinstance(v, str):
        text = v.rstrip("\n")
        if "\n" in text and not full:
            lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
            joined = " ⏎ ".join(lines[:2])
            if len(joined) > STR_LEN:
                joined = joined[:STR_LEN - 1] + "…"
            more = len(lines) - 2
            return _plain(joined) + (f" …(+{more} lines)" if more > 0 else "")
        if not full and len(text) > STR_LEN:
            return _plain(text[:STR_LEN - 1] + "…") + f" ({len(text):,} chars)"
        return _plain(text)
    return str(v)


def _tick(r) -> None:
    r.nodes += 1
    if r.nodes > MAX_NODES:
        raise _TooBig()


# --- document labels ----------------------------------------------------------

def _label(doc) -> str:
    if isinstance(doc, dict):
        kind = doc.get("kind")
        if isinstance(kind, str):
            meta = doc.get("metadata")
            name = meta.get("name") if isinstance(meta, dict) else None
            text = kind + (f" `{name}`" if name else "")
            ver = doc.get("apiVersion")
            return text + (f" ({ver})" if isinstance(ver, str) else "")
        return f"mapping, {len(doc)} keys"
    if isinstance(doc, list):
        return f"list, {len(doc)} items"
    return "scalar"


def _kind_text(v) -> str:
    if isinstance(v, dict):
        return f"{{{len(v)}}}"
    if isinstance(v, list):
        return f"[{len(v)}]"
    return ""


# --- level 1 and 2: key outline -------------------------------------------------

def _merge(values: list):
    """One representative for several values: dicts union their keys, lists their items."""
    dicts = [v for v in values if isinstance(v, dict)]
    lists = [v for v in values if isinstance(v, list)]
    if dicts and len(dicts) >= len(lists):
        out = {}
        for d in dicts[:200]:
            for k, v in d.items():
                out.setdefault(k, []).append(v)
        return {k: _merge(vs) for k, vs in out.items()}
    if lists:
        return [_merge([x for lst in lists[:200] for x in lst[:200]])] if any(lists) else []
    return None


def _outline(v, depth: int, lines: list, r) -> None:
    pad = "  " * depth
    if depth >= OUTLINE_DEPTH:
        lines.append(f"{pad}…")
        return
    if isinstance(v, dict):
        if map_kind(v) == "records" and len(v) >= MAP_MIN_RECORDS:
            keys = list(v)
            shown = ", ".join(str(k) for k in keys[:6]) + (f", … {len(keys) - 6} more" if len(keys) > 6 else "")
            lines.append(f"{pad}(map of {len(v):,} entries: {shown}) each:")
            _outline(_merge(list(v.values())), depth + 1, lines, r)
            return
        for k, val in list(v.items())[:80]:
            _tick(r)
            n = len(val) if isinstance(val, (dict, list)) else None
            mark = f" [{n}]" if isinstance(val, list) else ""
            lines.append(f"{pad}{k}{mark}")
            if isinstance(val, dict):
                _outline(val, depth + 1, lines, r)
            elif isinstance(val, list) and val and any(isinstance(x, (dict, list)) for x in val):
                merged = _merge(val)
                _outline(merged[0] if isinstance(merged, list) and merged else merged, depth + 1, lines, r)
        if len(v) > 80:
            lines.append(f"{pad}… {len(v) - 80} more keys")
    elif isinstance(v, list) and v:
        merged = _merge(v)
        if isinstance(merged, list) and merged:
            merged = merged[0]
        _outline(merged, depth, lines, r)


class _R:
    def __init__(self):
        self.nodes = 0


def _outline_docs(docs: list, level: int, name: str) -> str:
    r = _R()
    head = f"# YAML: {name}" + (f" ({len(docs)} documents)" if len(docs) > 1 else "")
    lines = [head]
    shown = docs[:MAX_DOCS_SHOWN]
    for i, doc in enumerate(shown, 1):
        prefix = f"Document {i}: {_label(doc)}" if len(docs) > 1 else ""
        if level == 1:
            if isinstance(doc, dict):
                keys = ", ".join(f"{k}{_kind_text(v)}" for k, v in list(doc.items())[:60])
                lines.append((f"{prefix}. Keys: " if prefix else "Keys: ") + keys)
            else:
                lines.append(f"{prefix}" if prefix else f"Top level: {_label(doc)}")
        else:
            if prefix:
                lines.append(prefix)
            elif not isinstance(doc, dict):
                lines.append(f"Top level: {_label(doc)}")
            _outline(doc, 0, lines, r)
    if len(docs) > len(shown):
        lines.append(f"… {len(docs) - len(shown)} more documents")
    return "\n".join(lines)


# --- level 3 and 4: compact YAML ----------------------------------------------------

class _Writer:
    def __init__(self, full: bool):
        self.full = full
        self.nodes = 0
        self.lines = []
        self.omitted = 0

    def add(self, line: str) -> None:
        if not self.full and len(self.lines) >= MAX_LINES_L3:
            self.omitted += 1
        else:
            self.lines.append(line)


def _flow(v, w: _Writer, limit: int) -> Optional[str]:
    """Inline `{a: 1, b: [x, y]}` text, or None when it does not fit or has multi-line strings."""
    _tick(w)
    if _is_scalar(v):
        if isinstance(v, str) and "\n" in v.strip("\n"):
            return None
        return _scalar(v, w.full)
    if isinstance(v, list):
        if len(v) > 20 and not w.full:
            return None
        parts = []
        for x in v:
            f = _flow(x, w, limit)
            if f is None:
                return None
            parts.append(f)
        text = "[" + ", ".join(parts) + "]"
    elif isinstance(v, dict):
        parts = []
        for k, x in v.items():
            f = _flow(x, w, limit)
            if f is None:
                return None
            parts.append(f"{k}: {f}")
        text = "{" + ", ".join(parts) + "}"
    else:
        return None
    return text if (w.full or len(text) <= limit) else None


def _emit_value(key_prefix: str, v, depth: int, w: _Writer) -> None:
    """Lines for `key: value` (key_prefix is 'key:' or '-')."""
    pad = "  " * depth
    _tick(w)
    if _is_scalar(v):
        if isinstance(v, str) and "\n" in v.strip("\n") and w.full:
            w.add(f"{pad}{key_prefix} |")
            for ln in v.rstrip("\n").split("\n"):
                w.add(f"{pad}  {ln}" if ln else "")
            return
        w.add(f"{pad}{key_prefix} {_scalar(v, w.full)}")
        return
    if not v:
        w.add(f"{pad}{key_prefix} {'{}' if isinstance(v, dict) else '[]'}")
        return
    inline = _flow(v, w, FLOW_LEN)
    if inline is not None and (isinstance(v, list) or len(v) <= 6):
        w.add(f"{pad}{key_prefix} {inline}")
        return
    if isinstance(v, dict):
        kind = map_kind(v) if not w.full else None
        if kind:
            w.add(f"{pad}{key_prefix} # map of {len(v):,} entries")
            for ml in describe_map(v, kind, 3):
                w.add(f"{pad}  # {ml}")
            return
        w.add(f"{pad}{key_prefix}")
        _emit_map(v, depth + 1, w)
        return
    # list
    w.add(f"{pad}{key_prefix}")
    _emit_list(v, depth + 1, w)


def _emit_map(d: dict, depth: int, w: _Writer) -> None:
    for k, v in d.items():
        _emit_value(f"{_plain(str(k))}:", v, depth, w)


def _emit_list(items: list, depth: int, w: _Writer) -> None:
    pad = "  " * depth
    shown = items
    dict_items = [x for x in items if isinstance(x, dict)]
    if not w.full and len(items) > LONG_LIST and len(dict_items) * 10 >= len(items) * 9:
        w.add(f"{pad}# {len(items):,} items; each:")
        for fl in render_fields(profile_records(dict_items), 3):
            w.add(f"{pad}# {fl}")
        shown = items[:2]
    elif not w.full and len(items) > 3 * LONG_LIST:
        shown = items[:LONG_LIST]
    for x in shown:
        if isinstance(x, dict) and x:
            sub = _Writer(w.full)
            sub.nodes = w.nodes
            inline = _flow(x, sub, FLOW_LEN)
            if inline is not None:
                w.add(f"{pad}- {inline}")
                continue
            _emit_map(x, depth + 1, sub)
            w.nodes = sub.nodes
            if sub.lines:
                first = sub.lines[0]
                w.add(f"{pad}- {first[len(pad) + 2:]}")
                for ln in sub.lines[1:]:
                    w.add(ln)
        else:
            _emit_value("-", x, depth, w)
    if len(shown) < len(items):
        w.add(f"{pad}# … {len(items) - len(shown):,} more")


def _values_text(docs: list, level: int, name: str) -> str:
    w = _Writer(level >= 4)
    head = f"# YAML: {name}" + (f" ({len(docs)} documents)" if len(docs) > 1 else "")
    for i, doc in enumerate(docs[:MAX_DOCS_SHOWN] if not w.full else docs, 1):
        if i > 1:
            w.add("---")
        if len(docs) > 1:
            w.add(f"# {i}: {_label(doc)}")
        if isinstance(doc, dict):
            _emit_map(doc, 0, w)
        elif isinstance(doc, list):
            _emit_list(doc, 0, w)
        else:
            w.add(_scalar(doc, w.full))
    if len(docs) > MAX_DOCS_SHOWN and not w.full:
        w.add(f"# … {len(docs) - MAX_DOCS_SHOWN} more documents")
    if w.omitted:
        w.lines.append(f"# … {w.omitted:,} more lines (use `--detail-level 4` for everything)")
    return head + "\n```yaml\n" + "\n".join(w.lines) + "\n```\n"


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
        try:
            raw = Path(file_path).read_text(encoding='utf-8', errors='replace')
        except Exception as e:
            logger.error(f"Error reading YAML: {e}")
            return f"[Error reading YAML: {e}]"
        full = f"```yaml\n{raw.rstrip()}\n```\n"
        try:
            docs = [d for d in yaml.load_all(raw, Loader=_Loader) if d is not None]
        except yaml.YAMLError as e:
            logger.warning(f"YAML does not parse ({e}); returning it as is")
            return full
        if not docs:
            return "_(Empty file)_" if not raw.strip() else full
        name = Path(file_path).name
        level = min(options.detail_level, 4)

        def render(lv: int) -> str:
            if lv <= 2:
                return _outline_docs(docs, lv, name)
            return _values_text(docs, lv, name)

        try:
            return clamp_levels(render, level, full)
        except (_TooBig, RecursionError):
            logger.warning("YAML too deeply nested or aliased to summarise; returning it as is")
            return full

    def get_file_info(self, file_path: str) -> dict:
        try:
            with open(file_path, encoding='utf-8', errors='replace') as f:
                data = yaml.load(f, Loader=_Loader)
            return {'type': type(data).__name__, 'keys': len(data.keys()) if isinstance(data, dict) else 0}
        except Exception:
            return {'type': 'unknown', 'keys': 0}
