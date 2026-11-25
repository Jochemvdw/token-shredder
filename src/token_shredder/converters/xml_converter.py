"""
token_shredder - XML Converter

Summarises an XML file instead of dumping every element:

1. element outline: tag names, with counts for repeated elements
2. + attribute names and a profile of repeated elements (RSS items, Maven dependencies)
3. + values: short text inline, long text cut, repeated records one line each
4. all values, no cut-offs (still more compact than the XML itself)

A summary that is not smaller than the file is replaced by the file.
"""
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Optional

from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.profiling import clamp_levels, profile_records, render_fields, infer_cell
from token_shredder.utils.logger import setup_logger

logger = setup_logger(__name__)

REPEAT_MIN = 3          # same tag this many times under one parent = a list of records
MAX_ITEMS_L3 = 40       # records shown per repeated group at level 3
ITEM_CHARS_L3 = 6000    # level 3: stop listing a group's records after about this many characters
MAX_LINES_L3 = 260      # level 3 stops after this many lines
TEXT_LEN = 100          # level 3: text values are cut to this many characters
ATTR_LEN = 60           # level 3: attribute values
FIELD_LEN = 160         # level 3: a record field longer than this on average is left out of the record lines
OUTLINE_DEPTH = {1: 5, 2: 8}
MAX_TAGS = 40           # outline: distinct child tags listed per element


class Node:
    __slots__ = ("tag", "attrs", "text", "children")

    def __init__(self, tag, attrs):
        self.tag = tag
        self.attrs = attrs
        self.text = ""
        self.children = []


def parse_tree(file_path: str) -> Node:
    """Element tree with readable names (`prefix:local`) and collapsed whitespace."""
    prefixes = {}  # namespace uri -> prefix

    def name(qn: str) -> str:
        if qn.startswith("{"):
            uri, local = qn[1:].split("}", 1)
            prefix = prefixes.get(uri, "")
            return f"{prefix}:{local}" if prefix else local
        return qn

    root = None
    stack = []
    for event, obj in ET.iterparse(file_path, events=("start-ns", "start", "end")):
        if event == "start-ns":
            prefix, uri = obj
            prefixes.setdefault(uri, prefix)
        elif event == "start":
            node = Node(name(obj.tag), {name(k): v for k, v in obj.attrib.items()})
            if stack:
                stack[-1].children.append(node)
            else:
                root = node
            stack.append(node)
        else:
            node = stack.pop()
            node.text = " ".join((obj.text or "").split())
            obj.clear()
    return root


def _cut(text: str, limit: int) -> str:
    return text if len(text) <= limit else f"{text[:limit - 1]}…({len(text):,} chars)"


# --- outline (levels 1-2) ---------------------------------------------------

class Shape:
    """All elements with the same tag under the same path, merged."""
    __slots__ = ("count", "attrs", "children")

    def __init__(self):
        self.count = 0
        self.attrs = Counter()
        self.children = {}

    def add(self, node: Node) -> None:
        self.count += 1
        self.attrs.update(node.attrs.keys())
        for c in node.children:
            self.children.setdefault(c.tag, Shape()).add(c)


def _outline(tag: str, shape: Shape, depth: int, limit: int, attrs: bool, lines: list) -> None:
    pad = "  " * depth
    text = f"{pad}- {tag}"
    if shape.count > 1:
        text += f" ×{shape.count:,}"
    if attrs and shape.attrs:
        text += " [" + ", ".join(f"@{a}" if c == shape.count else f"@{a}?" for a, c in shape.attrs.items()) + "]"
    lines.append(text)
    if not shape.children:
        return
    if depth + 1 >= limit:
        lines.append(f"{pad}  - ... {len(shape.children)} child tags not shown")
        return
    leaves = [(t, s) for t, s in shape.children.items() if not s.children and not (attrs and s.attrs)]
    branches = [(t, s) for t, s in shape.children.items() if s.children or (attrs and s.attrs)]
    if leaves:
        shown = [t for t, _ in leaves[:MAX_TAGS]]
        more = len(leaves) - len(shown)
        lines.append(f"{pad}  - " + ", ".join(shown) + (f", … {more} more" if more else ""))
    for t, s in branches[:MAX_TAGS]:
        _outline(t, s, depth + 1, limit, attrs, lines)
    if len(branches) > MAX_TAGS:
        lines.append(f"{pad}  - ... {len(branches) - MAX_TAGS} more child tags")


