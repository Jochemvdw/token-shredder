"""
token_shredder - Question-aware shredding (--query)

Splits a file's full content into chunks (functions, sections, paragraphs,
records), ranks them against the query with BM25, and keeps the best ones in
full next to the normal outline. No model, no network: plain keyword relevance,
with identifiers split (truncateMiddle -> truncate, middle; parse_dict -> parse, dict).
"""
import ast
import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, List, Optional

STOPWORDS = set("""
a an and are as at be by can could do does did for from has have how i if in into is it its
me my of on or should so than that the their them then there these this to was we what when
where which who why will with would you your about does work works used use using get give
show tell explain find file files code text please there any all some one
""".split())

CODE_FORMATS = {'py', 'python', 'js', 'mjs', 'cjs', 'ts', 'tsx', 'jsx', 'java', 'go', 'rs',
                'c', 'cpp', 'cc', 'cxx', 'h', 'hpp', 'cs', 'kt', 'rb', 'php', 'sh', 'bash', 'zsh'}
MAX_CHUNK_TOKENS = 1500


@dataclass
class Chunk:
    title: str            # where it is: "function truncate (lines 120-158)", "## Results"
    text: str
    order: int            # position in the file, to print selected chunks in reading order
    lang: str = ""        # code fence language, "" for prose
    tokens: int = 0
    score: float = 0.0
    source: str = ""      # file, for folder mode
    terms: Counter = field(default_factory=Counter)


# --- tokenising ----------------------------------------------------------------

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9]*|\d+")
_CAMEL = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")


def terms(text: str) -> List[str]:
    """Lower-case terms; identifiers are split (truncateMiddle -> truncate, middle) and
    also kept whole (truncatemiddle), so exact names score highest."""
    out = []
    for word in _WORD.findall(text):
        low = word.lower()
        parts = [p.lower() for p in _CAMEL.findall(word)]
        if len(parts) > 1:
            out.append(low)
        for p in parts or [low]:
            if len(p) > 1 and p not in STOPWORDS:
                out.append(_stem(p))
    return out


def _stem(w: str) -> str:
    for suffix in ("ing", "ies", "es", "s", "ed"):
        if len(w) > len(suffix) + 2 and w.endswith(suffix):
            return w[: -len(suffix)] + ("y" if suffix == "ies" else "")
    return w


def query_terms(query: str) -> List[str]:
    return list(dict.fromkeys(terms(query)))


# --- chunking -----------------------------------------------------------------

def chunk_python(source: str) -> List[Chunk]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return chunk_lines(source, "py")
    lines = source.splitlines()
    chunks = []

    def add(node, title):
        start = min([d.lineno for d in getattr(node, "decorator_list", [])] + [node.lineno])
        text = "\n".join(lines[start - 1: node.end_lineno])
        chunks.append(Chunk(f"{title} (lines {start}-{node.end_lineno})", text, start, "python"))

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            add(node, f"function {node.name}")
        elif isinstance(node, ast.ClassDef):
            methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            if methods and node.end_lineno - node.lineno > 60:
                head_end = methods[0].lineno - 1
                chunks.append(Chunk(f"class {node.name} (lines {node.lineno}-{head_end})",
                                    "\n".join(lines[node.lineno - 1: head_end]), node.lineno, "python"))
                for m in methods:
                    add(m, f"method {node.name}.{m.name}")
            else:
                add(node, f"class {node.name}")
    return chunks or chunk_lines(source, "py")


def chunk_code(source: str, lang: str) -> List[Chunk]:
    """Other languages: a chunk starts at each declaration (with its doc comment)."""
    from token_shredder.converters.code_converter import CodeConverter
    lines = source.splitlines()
    starts = []
    for i, line in enumerate(lines):
        if CodeConverter._DECL_RE.match(line) or CodeConverter._MEMBER_RE.match(line):
            j = i
            while j > 0 and lines[j - 1].strip().startswith(("*", "/*", "//", "*/", "#[", "@")):
                j -= 1
            starts.append((j, line.strip().rstrip("{").strip()))
    if not starts:
        return chunk_lines(source, lang)
    chunks = []
    for n, (start, decl) in enumerate(starts):
        end = starts[n + 1][0] if n + 1 < len(starts) else len(lines)
        if start >= end:
            continue
        name = decl if len(decl) <= 80 else decl[:77] + "..."
        chunks.append(Chunk(f"{name} (lines {start + 1}-{end})", "\n".join(lines[start:end]).rstrip(),
                            start + 1, lang))
    return chunks


