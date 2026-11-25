"""Prose clean-up and detail levels for TXT, Markdown, PDF, DOCX and PPTX."""
import pytest
from docx import Document
from pptx import Presentation

from token_shredder.main import convert_file
from token_shredder.prose import (
    first_sentence, markdown_level, prose_from_text, strip_running, build_blocks,
)

WRAPPED = (
    "The Transformer is a model architecture that relies entirely on an attention mechanism to draw\n"
    "global dependencies between input and output. It allows for significantly more parallelization\n"
    "and can reach a new state of the art in translation quality.\n"
)


WORDS = ['', 'alpha', 'bravo', 'charlie', 'delta', 'echo', 'foxtrot']


def _convert(path, level):
    return convert_file(str(path), detail_level=level, write_output=False,
                        show_metrics=False, cache_enabled=False).markdown


# --- clean-up -------------------------------------------------------------

def test_dehyphenates_split_word():
    text = ("This sentence is long enough to be a wrapped line of text, which ends with a trans-\n"
            "former and carries on with more words after it so the line is long enough.\n")
    out = prose_from_text(text, 3)
    assert "transformer" in out
    assert "trans-" not in out


def test_keeps_real_hyphen_when_document_uses_it():
    text = ("Self-attention is used in the decoder and the encoder of this model, and we call it self-\n"
            "attention everywhere in this long wrapped line of text for a total of many characters.\n")
    out = prose_from_text(text, 3)
    assert "self-attention" in out.lower()
    assert "selfattention" not in out.lower()


def test_keeps_hyphen_before_capital_or_digit():
    out = prose_from_text("The long line goes on and on until it ends in a hyphen to be kept for English-\nto-German work.\n", 3)
    assert "English-to-German" in out


def test_joins_hard_wrapped_lines():
    out = prose_from_text(WRAPPED, 3)
    assert out.count("\n") == 0
    assert "output. It allows" in out


def test_does_not_join_lists_headings_or_code():
    text = (
        "1. Introduction\n\n"
        "Some words here that explain what follows and go on for quite a while, until the line ends\n"
        "and wraps around to the next line.\n\n"
        "- first item that is quite long and goes on for a good while with many words in it, really\n"
        "- second item\n"
        "- third item\n\n"
        "2. Method\n\n"
        "Text before the code example, which is introduced like this:\n\n"
        "      def f(x):\n"
        "          return x + 1\n"
    )
    out = prose_from_text(text, 3)
    lines = out.splitlines()
    assert "## 1. Introduction" in lines
    assert "## 2. Method" in lines
    assert "- second item" in lines and "- third item" in lines
    assert any(l.startswith("- first item") for l in lines)
    assert "def f(x):\n    return x + 1" in out


def test_collapses_spaces_and_form_feeds():
    out = prose_from_text("Word   with    many     spaces\x0c and  a form feed.\n", 3)
    assert "  " not in out and "\x0c" not in out


def test_removes_running_headers_footers_and_page_numbers():
    pages = []
    for n in range(1, 6):
        pages.append([
            f"RFC 9110   HTTP Semantics   June 2022",
            f"This is body line one of page {WORDS[n]} which is a sentence of reasonable length",
            f"and body line two of page {WORDS[n]}.",
            f"Fielding & Reschke   Standards Track   [Page {n}]",
            str(n),
        ])
    entries = strip_running(pages)
    kept = [e for e in entries if isinstance(e, str)]
    assert not any("RFC 9110" in l or "[Page" in l for l in kept)
    assert "3" not in kept  # lone page number
    assert sum("body line one" in l for l in kept) == 5


def test_running_header_removed_from_text_file(tmp_path):
    parts = []
    for n in range(1, 5):
        parts.append(f"Network Working Group  Standards Track  [Page {n}]\n\nBody text of page {WORDS[n]} goes here.\n")
    f = tmp_path / "x.txt"
    f.write_text("\f".join(parts))
    out = _convert(f, 3)
    assert "Standards Track" not in out
    assert "Body text of page charlie" in out


