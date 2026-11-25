"""
token_shredder - Test HTML Converter
"""
import pytest
from token_shredder.converters.html_converter import HTMLConverter
from token_shredder.models import ConversionOptions


def test_html_converter_instantiation():
    converter = HTMLConverter()
    assert converter is not None


def test_html_converter_extensions():
    assert '.html' in HTMLConverter.get_supported_extensions()


HTML = """<html><head><title>T</title><script>x()</script></head><body>
<nav><a href="/">Home</a></nav>
<h1>Intro</h1><p>First <b>para</b> with a <a href="https://e.com/x">link</a>.<sup>[1]</sup></p>
<p>Text <!-- hidden comment --> more</p>
<h2>Data</h2><ul><li>one<ul><li>nested</li></ul></li><li>two</li></ul>
<table><tr><th>k</th><th>v</th></tr><tr><td>a</td><td>1</td></tr></table>
<footer>footer text</footer></body></html>"""


def _convert(tmp_path, level):
    from token_shredder.models import ConversionOptions
    f = tmp_path / "p.html"
    f.write_text(HTML)
    return HTMLConverter().convert_to_markdown(str(f), ConversionOptions(detail_level=level))


def test_html_keeps_document_order(tmp_path):
    md = _convert(tmp_path, 3)
    assert md.index("# Intro") < md.index("First para") < md.index("## Data") < md.index("- one")
    assert "  - nested" in md and "| a | 1 |" in md
    for gone in ("x()", "Home", "footer text", "hidden comment", "[1]", "https://e.com/x"):
        assert gone not in md


def test_html_levels(tmp_path):
    l1, l2, l4 = (_convert(tmp_path, n) for n in (1, 2, 4))
    assert "# Intro" in l1 and "First" not in l1
    assert "First para" in l2 and "| a |" not in l2
    assert "[link](https://e.com/x)" in l4
