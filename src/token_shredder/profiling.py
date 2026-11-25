"""
token_shredder - streaming data profiler

Summarises the shape of a data file (a list of records) in a few lines per
field. Memory stays bounded however many rows go through: each field keeps
counters, a min/max, up to 3 examples and a distinct-value set that stops
growing at MAX_DISTINCT.
"""
import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Iterable, Optional

MAX_DISTINCT = 50       # stop tracking distinct values of a field after this many
ENUM_MAX = 10           # report an enum when there are at most this many values
ENUM_MIN_ROWS = 20      # ... and the field has this many values (or values repeat)
MAX_FIELDS = 500        # ignore new field names beyond this (maps used as objects)
EXAMPLE_LEN = 28
KEY_LEN = 64            # distinct-set keys are truncated to this many characters
MAX_EXAMPLES = 3
MAX_SUBFIELDS = 12      # a nested object with more distinct keys than this is a map, not flattened
MAP_MIN_RECORDS = 8     # dict of records: at least this many entries to count as a map
MAP_MIN_SCALARS = 40    # dict of scalars: at least this many entries to count as a map
MAP_KEYS_LISTED = 60    # list every key of a map of records up to this many, else a few examples
MAP_SCALAR_KEYS_LISTED = 150  # same for a map of scalars (dependencies, scripts: the names are the content)

_ID_LIKE = re.compile(r'^([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
                      r'|[0-9a-fA-F]{16,}|[A-Za-z][A-Za-z0-9+.-]*://\S+)$')
_ISO_DATE = re.compile(r'^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?)?$')


def example(value) -> str:
    """JSON text of a value, cut to 28 characters."""
    text = json.dumps(value, ensure_ascii=False)
    return text if len(text) <= EXAMPLE_LEN else text[:EXAMPLE_LEN - 3] + '..."'


def is_id_like(text: str) -> bool:
    """URLs, UUIDs, hashes and other long tokens without spaces: one example says it all."""
    if _ID_LIKE.match(text):
        return True
    return len(text) >= 20 and not any(c.isspace() for c in text)


def json_type(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, (list, tuple)):
        return "array"
    return "string"


def unique_headers(cells) -> list:
    """Column names that are non-empty and unique (blank -> col_N, dupes -> name_2)."""
    seen = Counter()
    out = []
    for i, c in enumerate(cells, 1):
        name = str(c).strip() if c is not None else ""
        name = name or f"col_{i}"
        seen[name] += 1
        out.append(name if seen[name] == 1 else f"{name}_{seen[name]}")
    return out


_INT = re.compile(r'-?(0|[1-9]\d*)')
_FLOAT = re.compile(r'-?(0|[1-9]\d*)\.\d+')


def infer_cell(text: str):
    """Typed value for a text cell: '' -> None, numbers -> int/float, true/false -> bool."""
    if text == "":
        return None
    c = text[0]
    if c.isdigit() or c == "-":
        if _INT.fullmatch(text):
            return int(text)
        if _FLOAT.fullmatch(text):
            return float(text)
    elif text in ("true", "false", "True", "False"):
        return text in ("true", "True")
    return text