def chunk_lines(text: str, lang: str = "", size: int = 60) -> List[Chunk]:
    lines = text.splitlines()
    return [Chunk(f"lines {i + 1}-{min(i + size, len(lines))}", "\n".join(lines[i:i + size]), i + 1, lang)
            for i in range(0, len(lines), size)]


_HEADING = re.compile(r"^(#{1,6})\s+(.*)")


def chunk_prose(markdown: str) -> List[Chunk]:
    """Sections by heading; long sections split into groups of paragraphs."""
    chunks, path, buf, order = [], [], [], 0

    def flush():
        nonlocal buf
        body = "\n".join(buf).strip()
        if body:
            title = " > ".join(path) if path else "(start)"
            paras = re.split(r"\n\s*\n", body)
            group, glen = [], 0
            for p in paras:
                group.append(p)
                glen += len(p)
                if glen > 2400:
                    chunks.append(Chunk(title, "\n\n".join(group), len(chunks)))
                    group, glen = [], 0
            if group:
                chunks.append(Chunk(title, "\n\n".join(group), len(chunks)))
        buf = []

    in_fence = False
    for line in markdown.splitlines():
        if line.strip().startswith("```"):
            in_fence = not in_fence
        m = None if in_fence else _HEADING.match(line)
        if m and re.fullmatch(r"Page \d+", m.group(2).strip()):
            continue  # page markers from PDFs are not sections
        if m:
            flush()
            depth = len(m.group(1))
            path = path[: depth - 1] + [m.group(2).strip()]
            order += 1
        else:
            buf.append(line)
    flush()
    return chunks


def chunk_records(records: list, label: Callable[[int, object], str]) -> List[Chunk]:
    out = []
    for i, r in enumerate(records):
        text = json.dumps(r, ensure_ascii=False, separators=(",", ":")) if not isinstance(r, str) else r
        out.append(Chunk(label(i, r), text, i))
    return out


def chunk_csv(text: str) -> List[Chunk]:
    import csv
    import io
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return []
    header = rows[0]
    return [Chunk(f"row {i}", ",".join(header) + "\n" + ",".join(r), i, "csv")
            for i, r in enumerate(rows[1:], 1) if r]


def chunk_json(text: str) -> List[Chunk]:
    try:
        data = json.loads(text)
    except ValueError:
        return chunk_lines(text, "json")
    if isinstance(data, dict):
        # The biggest list/map inside is usually the data (items, packages, ...)
        best = max(((k, v) for k, v in data.items() if isinstance(v, (list, dict))),
                   key=lambda kv: len(kv[1]), default=None)
        if best and len(best[1]) > 5:
            k, v = best
            if isinstance(v, list):
                return chunk_records(v, lambda i, r: f"{k}[{i}]")
            return chunk_records(list(v.items()), lambda i, kv: f"{k}[{kv[0]!r}]")
        return chunk_records(list(data.items()), lambda i, kv: f"key {kv[0]!r}")
    if isinstance(data, list):
        return chunk_records(data, lambda i, r: f"item {i}")
    return []