def _groups(node: Node, path: str, out: dict) -> None:
    """Repeated sibling groups: path -> [nodes] (summed over all parents)."""
    counts = Counter(c.tag for c in node.children)
    for c in node.children:
        p = f"{path}/{c.tag}"
        if counts[c.tag] >= REPEAT_MIN:
            out.setdefault(p, []).append(c)
        _groups(c, p, out)


def _record(node: Node) -> dict:
    """Fields of a record element: attributes and simple children (typed like CSV cells)."""
    rec = {}
    for k, v in node.attrs.items():
        rec[k] = v
    seen = Counter(c.tag for c in node.children)
    for c in node.children:
        if c.children:
            continue
        if c.attrs:
            for k, v in c.attrs.items():
                rec[f"{c.tag}.{k}"] = v
        if c.text:
            val = c.text
            if seen[c.tag] > 1 and c.tag in rec:
                rec[c.tag] = f"{rec[c.tag]}, {val}"
            else:
                rec[c.tag] = val
    if node.text and not node.children:
        rec["#text"] = node.text
    return rec


def _outline_text(root: Node, level: int, name: str) -> str:
    shape = Shape()
    shape.add(root)
    lines = [f"# XML: {name}", "(×N = occurrences; comma lists are childless elements"
             + ("; [@x] = attributes, ? = not always present" if level >= 2 else "") + ")", ""]
    _outline(root.tag, shape, 0, OUTLINE_DEPTH[level], level >= 2, lines)
    if level >= 2:
        groups = {}
        _groups(root, root.tag, groups)
        big = sorted(groups.items(), key=lambda kv: -len(kv[1]) * len(kv[1][0].children or [0]))[:5]
        for path, nodes in big:
            recs = [_record(n) for n in nodes]
            if not any(recs):
                continue
            profile = profile_records({k: infer_cell(v) for k, v in r.items()} for r in recs)
            lines += ["", f"Repeated `{path}` ×{len(nodes):,}:"] + render_fields(profile, 2)
    return "\n".join(lines)


# --- values (levels 3-4) ----------------------------------------------------

class _Writer:
    def __init__(self, level: int):
        self.full = level >= 4
        self.lines = []
        self.omitted = 0

    def add(self, pad: str, text: str) -> None:
        if not self.full and len(self.lines) >= MAX_LINES_L3:
            self.omitted += 1
            return
        self.lines.append(pad + text)

    def text(self, value: str, limit: int) -> str:
        return value if self.full else _cut(value, limit)

    def attrs(self, node: Node) -> str:
        if not node.attrs:
            return ""
        return " {" + ", ".join(f"{k}={self.text(v, ATTR_LEN)}" for k, v in node.attrs.items()) + "}"


def _is_simple(node: Node, w: _Writer) -> bool:
    """A few childless, attribute-less children with short text: one line."""
    kids = node.children
    if not kids or len(kids) > 6 or node.attrs or node.text:
        return False
    tags = Counter(c.tag for c in kids)
    if any(n > 1 for n in tags.values()):
        return False
    return all(not c.children and not c.attrs and c.text and len(c.text) <= 40 for c in kids)


def _write_node(node: Node, depth: int, w: _Writer) -> None:
    pad = "  " * depth
    head = f"{pad}- {node.tag}{w.attrs(node)}"
    if not node.children:
        w.add("", head + (f": {w.text(node.text, TEXT_LEN)}" if node.text else ""))
        return
    if _is_simple(node, w):
        w.add("", head + ": " + ", ".join(f"{c.tag}={c.text}" for c in node.children))
        return
    w.add("", head + (f": {w.text(node.text, TEXT_LEN)}" if node.text else ""))
    _write_children(node, depth + 1, w)


def _write_children(node: Node, depth: int, w: _Writer) -> None:
    counts = Counter(c.tag for c in node.children)
    done = set()
    for c in node.children:
        if counts[c.tag] >= REPEAT_MIN:
            if c.tag not in done:
                done.add(c.tag)
                _write_group([x for x in node.children if x.tag == c.tag], depth, w)
        else:
            _write_node(c, depth, w)


