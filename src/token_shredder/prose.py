"""
token_shredder - prose helpers shared by the PDF, DOCX, PPTX, TXT and Markdown converters.

Pipeline for text that comes from a PDF or a plain-text file:

    lines --strip_running--> lines without running headers/footers/page numbers
          --build_blocks---> Block list (headings, paragraphs, list items, tables, code)
          --render---------> markdown for detail level 1..4

Detail levels for prose:
    1  title + headings only
    2  + the first sentence of every paragraph (first item of every list)
    3  the full cleaned text (default)
    4  + what level 3 drops: PDF page markers, PPTX speaker notes, DOCX headers/footers,
       Markdown link URLs, images, HTML
    5  full extraction without clean-up (handled by the converters / main.py)
"""
from __future__ import annotations

import html
import re
from collections import Counter
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set

# --------------------------------------------------------------------------- #
# Small text helpers
# --------------------------------------------------------------------------- #

_LIGATURES = str.maketrans({
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi",
    "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st",
    " ": " ", "­": "", "\x00": "", "\x0c": "",
})
_SPACES = re.compile(r"[ \t]+")
_DOT_LEADER = re.compile(r"(?:\s*\.){4,}")
_RULE_LINE = re.compile(r"^\s*([-=_*~#+.])\1{3,}\s*$")
_TERMINAL = (".", ":", "?", "!")
_CLOSERS = "\"')]}”’"


def tidy(text: str) -> str:
    """Normalise one line or paragraph: ligatures, odd spaces, dot leaders, runs of spaces."""
    text = text.translate(_LIGATURES)
    text = _DOT_LEADER.sub(" ", text)
    text = re.sub(r"_{4,}", "___", text)
    return _SPACES.sub(" ", text).strip()


def ends_terminal(line: str) -> bool:
    line = line.rstrip()
    while line and line[-1] in _CLOSERS:
        line = line[:-1]
    return line.endswith(_TERMINAL)


_ABBREV = {
    "e.g", "i.e", "et al", "al", "fig", "figs", "eq", "eqs", "sec", "no", "vs", "dr", "mr", "mrs",
    "ms", "etc", "approx", "cf", "inc", "ltd", "ca", "pp", "vol", "ed", "eds", "st", "jr", "sr",
    "prof", "resp", "ref", "refs", "cp", "viz", "tab",
}
_SENT_END = re.compile(r"""[.!?]["')\]”’]*\s+(?=["'(\[“]?[A-Z0-9])""")


def first_sentence(text: str, limit: int = 300) -> str:
    """The first sentence of a paragraph (abbreviations and initials do not end it)."""
    text = text.strip()
    for m in _SENT_END.finditer(text):
        before = text[: m.start() + 1]
        word = re.search(r"([A-Za-z.]+)\.$", before)
        w = word.group(1).lower().rstrip(".") if word else ""
        if w in _ABBREV or (len(w) == 1 and w.isalpha() and word and word.group(1).isupper()):
            continue
        return _cap(text[: m.start() + 1], limit)
    return _cap(text, limit)