def test_txt_has_no_path_heading(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("Hello world.\n")
    assert str(tmp_path) not in _convert(f, 3)


def test_non_utf8_text_and_missing_file(tmp_path):
    f = tmp_path / "b.txt"
    f.write_bytes(b"caf\xe9 au lait is a drink.\n")
    assert "au lait" in _convert(f, 3)


# --- level semantics ------------------------------------------------------

RFC_LIKE = (
    "Title of the Document\n\n"
    "1. Introduction\n\n"
    "   This document is about things. It has a second sentence that matters less to a quick\n"
    "   reader who only wants the gist of it.\n\n"
    "   A second paragraph follows. With more detail.\n\n"
    "2. Details\n\n"
    "2.1. Sub Details\n\n"
    "   Details are explained here. In many words, over many lines, for the benefit of all\n"
    "   readers who have the patience to read them.\n"
)


def test_text_levels(tmp_path):
    f = tmp_path / "doc.txt"
    f.write_text(RFC_LIKE)
    l1, l2, l3, l4, l5 = (_convert(f, lv) for lv in range(1, 6))
    assert "1. Introduction" in l1 and "2.1. Sub Details" in l1
    assert "This document is about things" not in l1
    assert "This document is about things." in l2
    assert "second sentence" not in l2
    assert "second sentence" in l3 and "A second paragraph follows. With more detail." in l3
    assert l5 == RFC_LIKE
    sizes = [len(x) for x in (l1, l2, l3, l4, l5)]
    assert sizes == sorted(sizes)


def test_first_sentence_skips_abbreviations():
    assert first_sentence("See Fig. 3 for details, e.g. the plot. Then more.") == "See Fig. 3 for details, e.g. the plot."
    assert first_sentence("J. Smith wrote this. Next.") == "J. Smith wrote this."


def test_toc_dropped_at_level_3_kept_at_4(tmp_path):
    f = tmp_path / "toc.txt"
    f.write_text(
        "Table of Contents\n\n   1. Alpha\n   2. Beta\n   3. Gamma\n   4. Delta\n\n"
        "1. Alpha\n\n   Text of alpha, which is long enough to be a paragraph on its own.\n\n"
        "2. Beta\n\n   Text of beta.\n\n3. Gamma\n\n   Text of gamma.\n\n4. Delta\n\n   Text of delta.\n")
    assert "   1. Alpha" not in _convert(f, 3) and "- 1." not in _convert(f, 3)
    l3 = _convert(f, 3)
    assert l3.count("Alpha") == 1
    assert _convert(f, 4).count("Alpha") == 2


# --- markdown -------------------------------------------------------------

MD = """# Project

[![Build](https://img.shields.io/b.svg)](https://ci.example.com)
![logo](logo.png)

<!-- hidden
comment -->
<p align="center"><b>Bold</b> text with <a href="https://x.y">a link</a></p>

See [the docs](https://example.com/docs "Docs") and [ref link][r1].

[r1]: https://example.com/ref

```
[keep](https://example.com) <b>inside</b> code
```

| a | b |
|---|---|
| [x](https://x.example) | 2 |

- [Awesome Tool](https://github.com/a/b) - does things
- [Other](https://github.com/c/d) - more things
"""


def test_markdown_levels_1_to_3():
    l3 = markdown_level(MD, 3)
    assert "img.shields.io" not in l3 and "logo" not in l3
    assert "hidden" not in l3 and "<p" not in l3 and "<b>Bold" not in l3
    assert "Bold text with a link" in l3
    assert "See the docs and ref link." in l3
    assert "[r1]:" not in l3
    assert "[keep](https://example.com) <b>inside</b> code" in l3  # code untouched
    assert "| x | 2 |" in l3 and "|---|---|" in l3
    assert "- Awesome Tool - does things" in l3
    assert "github.com" not in l3
    l1, l2 = markdown_level(MD, 1), markdown_level(MD, 2)
    assert l1.strip() == "# Project"
    assert "See the docs and ref link." in l2
    assert len(l1) <= len(l2) <= len(l3) <= len(markdown_level(MD, 4))


def test_markdown_level_4_keeps_urls(tmp_path):
    f = tmp_path / "r.md"
    f.write_text(MD)
    assert "https://example.com/docs" in _convert(f, 4)
    assert _convert(f, 5) == MD
    sizes = [len(_convert(f, lv)) for lv in range(1, 6)]
    assert sizes == sorted(sizes)


def test_markdown_awesome_list_shrinks():
    items = "\n".join(f"- [Tool {i}](https://github.com/org/tool-{i}) - A tool number {i}." for i in range(50))
    src = "# Awesome\n\n## Tools\n\n" + items + "\n"
    out = markdown_level(src, 3)
    assert len(out) < 0.6 * len(src)
    for i in range(50):
        assert f"Tool {i} - A tool number {i}." in out


def test_markdown_setext_and_generics():
    out = markdown_level("Title\n=====\n\nUse List<String> and Map<K, V> here.\n", 3)
    assert out.startswith("# Title")
    assert "List<String>" in out and "Map<K, V>" in out


# --- DOCX / PPTX ----------------------------------------------------------

@pytest.fixture
def docx_file(tmp_path):
    d = Document()
    d.add_heading("Report Title", 0)
    d.add_heading("Intro", 1)
    d.add_paragraph("First sentence of intro.   Second   sentence of intro.")
    d.add_heading("Details", 2)
    d.add_paragraph("Only sentence here is quite long, though.")
    d.add_paragraph("item one", style="List Bullet")
    t = d.add_table(rows=2, cols=2)
    t.cell(0, 0).text = "H1"
    t.cell(0, 1).text = "H2"
    t.cell(1, 0).text = "a"
    t.cell(1, 1).text = "b"
    p = tmp_path / "r.docx"
    d.save(p)
    return p


def test_docx_levels(docx_file):
    outs = [_convert(docx_file, lv) for lv in range(1, 6)]
    l1, l2, l3 = outs[:3]
    assert "# Report Title" in l1 and "## Details" in l1 or "# Intro" in l1
    assert "First sentence" not in l1
    assert "First sentence of intro." in l2 and "Second sentence" not in l2
    assert "Second sentence of intro." in l3 and "| H1 | H2 |" in l3
    sizes = [len(o) for o in outs]
    assert sizes == sorted(sizes)


@pytest.fixture
def pptx_file(tmp_path):
    prs = Presentation()
    s = prs.slides.add_slide(prs.slide_layouts[1])
    s.shapes.title.text = "Roadmap"
    s.placeholders[1].text = "First point. More detail.\nSecond point"
    s.notes_slide.notes_text_frame.text = "Say hello"
    prs.slides.add_slide(prs.slide_layouts[5]).shapes.title.text = "Wrap up"
    p = tmp_path / "d.pptx"
    prs.save(p)
    return p


def test_pptx_levels(pptx_file):
    outs = [_convert(pptx_file, lv) for lv in range(1, 6)]
    l1, l2, l3, l4, _ = outs
    assert "Roadmap" in l1 and "Wrap up" in l1 and "First point" not in l1
    assert "First point." in l2 and "More detail" not in l2
    assert "Second point" in l3 and "Say hello" not in l3
    assert "Say hello" in l4
    sizes = [len(o) for o in outs]
    assert sizes == sorted(sizes)


# --- PDF ------------------------------------------------------------------

def _make_pdf(path, pages):
    """Tiny text-only PDF with one Helvetica text object per line."""
    objs = []
    kids = []
    for i, lines in enumerate(pages):
        content = "BT /F1 11 Tf 14 TL 50 750 Td " + " ".join(
            f"({l.replace('(', '[').replace(')', ']')}) Tj T*" for l in lines) + " ET"
        objs.append((f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {4 + 2 * i} 0 R "
                     f"/Resources << /Font << /F1 3 0 R >> >> >>"))
        objs.append(f"<< /Length {len(content)} >>\nstream\n{content}\nendstream")
        kids.append(f"{3 + 2 * i + 1} 0 R")
    body = ["<< /Type /Catalog /Pages 2 0 R >>",
            f"<< /Type /Pages /Kids [{' '.join(k for k in kids)}] /Count {len(pages)} >>",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    # page objects at 4,6,..; content streams at 5,7,..
    flat = []
    for i in range(len(pages)):
        flat.append(objs[2 * i].replace(f"/Contents {4 + 2 * i} 0 R", f"/Contents {5 + 2 * i} 0 R"))
        flat.append(objs[2 * i + 1])
    body += flat
    kids2 = [f"{4 + 2 * i} 0 R" for i in range(len(pages))]
    body[1] = f"<< /Type /Pages /Kids [{' '.join(kids2)}] /Count {len(pages)} >>"
    out = b"%PDF-1.4\n"
    offsets = []
    for n, o in enumerate(body, 1):
        offsets.append(len(out))
        out += f"{n} 0 obj\n{o}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(body) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(body) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    path.write_bytes(out)


def test_pdf_cleanup_and_levels(tmp_path):
    pages = []
    for n in range(1, 5):
        pages.append([
            "Journal of Tests 2024",
            f"{n} Section About {WORDS[n].title()}" if n > 1 else "1 Introduction",
            f"This body line number {WORDS[n]} is long enough to be wrapped by a typesetter and it ends with a trans-",
            f"former that was split. And the next line {WORDS[n]} starts a new sentence in the same paragraph.",
            f"Page {n}",
        ])
    f = tmp_path / "p.pdf"
    _make_pdf(f, pages)
    outs = [_convert(f, lv) for lv in range(1, 6)]
    l1, l2, l3, l4, l5 = outs
    assert "Journal of Tests" not in l3 and "Journal of Tests" in l5
    assert "transformer" in l3 and "trans-" in l5
    assert "## Page 1" not in l3 and "## Page 1" in l4
    assert "## 1 Introduction" in l1 and "## 2 Section About Bravo" in l1
    assert "transformer" not in l1
    sizes = [len(o) for o in outs]
    assert sizes == sorted(sizes), sizes


def test_pdf_error_is_reported(tmp_path):
    from token_shredder.converters.pdf_converter import PDFConverter
    from token_shredder.models import ConversionOptions
    f = tmp_path / "bad.pdf"
    f.write_bytes(b"not a pdf")
    out = PDFConverter().convert_to_markdown(str(f), ConversionOptions(detail_level=3))
    assert out.startswith("[Error")


def test_headings_detected_in_blocks():
    lines = ["3.2 Scaled Dot-Product Attention", "We call our attention function the thing.", "x"]
    blocks = build_blocks(strip_running([lines]))
    assert blocks[0].kind == "heading" and blocks[0].level == 3