@dataclass
class FieldStats:
    n: int = 0
    types: Counter = field(default_factory=Counter)
    num_min: Optional[float] = None
    num_max: Optional[float] = None
    all_int: bool = True
    len_min: Optional[int] = None
    len_max: Optional[int] = None
    str_min: Optional[str] = None
    str_max: Optional[str] = None
    dates: int = 0
    examples: list = field(default_factory=list)
    distinct: Counter = field(default_factory=Counter)
    overflow: bool = False
    single_example: bool = False

    def add(self, value) -> None:
        self.n += 1
        t = json_type(value)
        self.types[t] += 1
        if t in ("null", "object", "array"):
            return
        if t == "number":
            if isinstance(value, float) and not math.isfinite(value):
                key = str(value)
            else:
                if self.num_min is None or value < self.num_min:
                    self.num_min = value
                if self.num_max is None or value > self.num_max:
                    self.num_max = value
                if not isinstance(value, int):
                    self.all_int = False
                key = value
        elif t == "string":
            ln = len(value)
            self.len_min = ln if self.len_min is None else min(self.len_min, ln)
            self.len_max = ln if self.len_max is None else max(self.len_max, ln)
            if _ISO_DATE.match(value):
                self.dates += 1
                if self.str_min is None or value < self.str_min:
                    self.str_min = value
                if self.str_max is None or value > self.str_max:
                    self.str_max = value
            key = value[:KEY_LEN]
        else:
            key = value
        if t == "string" and len(self.examples) < MAX_EXAMPLES and not self.single_example:
            ex = example(value)
            if not self.examples and (is_id_like(value) or ex.endswith('..."')):
                self.single_example = True   # URLs, ids, long text: one example is enough
            if ex not in self.examples:
                self.examples.append(ex)
        if not self.overflow:
            dkey = ("b", key) if t == "boolean" else key
            if dkey in self.distinct or len(self.distinct) < MAX_DISTINCT:
                self.distinct[dkey] += 1
            else:
                self.overflow = True
                self.distinct.clear()

    @property
    def value_count(self) -> int:
        return sum(c for t, c in self.types.items() if t not in ("null",))

    def enum(self):
        """[(value, count)] by frequency when this looks like an enum, else None."""
        if self.overflow or not self.distinct:
            return None
        k = len(self.distinct)
        total = sum(self.distinct.values())
        if k <= ENUM_MAX and (total >= ENUM_MIN_ROWS or total > k):
            return self.distinct.most_common()
        return None


@dataclass
class Profile:
    rows: int = 0
    truncated: bool = False
    fields: dict = field(default_factory=dict)
    skipped_fields: int = 0
    sub_counts: dict = field(default_factory=dict)   # parent -> flattened sub-field names
    map_fields: set = field(default_factory=set)     # parents whose keys vary per record

    def _stats(self, name):
        st = self.fields.get(name)
        if st is None:
            if len(self.fields) >= MAX_FIELDS:
                self.skipped_fields += 1
                return None
            st = self.fields[name] = FieldStats()
        return st

    def add(self, record: dict) -> None:
        self.rows += 1
        for k, v in record.items():
            k = str(k)
            st = self._stats(k)
            if st is not None:
                st.add(v)
            if isinstance(v, dict) and k not in self.map_fields:
                if len(v) > MAX_SUBFIELDS:
                    self._drop_subfields(k)
                    continue
                for k2, v2 in v.items():
                    name = f"{k}.{k2}"
                    st2 = self._stats(name)
                    if st2 is not None:
                        st2.add(v2)
                        subs = self.sub_counts.setdefault(k, set())
                        subs.add(name)
                        if len(subs) > MAX_SUBFIELDS:  # keys vary per record: it is a map
                            self._drop_subfields(k)
                            break

    def _drop_subfields(self, k: str) -> None:
        self.map_fields.add(k)
        for name in self.sub_counts.pop(k, ()):
            self.fields.pop(name, None)


def profile_records(records: Iterable[dict], max_rows: Optional[int] = None) -> Profile:
    p = Profile()
    for rec in records:
        if max_rows is not None and p.rows >= max_rows:
            p.truncated = True
            break
        if isinstance(rec, dict):
            p.add(rec)
    return p


def _num(v) -> str:
    if isinstance(v, int):
        return str(v)
    if v == int(v) and abs(v) < 1e15:
        return str(int(v))
    return f"{v:.6g}"


def _pct(c, total) -> str:
    p = c * 100 / total if total else 0
    return "<1%" if 0 < p < 1 else f"{round(p)}%"


def _enum_text(key, count, total) -> str:
    if isinstance(key, tuple):  # boolean marker
        key = "true" if key[1] else "false"
    text = str(key) if not isinstance(key, str) else key
    if len(text) > EXAMPLE_LEN:
        text = text[:EXAMPLE_LEN - 1] + "…"
    return f"{text} ({_pct(count, total)})"


def _example_text(st: FieldStats) -> str:
    return (", e.g. " + ", ".join(st.examples)) if st.examples else ""