def _cap(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut.rstrip(",;:") + " ..."


# --------------------------------------------------------------------------- #
# Blocks and rendering
# --------------------------------------------------------------------------- #

@dataclass
class Block:
    kind: str          # title | heading | para | list | table | code | page | toc | extra
    text: str          # for table/code: newline-separated lines
    level: int = 0     # heading depth (1 = document title)


def render_blocks(blocks: Sequence[Block], level: int, raw: bool = False) -> str:
    """Markdown for detail level 1-4 (5 behaves as 4 but skips tidy-ups when raw=True)."""
    out: List[str] = []
    seen_heading = any(b.kind in ("title", "heading") for b in blocks)
    first_para_done = False
    i = 0
    n = len(blocks)
    while i < n:
        b = blocks[i]
        k = b.kind
        if k in ("title", "heading"):
            out.append("#" * max(1, min(b.level or 2, 6)) + " " + (b.text if raw else tidy(b.text)))
        elif k == "page":
            if level >= 4:
                out.append(f"## Page {b.text}")
        elif k == "toc":
            if level >= 4:
                out.append(b.text)
        elif k == "extra":
            if level >= 4:
                out.append(b.text)
        elif k == "list":
            j = i
            items = []
            while j < n and blocks[j].kind == "list":
                items.append(blocks[j].text)
                j += 1
            i = j - 1
            if level >= 3:
                out.append("\n".join(items if raw else (_tidy_indented(x) for x in items)))
            elif level == 2:
                out.append(first_sentence(items[0]) if not _is_marked(items[0]) else _mark_first(items[0]))
        elif k == "para":
            if level >= 3:
                out.append(b.text if raw else tidy(b.text))
            elif level == 2:
                out.append(first_sentence(b.text))
            elif level == 1 and not seen_heading and not first_para_done:
                out.append(first_sentence(b.text, 200))
            first_para_done = True
        elif k in ("table", "code"):
            if level >= 3:
                lines = b.text.split("\n")
                if k == "code" and len(lines) > 1:
                    out.append("```\n" + b.text + "\n```")
                else:
                    out.append(b.text)
        i += 1
    if not any(x.strip() for x in out) and level < 3:
        for b in blocks:  # nothing but tables/code: show where the text starts
            if b.text.strip() and b.kind not in ("page", "extra"):
                return first_sentence(b.text.strip().split("\n")[0], 200)
    return "\n\n".join(x for x in out if x.strip())


def _tidy_indented(text: str) -> str:
    """tidy() each line of a list item but keep its leading indentation."""
    lines = []
    for line in text.split("\n"):
        lead = line[: len(line) - len(line.lstrip(" "))]
        lines.append(lead + tidy(line))
    return "\n".join(lines)


_MARK_RE = re.compile(r"^(\s*(?:[-*+•●▪–o]|\d+[.)]|\(?[a-zA-Z][.)])\s+)(.*)$", re.S)


def _is_marked(item: str) -> bool:
    return bool(_MARK_RE.match(item))


def _mark_first(item: str) -> str:
    m = _MARK_RE.match(item)
    return m.group(1) + first_sentence(m.group(2), 200)


def levels_output(render: Callable[[int], str], level: int) -> str:
    """render(1..level), made monotonic: a higher level is never shorter than a lower one."""
    best = ""
    for lv in range(1, max(1, min(level, 4)) + 1):
        out = render(lv)
        if len(out) < len(best):
            out = best
        best = out
    return best


# --------------------------------------------------------------------------- #
# Running headers / footers / page numbers
# --------------------------------------------------------------------------- #

class _Soft:
    """Marker left where a running header/footer was removed (a page boundary)."""
    __slots__ = ("page",)

    def __init__(self, page: Optional[int] = None):
        self.page = page


_PAGE_NUM = re.compile(
    r"^(?:[-–—]\s*)?(?:page\s*)?\[?\(?\d{1,4}\)?\]?(?:\s*(?:of|/)\s*\d{1,4})?(?:\s*[-–—])?$",
    re.I)


def _norm_running(line: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\d+", "#", line.translate(_LIGATURES))).strip()


def strip_running(pages: Sequence[Sequence[str]], mark_pages: bool = False) -> List[object]:
    """Flatten pages into one entry list, dropping running headers/footers and page numbers.

    A line is a running header/footer when its digit-normalised form sits among the
    first/last lines of 3+ pages (or, for text without page breaks, repeats 3+ times and
    contains digits or wide gaps). Removed lines become a _Soft marker so paragraphs that
    continue across a page break can still be joined. Entries are str lines or _Soft.
    """
    pages = [list(p) for p in pages]
    npages = len(pages)
    remove: Set[tuple] = set()  # (page, line index)

    if npages >= 3:
        counts: Counter = Counter()
        edge_cache = []
        for pi, lines in enumerate(pages):
            idx = [i for i, l in enumerate(lines) if l.strip() and not _RULE_LINE.match(l)]
            edge = idx[:3] + idx[-3:] if len(idx) > 6 else idx
            edge_cache.append((idx, set(edge)))
            seen = set()
            for i in edge:
                key = _norm_running(lines[i])
                if len(key) >= 4 and key not in seen:
                    seen.add(key)
                    counts[key] += 1
        threshold = 3 if npages < 12 else max(3, npages // 5)
        threshold = min(threshold, 3) if npages <= 12 else threshold
        repeated = {k for k, c in counts.items() if c >= threshold}
        for pi, lines in enumerate(pages):
            idx, edge = edge_cache[pi]
            near = set(idx[:2] + idx[-2:])
            for i in edge:
                key = _norm_running(lines[i])
                if key in repeated:
                    remove.add((pi, i))
                elif i in near and _PAGE_NUM.match(lines[i].strip()):
                    remove.add((pi, i))
    else:
        # No usable page structure: look at the whole text for repeating header/footer lines.
        flat = [(pi, i, l) for pi, lines in enumerate(pages) for i, l in enumerate(lines)]
        counts = Counter()
        for _, _, l in flat:
            s = l.strip()
            if 8 <= len(s) <= 120 and (re.search(r"\d", s) or re.search(r"\S {3,}\S", s)):
                counts[_norm_running(l)] += 1
        for pi, i, l in flat:
            s = l.strip()
            if s and counts.get(_norm_running(l), 0) >= 3 and 8 <= len(s) <= 120 \
                    and (re.search(r"\d", s) or re.search(r"\S {3,}\S", s)) \
                    and not _looks_like_content(s):
                remove.add((pi, i))

    entries: List[object] = []
    for pi, lines in enumerate(pages):
        if mark_pages or npages > 1:
            entries.append(_Soft(pi + 1))
        for i, l in enumerate(lines):
            entries.append(_Soft() if (pi, i) in remove else l)
    return entries


def _looks_like_content(s: str) -> bool:
    """Guard for the no-page-structure case: sentences and list items repeat legitimately."""
    return bool(re.match(r"^(?:[-*•o]|\d+[.)])\s", s)) or (ends_terminal(s) and len(s.split()) > 6)


# --------------------------------------------------------------------------- #
# Line classification and block building
# --------------------------------------------------------------------------- #

_LIST_RE = re.compile(
    r"^(?:[-*+•●▪◦‣⁃–—]|o|\d{1,3}(?:\.\d{1,3})*[.)]|\(\d{1,3}\)|\(?[a-zA-Z][.)]|\[\d{1,3}\])\s+\S")
_NUM_HEAD = re.compile(
    r"^(?:(?P<num>\d{1,2}(?:\.\d{1,3}){0,4}|[A-Z](?:\.\d{1,3}){1,4}|[A-Z]|[IVX]{1,5})(?P<dot>\.)?"
    r"|(?:Appendix|Annex)\s+[A-Z0-9]+[.:]?|(?:Chapter|Section|Part)\s+\d+[.:]?)\s+(?P<t>\S.*)$")
_SMALL_WORDS = {"of", "the", "and", "for", "in", "to", "a", "an", "on", "with", "or", "at", "by",
                "from", "as", "is", "are", "vs", "via", "per"}
_KNOWN_HEADS = {"abstract", "introduction", "references", "conclusion", "conclusions", "contents",
                "table of contents", "bibliography", "summary", "background", "related work",
                "acknowledgements", "acknowledgments", "appendix", "discussion", "results",
                "methods", "overview", "security considerations", "iana considerations",
                "status of this memo", "copyright notice", "author's address", "authors' addresses", "full copyright statement"}


def _words_ok_for_heading(t: str) -> bool:
    words = t.split()
    return 1 <= len(words) <= 12 and len(t) <= 100 and not t.rstrip().endswith((",", ";", ".", ":"))


def numbered_heading(s: str) -> Optional[tuple]:
    """(depth, full text) when s looks like '3.2 Scaled Dot-Product Attention'."""
    if len(s) > 110:
        return None
    m = _NUM_HEAD.match(s)
    if not m:
        return None
    t = m.group("t")
    num = m.group("num")
    if not _words_ok_for_heading(t):
        return None
    if re.search(r"\.{3,}|\s\d{1,4}$", t) and not re.match(r"\d", t):
        return None  # table-of-contents line with page number
    first = t[0]
    depth_guess = len(num.split(".")) if num else 1
    if not (first.isupper() or first.isdigit() or (depth_guess >= 2 and first.isalpha())):
        return None
    tw = t.split()
    if depth_guess == 1:
        caps = [w for w in tw if w.lower().strip("(),") not in _SMALL_WORDS]
        if (len(tw) > 8 or "," in t or tw[-1].lower() in _SMALL_WORDS
                or (len(caps) > 2 and sum(w[:1].isupper() for w in caps) / len(caps) < 0.6)):
            return None
    if num is not None and re.fullmatch(r"[A-Z]|[IVX]{1,5}", num) and not m.group("dot"):
        return None  # "A Study of ..." is a sentence, not heading "A."
    if num is not None and re.fullmatch(r"[A-Z]", num) and len(t.split()) > 6:
        return None  # "A. Vaswani, N. Shazeer, ..." (reference entries)
    if num is not None and re.fullmatch(r"\d{1,2}", num) and not m.group("dot") and first.isdigit():
        return None  # "3 120 volts"
    if re.search(r"[,;]\s", t) and len(t.split()) > 7:
        return None
    depth = len(num.split(".")) if num and re.match(r"\d", num) else 1
    if num and re.match(r"[A-Z]\.", num):
        depth = len(num.split("."))
    return depth, s


def _title_case_heading(s: str) -> bool:
    if len(s) < 8 or len(s) > 80 or not s[0].isupper():
        return False
    if s.endswith((".", ",", ";", ":")):
        return False
    words = s.split()
    if not 2 <= len(words) <= 9:
        return False
    for w in words:
        wl = w.strip("()?!\"'").lower()
        if not wl:
            continue
        if wl in _SMALL_WORDS or not wl[0].isalpha():
            continue
        if not w.strip("(\"'")[:1].isupper():
            return False
    return not re.search(r"\d{3,}|@|https?://", s)


def _caps_heading(s: str) -> bool:
    letters = [c for c in s if c.isalpha()]
    return (len(letters) >= 4 and s == s.upper() and len(s.split()) <= 8 and len(s) <= 70
            and not s.endswith((".", ",", ";", ":")) and not re.search(r"\d.*\d", s))


def _indent(line: str) -> int:
    expanded = line.expandtabs(8)
    return len(expanded) - len(expanded.lstrip(" "))


def _percentile(values: List[int], p: float) -> int:
    if not values:
        return 0
    values = sorted(values)
    return values[min(len(values) - 1, int(len(values) * p))]


def _key(s: str) -> str:
    return re.sub(r"\W+", "", s.casefold())


def _vocab(entries: Iterable[object]):
    words: Set[str] = set()
    hyph: Set[str] = set()
    for e in entries:
        if isinstance(e, str):
            e = re.sub(r"[A-Za-z]+-\s*$", "", e)  # a word split over two lines is not vocabulary
            for w in re.findall(r"[A-Za-z]+(?:-[A-Za-z]+)*", e):
                wl = w.lower()
                if "-" in wl:
                    hyph.add(wl)
                else:
                    words.add(wl)
    return words, hyph


_KEEP_SUFFIX = {"based", "wise", "like", "free", "level", "style", "specific", "related", "driven",
                "scale", "art", "to", "of", "by", "in", "term", "side", "only", "aware", "agnostic",
                "oriented", "centric", "line", "time", "less", "way", "fold", "shot", "step"}


def _join_lines(prev: str, nxt: str, words: Set[str], hyph: Set[str]) -> str:
    """Join two wrapped lines, healing a split word ('trans-' + 'former')."""
    m = re.search(r"(?:^|[^\w-])([a-z]{2,})-$", prev)
    if m and nxt[:1].islower():
        frag = m.group(1)
        mt = re.match(r"[a-z]+", nxt)
        tail = mt.group(0) if mt else ""
        if frag + tail in words:
            return prev[:-1] + nxt
        if f"{frag}-{tail}" in hyph or tail in _KEEP_SUFFIX:
            return prev + nxt
        if len(frag) >= 4 and len(tail) >= 4 and frag in words and tail in words:
            return prev + nxt  # two real words: a compound like "sequence-aligned"
        return prev[:-1] + nxt
    if re.search(r"[A-Za-z0-9]-$", prev) and nxt[:1].islower():
        return prev + nxt  # "English-" + "to-German": the hyphen is real
    return prev + " " + nxt


def build_blocks(entries: Sequence[object], known_headings: Optional[Dict[str, int]] = None,
                 mark_pages: bool = False, detect_title: bool = True) -> List[Block]:
    """Turn cleaned lines into blocks: headings, paragraphs, list items, tables, code."""
    known_headings = known_headings or {}
    text_lines = [e for e in entries if isinstance(e, str) and e.strip()]
    if not text_lines:
        return []
    indents = [_indent(l) for l in text_lines if len(l.strip()) > 30]
    base = Counter(indents).most_common(1)[0][0] if indents else 0
    lens = [len(tidy(l)) for l in text_lines if len(l.strip()) >= 20]
    typical = max(_percentile(lens, 0.9), 20)
    words, hyph = _vocab(entries)
    n_blank = sum(1 for e in entries if isinstance(e, str) and not e.strip())

    numbered = sum(1 for l in text_lines if numbered_heading(tidy(l)) is not None
                   and _indent(l) <= max(base - 1, 0))
    loose_headings = numbered < 3 and not known_headings

    blocks: List[Block] = []
    cur: Optional[Block] = None          # open para/list block
    cur_last = ""                         # last raw (tidied) line of cur
    pending_blank = False
    soft = False
    prev_ok = True                        # previous line ended a sentence / start of a block
    title_done = not detect_title
    nonblank_seen = 0

    def flush():
        nonlocal cur
        if cur is not None:
            blocks.append(cur)
            cur = None

    for e in entries:
        if isinstance(e, _Soft):
            soft = True
            if e.page is not None and mark_pages:
                flush()
                blocks.append(Block("page", str(e.page)))
            continue
        raw = e
        if not raw.strip() or _RULE_LINE.match(raw):
            pending_blank = True
            continue
        s = tidy(raw)
        if not s:
            pending_blank = True
            continue
        ind = _indent(raw)
        nonblank_seen += 1

        # --- title (centred line near the top of a text file)
        if (not title_done and nonblank_seen <= 40 and ind >= 12 and 6 <= len(s) <= 100
                and not re.search(r"\S {3,}\S", raw.strip())
                and abs(ind - (max(typical + base, 72) - ind - len(raw.strip()))) <= 8):
            flush()
            blocks.append(Block("title", s, 1))
            title_done = True
            pending_blank = True
            soft = False
            prev_ok = True
            continue

        kind = None
        heading_depth = 0
        k = _key(s)
        if k and len(k) >= 3 and k in known_headings and len(s) < 150:
            kind, heading_depth = "heading", known_headings[k] + 1
        elif ind <= max(base - 1, 0) if base > 0 else ind == 0:
            nh = numbered_heading(s)
            if nh and (prev_ok or pending_blank or cur is None):
                kind, heading_depth = "heading", nh[0] + 1
            elif s.lower().rstrip(":") in _KNOWN_HEADS and len(s) < 40:
                kind, heading_depth = "heading", 2
            elif prev_ok or pending_blank or cur is None:
                if loose_headings and (_title_case_heading(s) or _caps_heading(s)):
                    kind, heading_depth = "heading", 2
        if kind is None:
            if _LIST_RE.match(s):
                kind = "list"
            elif re.search(r"\S {3,}\S", raw.strip()) and not ends_terminal(s):
                kind = "table"
            elif ind >= base + 4 and (pending_blank or (cur is None and blocks and blocks[-1].kind == "code")):
                kind = "code"
            else:
                kind = "para"

        # --- joining
        if kind == "para":
            join = False
            if cur is not None and cur.kind in ("para", "list"):
                p = cur_last
                long_ = len(p) >= (0.85 if ends_terminal(p) else 0.6) * typical
                if pending_blank:
                    join = bool(soft) and not ends_terminal(p) and (s[:1].islower() or s[:1] == "(")
                else:
                    hyphen_wrap = bool(re.search(r"[a-z]-$", p)) and s[:1].islower()
                    join = hyphen_wrap or long_ or (not ends_terminal(p) and s[:1].islower())
                    # a short, non-terminal line followed by a capital is a label/line, not a wrap
                if join:
                    cur.text = _join_lines(cur.text, s, words, hyph)
                    cur_last = s
            if not join:
                flush()
                cur = Block("para", s)
                cur_last = s
        elif kind == "list":
            flush()
            cur = Block("list", s)
            cur_last = s
        elif kind == "heading":
            flush()
            blocks.append(Block("heading", s, min(heading_depth, 6)))
            cur_last = s
        elif kind == "toc":
            flush()
            blocks.append(Block("toc", s))
        elif kind == "table":
            flush()
            row = re.sub(r" {3,}", " | ", raw.strip().translate(_LIGATURES))
            row = re.sub(r" {2}", " ", row)
            if blocks and blocks[-1].kind == "table" and not pending_blank:
                blocks[-1].text += "\n" + row
            else:
                blocks.append(Block("table", row))
        elif kind == "code":
            flush()
            line = raw.expandtabs(8).rstrip()
            if blocks and blocks[-1].kind == "code":
                gap = "\n" if not pending_blank else "\n\n"
                blocks[-1].text += gap + line
            else:
                blocks.append(Block("code", line))
        prev_ok = ends_terminal(s) or kind in ("heading", "title", "table", "toc", "code")
        pending_blank = False
        soft = False
        if kind in ("heading", "toc", "table", "code"):
            cur_last = s
    flush()
    return _finish(blocks)


def _finish(blocks: List[Block]) -> List[Block]:
    """Dedent code, merge a table-of-contents into 'toc' blocks and drop the redundant ones at level 3."""
    for b in blocks:
        if b.kind == "code":
            lines = [l for l in b.text.split("\n")]
            nonblank = [l for l in lines if l.strip()]
            if nonblank:
                cut = min(_indent(l) for l in nonblank)
                lines = [l[cut:] if l.strip() else "" for l in lines]
            b.text = "\n".join(lines).strip("\n")
    # Table of contents: heading "Contents" followed by list/toc/table blocks that merely repeat headings.
    heading_keys = {_key(re.sub(r"^[\d.A-Z]{1,12}\.?\s+", "", b.text) or b.text) for b in blocks if b.kind == "heading"}
    heading_keys |= {_key(b.text) for b in blocks if b.kind == "heading"}
    heading_keys.discard("")
    out: List[Block] = []
    i = 0
    n = len(blocks)
    while i < n:
        b = blocks[i]
        out.append(b)
        if b.kind == "heading" and b.text.lower().strip(" :") in ("table of contents", "contents", "toc"):
            j = i + 1
            items = []
            while j < n and blocks[j].kind in ("list", "toc", "table", "code", "para") and \
                    (blocks[j].kind != "para" or len(blocks[j].text) < 120):
                items.append(blocks[j])
                j += 1
            if len(items) >= 3:
                titles = [_key(re.sub(r"^[\dA-Za-z]{0,3}[.)]?[\d.]*\s*", "", x.text.split("\n")[0])) for x in items]
                titles = [t for t in titles if t]
                hit = sum(1 for t in titles if t in heading_keys or any(t and t in h for h in heading_keys))
                if titles and hit / len(titles) >= 0.7:
                    out.append(Block("toc", "\n".join(x.text for x in items)))
                    i = j
                    continue
        i += 1
    # Merge consecutive blocks of the same 'toc' kind that were flagged individually.
    merged: List[Block] = []
    for b in out:
        if b.kind == "toc" and merged and merged[-1].kind == "toc":
            merged[-1].text += "\n" + b.text
        else:
            merged.append(b)
    return merged


def text_blocks(text: str, known_headings: Optional[Dict[str, int]] = None,
                mark_pages: bool = False) -> List[Block]:
    """Blocks for a plain-text document (form feeds separate pages)."""
    text = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    pages = [p.split("\n") for p in text.split("\f")] if "\f" in text else [text.split("\n")]
    pages = [p for p in pages if any(l.strip() for l in p)] or [[]]
    entries = strip_running(pages, mark_pages=mark_pages)
    return build_blocks(entries, known_headings, mark_pages=mark_pages)


def prose_from_text(text: str, level: int) -> str:
    """Complete pipeline for .txt files, levels 1-4."""
    blocks = text_blocks(text)
    if not blocks:
        return ""
    return levels_output(lambda lv: render_blocks(blocks, lv), level)


# --------------------------------------------------------------------------- #
# Markdown
# --------------------------------------------------------------------------- #

_ENTITY = re.compile(r"&(?:[a-zA-Z]{2,8}|#\d{1,6}|#x[0-9a-fA-F]{1,5});")
_CODE_SPAN = re.compile(r"(`+)(?:(?!\1).)+?\1")
_FENCE = re.compile(r"^\s*(`{3,}|~{3,})")  # any indent: fences nested in list items
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
_BADGE_LINK = re.compile(r"\[\s*!\[[^\]]*\]\([^)]*\)\s*\]\([^)]*\)")
_BADGE_REF = re.compile(r"\[\s*!\[[^\]]*\]\[[^\]]*\]\s*\](?:\[[^\]]*\]|\([^)]*\))")
_IMAGE = re.compile(r"!\[[^\]]*\](?:\((?:[^()]|\([^()]*\))*\)|\[[^\]]*\])")
_HTML_TAGS = ("a|abbr|b|big|blockquote|br|center|cite|code|dd|del|details|div|dl|dt|em|figcaption|figure|font|"
              "h[1-6]|hr|i|img|ins|kbd|li|mark|nobr|ol|p|picture|pre|s|samp|small|source|span|strike|strong|"
              "sub|summary|sup|svg|table|tbody|td|tfoot|th|thead|tr|tt|u|ul|video|audio|iframe|object|embed|"
              "section|article|nav|header|footer|main|aside|img|link|meta|script|style|noscript|g|path")
_HTML_IMG = re.compile(r"<(?:img|source|iframe|video|audio|embed|object|link|meta|path)\b[^>]*>", re.I)
_HTML_TAG = re.compile(r"</?(?:%s)\b[^>]*>" % _HTML_TAGS, re.I)
_HTML_BR = re.compile(r"<br\s*/?>", re.I)
_AUTOLINK = re.compile(r"<((?:https?|ftp|mailto):[^>\s]+)>")
_LINK = re.compile(r"\[((?:[^\[\]]|\[[^\[\]]*\])*)\]\((?:<[^>]*>|(?:[^()\s]|\((?:[^()\s]|\([^()]*\))*\))*)"
                   r"(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)")
_REF_LINK = re.compile(r"\[([^\[\]]+)\]\[[^\[\]]*\]")
_REF_DEF = re.compile(r"^\s{0,3}\[(?!\^)[^\]]+\]:\s*\S+(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*$")
_ATX = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)(?:\s+#+\s*)?$")
_MD_LIST = re.compile(r"^\s*(?:[-*+]|\d{1,3}[.)])\s+")
_MD_TABLE = re.compile(r"^\s*\|")


def _strip_inline(line: str) -> str:
    """Remove badges, images, HTML tags and link URLs from one markdown line (code spans untouched)."""
    pieces = []
    last = 0
    for m in _CODE_SPAN.finditer(line):
        pieces.append((False, line[last:m.start()]))
        pieces.append((True, m.group(0)))
        last = m.end()
    pieces.append((False, line[last:]))
    out = []
    for is_code, seg in pieces:
        if is_code:
            out.append(seg)
            continue
        seg = _BADGE_LINK.sub("", seg)
        seg = _BADGE_REF.sub("", seg)
        seg = _IMAGE.sub("", seg)
        seg = _HTML_BR.sub(" ", seg)
        seg = _HTML_IMG.sub("", seg)
        seg = _AUTOLINK.sub(r"\1", seg)
        seg = _HTML_TAG.sub("", seg)
        for _ in range(3):
            new = _LINK.sub(lambda m: m.group(1), seg)
            if new == seg:
                break
            seg = new
        seg = _REF_LINK.sub(lambda m: m.group(1), seg)
        if "&" in seg:
            seg = _ENTITY.sub(lambda m: html.unescape(m.group(0)).replace("\u00a0", " "), seg)
        out.append(seg)
    return "".join(out)


@dataclass
class _Seg:
    kind: str           # heading | para | list | table | code | meta | blank
    lines: List[str]


def _md_regions(text: str):
    """Split markdown into (is_code, lines) regions on fenced code blocks."""
    regions = []
    cur: List[str] = []
    fence = None
    for line in text.split("\n"):
        m = _FENCE.match(line)
        if fence is None:
            if m:
                if cur:
                    regions.append((False, cur))
                cur = [line]
                fence = m.group(1)[0] * 3, len(m.group(1))
            else:
                cur.append(line)
        else:
            cur.append(line)
            if m and m.group(1)[0] == fence[0][0] and len(m.group(1)) >= fence[1] \
                    and line.strip().strip(fence[0][0]) == "":
                regions.append((True, cur))
                cur = []
                fence = None
    if cur:
        regions.append((fence is not None, cur))
    return regions


def markdown_segments(text: str) -> List[_Seg]:
    """Parse markdown into cleaned segments (level-3 view: no badges, comments, HTML or link URLs)."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    segs: List[_Seg] = []
    lines_all = text.split("\n")
    start = 0
    # YAML front matter
    if lines_all and lines_all[0].strip() == "---":
        for j in range(1, min(len(lines_all), 60)):
            if lines_all[j].strip() in ("---", "..."):
                segs.append(_Seg("meta", [l.rstrip() for l in lines_all[:j + 1]]))
                start = j + 1
                break
    body = "\n".join(lines_all[start:])
    for is_code, lines in _md_regions(body):
        if is_code or (lines and _FENCE.match(lines[0])):
            segs.append(_Seg("code", [l.rstrip() for l in lines]))
            continue
        chunk = _HTML_COMMENT.sub("", "\n".join(lines))
        chunk = re.sub(r"<!--.*\Z", "", chunk, flags=re.S)  # unterminated comment
        raw_lines = chunk.split("\n")
        for idx, raw in enumerate(raw_lines):
            if not raw.strip():
                segs.append(_Seg("blank", [""]))
                continue
            if _REF_DEF.match(raw):
                continue
            line = _strip_inline(raw)
            if _MD_TABLE.match(raw):
                line = re.sub(r" {2,}", " ", line.rstrip())
                segs.append(_Seg("table", [line]))
                continue
            line = line.rstrip()
            if not line.strip():
                continue  # image / badge / html-only line
            if line != raw.rstrip() and not _MD_LIST.match(line):
                line = line.lstrip()  # leftover indentation of removed HTML
            m = _ATX.match(line)
            if m:
                if not m.group(2).strip():
                    continue
                segs.append(_Seg("heading", [f"{m.group(1)} {m.group(2).strip()}"]))
            elif re.fullmatch(r"\s{0,3}(?:=+|-{2,})\s*", line) and segs and segs[-1].kind == "para" \
                    and len(segs[-1].lines) == 1:
                level = 1 if "=" in line else 2
                segs[-1] = _Seg("heading", ["#" * level + " " + segs[-1].lines[0].strip()])
            elif _MD_LIST.match(line):
                if re.fullmatch(r"\s*(?:[-*+]|\d{1,3}[.)])\s*", line):
                    continue
                segs.append(_Seg("list", [line]))
            elif line[:1] in (" ", "\t") and segs and segs[-1].kind in ("list", "para") and segs[-1].lines[-1].strip():
                segs[-1].lines.append(line)
            elif segs and segs[-1].kind == "para" and segs[-1].lines[-1].strip():
                segs[-1].lines.append(line)
            else:
                segs.append(_Seg("para", [line]))
    return segs


def _collapse_blank(lines: List[str]) -> str:
    out: List[str] = []
    for l in lines:
        if not l.strip():
            if out and out[-1] != "":
                out.append("")
        else:
            out.append(l)
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out)


def _list_text(lines: List[str]) -> str:
    return " ".join(l.strip() for l in lines)


def markdown_level(text: str, level: int) -> str:
    """Markdown source at detail level 1-4."""
    if level >= 4:
        return _collapse_blank([l.rstrip() for l in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")])
    segs = markdown_segments(text)

    def render(lv: int) -> str:
        if lv >= 3:
            flat: List[str] = []
            for s in segs:
                if s.kind == "blank":
                    flat.append("")
                else:
                    flat.extend(s.lines)
            return _collapse_blank(flat)
        out: List[str] = []
        prev_list = False
        has_heading = any(s.kind == "heading" for s in segs)
        got_para = False
        for s in segs:
            if s.kind == "heading":
                out.append(s.lines[0])
                prev_list = False
            elif s.kind == "para":
                prev_list = False
                if lv == 2:
                    out.append(first_sentence(_list_text(s.lines)))
                elif not has_heading and not got_para:
                    out.append(first_sentence(_list_text(s.lines), 200))
                    got_para = True
            elif s.kind == "list":
                if lv == 2 and not prev_list:
                    mm = _MD_LIST.match(s.lines[0])
                    head = mm.group(0) if mm else "- "
                    out.append(head + first_sentence(s.lines[0][len(head):].strip(), 200))
                prev_list = True
            elif s.kind != "blank":
                prev_list = False
        return "\n\n".join(out)

    # level 1/2: blank-line separated chunks
    return levels_output(render, level)
