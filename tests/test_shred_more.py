"""Tighter output without losing the public API or main content (corpus tuning, 2026-11-25)."""
from token_shredder.converters.code_converter import CodeConverter
from token_shredder.converters.html_converter import HTMLConverter
from token_shredder.main import convert_file
from token_shredder.models import ConversionOptions


def _md(path, level=3):
    return convert_file(str(path), detail_level=level, show_metrics=False, cache_enabled=False,
                        write_output=False).markdown


def _outline(tmp_path, name, code, level=3):
    f = tmp_path / name
    f.write_text(code)
    return CodeConverter().convert_to_markdown(str(f), ConversionOptions(detail_level=level))


PY = '''
def public(a):
    """Do the public thing. More detail that only level 4 shows."""

def _helper(b):
    """Internal helper."""

class Api:
    def __init__(self, x):
        """Create it."""
    def run(self):
        """Run it."""
    def _internal(self):
        """Hidden."""
    def __repr__(self):
        return "Api"
'''


def test_python_private_members(tmp_path):
    l2, l3, l4 = (_outline(tmp_path, "m.py", PY, lv) for lv in (2, 3, 4))
    assert "_helper" not in l2 and "_internal" not in l2 and "__repr__" not in l2
    assert "__init__" in l2 and "run" in l2
    assert "_helper" in l3 and "Internal helper." not in l3   # signature only
    assert "Do the public thing." in l3 and "More detail" not in l3  # first sentence
    assert "Internal helper." in l4 and "More detail" in l4


def test_javadoc_markup_and_repeated_docs(tmp_path):
    java = ("public class A {\n"
            "  /** Assert that {@code x} is <em>true</em>. <p>More.</p> */\n"
            "  public static void ok(@Nullable String m) {\n  }\n"
            "  /** Assert that {@code x} is <em>true</em>. <p>More.</p> */\n"
            "  public static void ok(@Nullable String m, int n) {\n  }\n"
            "  private void hidden() {\n  }\n}\n")
    out = _outline(tmp_path, "A.java", java)
    assert "// Assert that x is true." in out and out.count("Assert that") == 1
    assert "static void ok(String m)" in out and "@Nullable" not in out
    assert "hidden" in out
    assert "hidden" not in _outline(tmp_path, "A.java", java, 2)
    assert "static void ok (x2)" in _outline(tmp_path, "A.java", java, 1)


def test_go_and_rust_private(tmp_path):
    go = "func Public() {\n}\nfunc private() {\n}\ntype hidden struct {\n}\n"
    assert "private" not in _outline(tmp_path, "a.go", go, 2)
    rs = "pub fn open() {\n}\nfn helper() {\n}\n"
    assert "helper" not in _outline(tmp_path, "a.rs", rs, 2) and "pub fn open" in _outline(tmp_path, "a.rs", rs, 2)


def test_minified_js(tmp_path):
    out = _outline(tmp_path, "x.min.js", "var a=1;" * 2000)
    assert "Minified" in out


def test_html_back_matter_dropped_at_3(tmp_path):
    html = ("<html><body><main><h1>Topic</h1>" + "<p>Main text here.</p>" * 30 +
            "<h2>See also</h2><ul><li>Other</li></ul><h2>References</h2><ol><li>Cite 1</li></ol>"
            "<h2>Later section</h2><p>Kept again.</p></main></body></html>")
    f = tmp_path / "p.html"
    f.write_text(html)
    l3 = HTMLConverter().convert_to_markdown(str(f), ConversionOptions(detail_level=3))
    l4 = HTMLConverter().convert_to_markdown(str(f), ConversionOptions(detail_level=4))
    assert "Cite 1" not in l3 and "Other" not in l3 and "Kept again." in l3
    assert "Cite 1" in l4


def test_summary_never_larger_than_file(tmp_path):
    f = tmp_path / "tiny.yaml"
    f.write_text("a: 1\n")
    outs = [_md(f, lv) for lv in range(1, 6)]
    assert all(len(o) <= len(outs[4]) for o in outs)