def render_field(name: str, st: FieldStats, rows: int, level: int) -> str:
    types = [t for t, _ in st.types.most_common() if t != "null"]
    if "null" in st.types:
        types.append("null")
    if level < 2:
        return f"- `{name}`: {'|'.join(types)}"

    enum = st.enum() if level >= 3 else None
    constant = enum[0][0] if enum and len(enum) == 1 else None
    if constant is not None:
        key = constant[1] if isinstance(constant, tuple) else constant
        shown = "true" if key is True else "false" if key is False else str(key)
        if len(shown) > EXAMPLE_LEN:
            shown = shown[:EXAMPLE_LEN - 1] + "…"
        line = f"- `{name}`: {' | '.join(types)} = {shown}"
        if st.n < rows:
            line += f", {st.n:,}/{rows:,}"
        return line
    parts = []
    for t in types:
        text = t
        if t == "number" and not enum and st.num_min is not None:
            rng = _num(st.num_min) if st.num_min == st.num_max else f"{_num(st.num_min)}–{_num(st.num_max)}"
            text += f" {rng} (int: {'yes' if st.all_int else 'no'})"
        elif t == "string" and level >= 3 and not enum:
            if st.dates and st.dates == st.types["string"]:
                text += f" (date) {st.str_min}–{st.str_max}"
            else:
                text += f" {st.len_min}–{st.len_max} chars" if st.len_min != st.len_max else f" {st.len_min} chars"
                text += _example_text(st)
        parts.append(text)
    line = f"- `{name}`: " + " | ".join(parts)
    if enum:
        total = sum(c for _, c in enum)
        line += ", enum: " + ", ".join(_enum_text(k, c, total) for k, c in enum)
    if st.n < rows:
        line += f", {st.n:,}/{rows:,}"
    return line


def _rare_subfield(name: str, st: FieldStats, profile: Profile) -> bool:
    """A flattened `parent.key` seen in under 2% of the records that have the parent."""
    parent = profile.fields.get(name.rsplit(".", 1)[0]) if "." in name else None
    return parent is not None and parent.n >= 50 and st.n * 50 < parent.n and name in profile.sub_counts.get(
        name.rsplit(".", 1)[0], ())


def render_fields(profile: Profile, level: int) -> list:
    lines = [render_field(name, st, profile.rows, level) for name, st in profile.fields.items()
             if not _rare_subfield(name, st, profile)]
    if profile.skipped_fields:
        lines.append(f"- ... and more fields (only the first {MAX_FIELDS} are profiled)")
    return lines


def render_profile(profile: Profile, level: int) -> str:
    """Markdown summary. Level 1 = names + types, 2 = + counts and ranges, 3+ = + examples and enums."""
    head = f"Rows: {profile.rows:,}"
    if profile.truncated:
        head += " (profile stopped at this many rows; file has more)"
    out = [head]
    if level >= 2:
        out.append("Fields (present in every row unless n/N is shown):")
    else:
        out.append("Fields:")
    out.extend(render_fields(profile, level))
    return "\n".join(out)


# --- maps (dicts used as id -> record lookups) ----------------------------

def map_kind(d: dict) -> Optional[str]:
    """'records' when d maps many keys to similar objects (npm "packages", OpenAPI
    "paths"), 'scalars' when it maps very many keys to one scalar type, else None."""
    n = len(d)
    if n < MAP_MIN_RECORDS:
        return None
    vals = list(d.values())
    dict_vals = [v for v in vals if isinstance(v, dict)]
    if len(dict_vals) * 10 >= n * 9:
        sample = dict_vals[:300]
        counts = Counter(k for v in sample for k in v)
        common = {k for k, c in counts.items() if c * 5 >= len(sample)}
        if not common:
            return None
        score = sum((sum(1 for k in v if k in common) / len(v)) if v else 1.0 for v in sample) / len(sample)
        return "records" if score >= 0.8 else None
    if n >= MAP_MIN_SCALARS:
        types = Counter(json_type(v) for v in vals[:300])
        top, c = types.most_common(1)[0]
        if top in ("string", "number", "boolean") and c * 10 >= sum(types.values()) * 9:
            return "scalars"
    return None


def _key_text(key) -> str:
    text = str(key)
    return "`" + (text if len(text) <= 40 else text[:39] + "…") + "`"