def _write_group(nodes: list, depth: int, w: _Writer) -> None:
    pad = "  " * depth
    tag = nodes[0].tag
    n = len(nodes)
    if all(not x.children and not x.attrs for x in nodes):  # <module>a</module> x N
        vals = [w.text(x.text, 40) for x in nodes if x.text]
        cap = len(vals) if w.full else 30
        more = f", … {len(vals) - cap} more" if len(vals) > cap else ""
        w.add("", f"{pad}- {tag} ×{n:,}: " + ", ".join(vals[:cap]) + more)
        return
    recs = [_record(x) for x in nodes]
    fields = []
    for r in recs:
        for k in r:
            if k not in fields:
                fields.append(k)
    # fields identical in every record are stated once; long fields are left out (level 3)
    const = {k: recs[0][k] for k in fields if all(k in r and r[k] == recs[0][k] for r in recs)}
    # long prose (descriptions) is left out; URLs and other space-free values stay
    long = [k for k in fields if k not in const and not w.full
            and sum(len(str(r.get(k, ""))) for r in recs) > (FIELD_LEN if n < 10 else 80) * len(recs)
            and sum(" " in str(r.get(k, "")) for r in recs) * 2 > len(recs)]
    same = {}
    for i, k in enumerate(fields):
        for j in fields[:i]:
            if j not in same and k not in const and j not in const and k not in long and j not in long and all(
                    r.get(k) == r.get(j) for r in recs if k in r) and any(k in r for r in recs):
                same[k] = j
                break
    shown_all = [k for k in fields if k not in const and k not in long and k not in same]
    # fields present in nearly every record are positional; rare ones are named per record
    shown = [k for k in shown_all if sum(k in r for r in recs) * 10 >= n * 9] or shown_all[:1]
    extra = [k for k in shown_all if k not in shown]
    nested = sorted({c.tag for x in nodes for c in x.children if c.children})
    sep = ":" if all((" " not in str(r.get(k, "")) and ":" not in str(r.get(k, "")))
                     for r in recs for k in shown) else " | "
    head = f"{pad}- {tag} ×{n:,}"
    if shown:
        head += f" ({sep.join(shown)}" + (f"; optional: {', '.join(extra)}" if extra else "") + ")"
    if const:
        head += ", all " + ", ".join(f"{k}={_cell(v, w)}" for k, v in const.items())
    notes = []
    if long:
        notes.append("not shown: " + ", ".join(long))
    if same:
        notes.append(", ".join(f"{k}={j}" for k, j in same.items()) + " (same value)")
    if nested:
        notes.append("+ nested " + ", ".join(nested))
    if notes:
        head += " [" + "; ".join(notes) + "]"
    w.add("", head + (":" if shown else ""))
    if not shown:
        return
    used = 0
    for i, r in enumerate(recs):
        line = sep.join(_cell(r.get(k, ""), w, 120) for k in shown).rstrip(": |")
        named = [f"{k}={_cell(r[k], w, 60)}" for k in extra if k in r]
        if named:
            line += " (" + ", ".join(named) + ")"
        used += len(line)
        if not w.full and i >= 10 and (i >= MAX_ITEMS_L3 or used > ITEM_CHARS_L3):
            w.add("", f"{pad}  - ... {n - i:,} more")
            break
        w.add("", f"{pad}  - " + line)


def _cell(value, w: _Writer, limit: int = TEXT_LEN) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    text = value if isinstance(value, str) else ("" if value is None else str(value))
    return w.text(text, limit)


def _values_text(root: Node, level: int, name: str) -> str:
    w = _Writer(level)
    w.lines.append(f"# XML: {name}")
    _write_node(root, 0, w)
    if w.omitted:
        w.lines.append(f"... {w.omitted:,} more lines (use `--detail-level 4` for everything)")
    return "\n".join(w.lines)


class XMLConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.xml']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format='xml',
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        try:
            raw = Path(file_path).read_text(encoding='utf-8', errors='replace')
        except Exception as e:
            logger.debug(f"Error reading XML: {e}")
            return f"[Error reading XML: {e}]"
        full = f"```xml\n{raw.rstrip()}\n```\n"
        try:
            root = parse_tree(file_path)
        except Exception as e:
            logger.warning(f"XML does not parse ({e}); returning it as is")
            return full
        if root is None:
            return full
        name = Path(file_path).name
        level = min(options.detail_level, 4)

        def render(lv: int) -> str:
            return _outline_text(root, lv, name) if lv <= 2 else _values_text(root, lv, name)

        return clamp_levels(render, level, full)

    def get_file_info(self, file_path: str) -> dict:
        try:
            tree = ET.parse(file_path)
            return {'root': tree.getroot().tag, 'elements': len(list(tree.getroot().iter()))}
        except Exception:
            return {'root': 'unknown', 'elements': 0}
