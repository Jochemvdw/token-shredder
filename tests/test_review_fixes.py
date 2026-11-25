"""Regression tests for the pre-release review (2026-11-25)."""
import pytest
from typer.testing import CliRunner

from token_shredder.main import ConversionError, app, batch_convert, convert_file
from token_shredder.models import ConversionOptions
from token_shredder.converters.code_converter import CodeConverter

runner = CliRunner()


def _conv(path, **kw):
    kw.setdefault("show_metrics", False)
    kw.setdefault("cache_enabled", False)
    return convert_file(str(path), **kw)


def test_markdown_input_is_never_overwritten(tmp_path):
    src = tmp_path / "notes.md"
    original = "# Notes\n\n- a\n- b\n\n| x | y |\n|---|---|\n| 1 | 2 |\n"
    src.write_text(original)
    r = _conv(src)
    assert src.read_text() == original
    assert r.target_file.endswith("notes.shredded.md")
    assert "- b\n\n| x | y |" in r.markdown
    with pytest.raises(ConversionError):
        _conv(src, output_path=str(src))


def test_cache_key_includes_format(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    body = 'def f():\n    """Doc."""\n    return 1\n'
    (tmp_path / "c1.py").write_text(body)
    (tmp_path / "c2.txt").write_text(body)
    _conv(tmp_path / "c1.py", cache_enabled=True)
    r = _conv(tmp_path / "c2.txt", cache_enabled=True)
    assert "return 1" in r.markdown


@pytest.mark.parametrize("name,content", [("bad.json", "{not json"), ("empty.json", "")])
def test_conversion_errors_exit_nonzero_and_write_nothing(tmp_path, name, content):
    src = tmp_path / name
    src.write_text(content)
    result = runner.invoke(app, ["convert", str(src), "--no-cache"])
    assert result.exit_code == 1
    assert not (tmp_path / (src.stem + ".md")).exists()


def test_non_utf8_text_is_converted(tmp_path):
    src = tmp_path / "latin.txt"
    src.write_bytes("café au lait\n".encode("latin-1"))
    r = _conv(src)
    assert "caf" in r.markdown and "lait" in r.markdown


def test_output_dir_is_created(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("hello")
    _conv(src, output_path=str(tmp_path / "new" / "dir" / "a.md"))
    assert (tmp_path / "new" / "dir" / "a.md").exists()


def test_batch_no_collisions_recursive_and_case_insensitive(tmp_path):
    d = tmp_path / "in"
    (d / "sub").mkdir(parents=True)
    (d / "a.py").write_text("def a():\n    pass\n")
    (d / "a.txt").write_text("text a")
    (d / "B.PY").write_text("def b():\n    pass\n")
    (d / "sub" / "deep.rs").write_text("fn deep() {}\n")
    results = batch_convert(str(d), output_dir=str(tmp_path / "out"), quiet=True)
    outs = sorted(p.relative_to(tmp_path / "out").as_posix() for p in (tmp_path / "out").rglob("*.md"))
    assert outs == ["B.PY.md", "a.py.md", "a.txt.md", "sub/deep.rs.md"]
    assert len(results) == 4
    # A second run next to the sources must not pick up its own output.
    batch_convert(str(d), quiet=True)
    batch_convert(str(d), quiet=True)
    assert not list(d.rglob("*.md.md"))


def test_batch_reports_failures(tmp_path):
    d = tmp_path / "in"
    d.mkdir()
    (d / "ok.txt").write_text("fine")
    (d / "bad.json").write_text("{nope")
    result = runner.invoke(app, ["batch", str(d), "-q"])
    assert result.exit_code == 1


def _outline(tmp_path, name, code, level=3):
    f = tmp_path / name
    f.write_text(code)
    return CodeConverter().convert_to_markdown(str(f), ConversionOptions(detail_level=level))


def test_ts_go_rust_outlines(tmp_path):
    ts = _outline(tmp_path, "s.ts", (
        "export class UserService {\n  constructor(private repo: Repo) {\n  }\n"
        "  async find(id: string): Promise<User> {\n    if (x) {\n    }\n  }\n}\n"
        "export const handler: Handler = async (req, res) => {\n};\n"))
    for name in ("class UserService", "constructor", "async find", "handler"):
        assert name in ts
    assert "if (x)" not in ts
    go = _outline(tmp_path, "s.go", (
        "type Server struct {\n}\n// Handle serves.\nfunc (s *Server) Handle(w W) {\n}\n"), level=1)
    assert "type Server struct" in go and "func (s *Server) Handle" in go
    rs = _outline(tmp_path, "s.rs", "/// Adds.\npub fn add(a: i32) -> i32 {\n}\n")
    assert "// Adds." in rs and "pub fn add" in rs


def test_python_decorators_kept(tmp_path):
    py = _outline(tmp_path, "p.py", "class A:\n    @property\n    def x(self):\n        return 1\n", 2)
    assert "@property def x(self)" in py


def test_api_convert_and_limits(tmp_path):
    from fastapi.testclient import TestClient
    from token_shredder.api import app as api

    client = TestClient(api)
    ok = client.post("/convert", files={"file": ("x.json", b'{"a": 1}')}, params={"detail_level": 5})
    assert ok.status_code == 200
    body = ok.json()
    assert body["source_file"] == "x.json" and '{"a": 1}' in body["markdown"]
    assert "/tmp" not in str(body) and "/var" not in str(body)
    assert client.post("/convert", files={"file": ("x.json", b"{bad")}).status_code == 422
    assert client.post("/convert", files={"file": ("x.json", b"{}")},
                       params={"detail_level": 99}).status_code == 422