def describe_map(d: dict, kind: str, level: int) -> list:
    """Lines describing a map: its keys and the shape of its values (no indent)."""
    keys = list(d)
    n = len(keys)
    if n <= (MAP_KEYS_LISTED if kind == "records" else MAP_SCALAR_KEYS_LISTED):
        picked, label = keys, "keys"
    else:
        picked, label = [keys[i * (n - 1) // 3] for i in range(4)], "keys e.g."
    lines = [f"{label}: " + ", ".join(_key_text(k) for k in picked)]
    if kind == "records":
        objs = [v for v in d.values() if isinstance(v, dict)]
        lines.append("each value (object):")
        lines.extend("  " + fl for fl in render_fields(profile_records(objs), level))
    else:
        st = FieldStats()
        for v in d.values():
            st.add(v)
        lines.append(render_field("value", st, n, level).replace("- `value`:", "each value:", 1))
    return lines


# --- size helpers shared by the data converters -------------------------------

_counter = None


def text_size(text: str) -> int:
    """cl100k tokens for normal sizes, a character estimate for huge texts."""
    global _counter
    if len(text) > 300_000:
        return len(text) // 3
    if _counter is None:
        from token_shredder.metrics import TokenCounter
        _counter = TokenCounter()
    return _counter.estimate(text)


def clamp_levels(render, level: int, full: str) -> str:
    """Output for `level` (1-4) with the two promises every data converter makes:
    never larger than `full` (the lossless alternative), and never smaller than the
    output of the level below. render(lv) gives the lossy text for one level."""
    full_size = text_size(full)
    out, out_size = None, 0
    for lv in range(1, level + 1):
        cur = render(lv)
        size = text_size(cur)
        if size >= full_size or len(cur) >= len(full):
            cur, size = full, full_size
        if out is not None and (out_size > size or len(out) > len(cur)):
            cur, size = out, out_size
        out, out_size = cur, size
    return out


# --- tables (CSV / XLSX sheets) -------------------------------------------

SAMPLE_ROWS = 5
_FULL_KEEP_CHARS = 400_000  # keep the full table for the "never longer" fallback only below this


def md_escape(cell) -> str:
    text = "" if cell is None else str(cell)
    return text.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ').replace('|', '\\|')


def _md_row(cells) -> str:
    return "| " + " | ".join(md_escape(c) for c in cells) + " |"


def summarize_table(headers: list, rows: Iterable[list], level: int, full_text: Optional[str] = None) -> str:
    """Markdown for a table read as text cells (streaming, bounded memory).

    1 = column names; 2 = + types and ranges; 3 = full profile + first 5 rows;
    4+ = the whole table. At every level a summary that is not smaller than the
    whole table is replaced by the whole table, and sizes never shrink as the
    level goes up. `full_text` is the lossless alternative when it is not the
    markdown table (CSV passes the fenced file).
    """
    names = unique_headers(headers)
    ncols = len(names)
    head_lines = [_md_row(headers), "| " + " | ".join(["---"] * ncols) + " |"]
    full = list(head_lines)
    full_len = sum(len(x) + 1 for x in full)
    keep_full = True
    sample = []
    profile = Profile()
    count = 0
    for row in rows:
        count += 1
        if level >= 4 or keep_full or len(sample) < SAMPLE_ROWS:
            line = _md_row(row)
            if len(sample) < SAMPLE_ROWS:
                sample.append(line)
            if keep_full:
                full.append(line)
                full_len += len(line) + 1
                if full_len > _FULL_KEEP_CHARS and level < 4:
                    keep_full = False
                    full = None
        if level < 4:
            profile.add({n: infer_cell(str(c)) for n, c in zip(names, row) if c is not None})

    full_md = "\n".join(full) if full is not None else None
    if level >= 4:
        return full_md
    summary = f"Rows: {count:,}, columns: {ncols}"
    profile.rows = count

    def render(lv: int) -> str:
        if lv == 1:
            return summary + "\n\nColumns: " + ", ".join(f"`{n}`" for n in names)
        body = render_profile(profile, lv).split("\n", 1)[1]
        lossy = summary + "\n\n" + body
        if lv >= 3 and sample:
            lossy += f"\n\nFirst {len(sample)} rows:\n\n" + "\n".join(head_lines + sample)
        return lossy

    whole = full_text if full_text is not None else full_md
    if whole is None:
        return render(level)
    return clamp_levels(render, level, whole)