def chunk_file(full_text: str, fmt: str) -> List[Chunk]:
    """Chunks of a file's full content. full_text is the raw file for text formats and
    the converter's full extraction (level 4) for documents and web pages."""
    if fmt in ("py", "python"):
        chunks = chunk_python(full_text)
    elif fmt in CODE_FORMATS:
        chunks = chunk_code(full_text, fmt)
    elif fmt in ("csv", "tsv"):
        chunks = chunk_csv(full_text)
    elif fmt in ("json",):
        chunks = chunk_json(full_text)
    elif fmt in ("jsonl", "ndjson"):
        chunks = chunk_records([ln for ln in full_text.splitlines() if ln.strip()],
                               lambda i, r: f"line {i + 1}")
    else:
        chunks = chunk_prose(full_text)
    out = []
    for c in chunks:
        # Very long chunks are split so one giant function can't eat the budget.
        if len(c.text) > MAX_CHUNK_TOKENS * 4:
            for sub in chunk_lines(c.text, c.lang, size=80):
                out.append(Chunk(f"{c.title}, part {sub.title}", sub.text, c.order, c.lang))
        else:
            out.append(c)
    return out


# --- ranking -------------------------------------------------------------------

def rank(chunks: List[Chunk], query: str, k1: float = 1.2, b: float = 0.75) -> List[Chunk]:
    """BM25 scores (title counts double). Returns chunks with score > 0, best first."""
    q = query_terms(query)
    if not q or not chunks:
        return []
    for c in chunks:
        c.terms = Counter(terms(c.text)) + Counter({t: 2 * n for t, n in Counter(terms(c.title)).items()})
    n = len(chunks)
    avg = sum(sum(c.terms.values()) for c in chunks) / n or 1
    df = Counter(t for c in chunks for t in set(c.terms) if t in q)
    for c in chunks:
        length = sum(c.terms.values()) or 1
        score = 0.0
        for t in q:
            tf = c.terms.get(t, 0)
            if tf:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * length / avg))
        # Chunks matching more of the distinct query terms come first.
        coverage = sum(1 for t in q if c.terms.get(t)) / len(q)
        c.score = score * (0.5 + coverage)
        # A function/class/section whose own name is in the question is what was asked for.
        name = _chunk_name(c.title)
        section = [t for t in terms(re.sub(r"^[\d.\s]+", "", c.title.split(" > ")[-1]))
                   if not t.isdigit()]
        if (name and (name in q or _stem(name) in q)) or \
                (not c.lang and section and len(section) <= 3 and set(section) <= set(q)):
            c.score = c.score * 2 + 10
    return sorted((c for c in chunks if c.score > 0), key=lambda c: -c.score)


_NAME = re.compile(r"(?:function|class|def|method|fn|func|interface|struct|enum|type)\s+"
                   r"(?:\([^)]*\)\s*)?(?:[\w$]+\.)?([\w$]+)")


def _chunk_name(title: str) -> str:
    m = _NAME.search(title)
    if not m:
        m = re.match(r"\s*(?:[\w<>\[\],?]+\s+)*([A-Za-z_$][\w$]*)\s*\(", title)
    return m.group(1).lower() if m else ""


def select(ranked: List[Chunk], budget: int, count: Callable[[str], int],
           min_ratio: float = 0.3, max_chunks: int = 8) -> List[Chunk]:
    """Best chunks that fit the budget, dropping weak matches (< min_ratio of the best)."""
    if not ranked:
        return []
    top = ranked[0].score
    chosen, used = [], 0
    for c in ranked:
        if c.score < top * min_ratio:
            break
        c.tokens = c.tokens or count(c.text) + count(c.title) + 8
        if used + c.tokens > budget:
            continue
        chosen.append(c)
        used += c.tokens
        if len(chosen) >= max_chunks:
            break
    return chosen


def render(chosen: List[Chunk], query: str, with_source: bool = False) -> str:
    if not chosen:
        return f'\n## Relevant to "{query}"\n\nNo part of the file matches the query.\n'
    parts = [f'\n## Relevant to "{query}" (full text of the best-matching parts)\n']
    for c in sorted(chosen, key=lambda c: (c.source, c.order)):
        where = f"{c.source}: {c.title}" if with_source and c.source else c.title
        parts.append(f"### {where}")
        parts.append(f"```{c.lang}\n{c.text}\n```" if c.lang else c.text)
        parts.append("")
    return "\n".join(parts)
