"""PDF heading detection from typography (font size / bold), no bookmarks."""
from token_shredder.converters.pdf_converter import (
    PDFConverter, _RunCollector, collect_lines, rank_typography_headings)
from token_shredder.models import ConversionOptions

BODY = "This is an ordinary body sentence that is long enough to dominate the character count."


def _page(*specs):
    return [(t, s, b) for t, s, b in specs]


def test_rank_sizes_into_levels():
    pages = [_page(("Big Title", 24, False), ("Overview", 16, False), (BODY, 10, False), (BODY, 10, False)),
             _page(("Details", 13, False), (BODY, 10, False), ("Overview", 16, False), (BODY, 10, False)),
             _page(("Methods", 16, False), (BODY, 10, False), ("Setup", 13, False), (BODY, 10, False))]
    r = rank_typography_headings(pages)
    assert r["overview"] == 0 and r["methods"] == 0
    assert r["details"] == 1 and r["setup"] == 1
    assert "bigtitle" not in r  # lone top size on page 1 is the title


def test_bold_short_lines_and_sentences():
    pages = [_page((BODY, 10, False)) * 5 + _page(("Results", 10, True), ("Bold sentence ends here.", 10, True))]
    r = rank_typography_headings(pages)
    assert "results" in r and "boldsentenceendshere" not in r


def test_unusable_sizes_fall_back():
    assert rank_typography_headings([_page(("Heading", 1, False), (BODY, 1, False))]) == {}
    assert rank_typography_headings([[]]) == {}


def test_collector_scales_size_by_matrices():
    c = _RunCollector()
    ident = [1, 0, 0, 1, 0, 0]
    c("Heading", [12, 0, 0, 12, 0, 700], [1, 0, 0, 1, 0, 0], {"/BaseFont": "/Arial-BoldMT"}, 1)
    c("body", ident, [1, 0, 0, 1, 0, 600], {"/BaseFont": "/Arial"}, 10)
    (t1, s1, b1), (t2, s2, b2) = collect_lines(c)
    assert (t1, s1, b1) == ("Heading", 12, True) and (t2, s2, b2) == ("body", 10, False)


def _pdf(path, lines):
    """lines: (text, size, font) with font F1 Helvetica / F2 Helvetica-Bold."""
    ops, y = [], 760
    for text, size, font in lines:
        ops.append(f"BT /{font} {size} Tf 50 {y} Td ({text}) Tj ET")
        y -= size + 8
    stream = "\n".join(ops).encode()
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << "
            b"/F1 5 0 R /F2 6 0 R >> >> >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"]
    out, offs = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    x = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offs)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (len(objs) + 1, x)
    path.write_bytes(out)


def test_pdf_end_to_end_typography(tmp_path):
    body = "Body text line number %d is plain prose and continues for a while, see the notes."
    lines = [("Annual Report", 22, "F2"), ("Jane Doe and John Smith", 10, "F1")]
    lines += [("Market Overview", 16, "F2")] + [(body % i, 10, "F1") for i in range(3)]
    lines += [("Regional Detail", 13, "F2")] + [(body % i, 10, "F1") for i in range(3, 6)]
    f = tmp_path / "t.pdf"
    _pdf(f, lines)
    md = PDFConverter().convert_to_markdown(str(f), ConversionOptions(detail_level=1))
    assert "Market Overview" in md and "Regional Detail" in md
    assert "Body text line" not in md
    # loose Title-Case heuristic is off when typography exists: author line is not a heading
    assert "Jane Doe" not in md
