"""--max-tokens, stdin, URLs, stdout/JSON output (v0.4 features)."""
import http.server
import io
import json
import threading

import pytest
from typer.testing import CliRunner

from token_shredder.main import app, batch_convert, convert_file
from token_shredder.metrics import TokenCounter
from token_shredder.sources import fetch_url, read_stdin, sniff_format

runner = CliRunner()
count = TokenCounter().estimate

PY = "\n".join(
    f'def func_{i}(a, b={i}):\n    """Function number {i} does a thing with a and b."""\n'
    f"    return a + b * {i}\n" for i in range(60)
)


def _conv(path, **kw):
    kw.setdefault("show_metrics", False)
    kw.setdefault("cache_enabled", False)
    kw.setdefault("write_output", False)
    return convert_file(str(path), **kw)


@pytest.mark.parametrize("budget", [60, 200, 800, 3000, 100000])
def test_max_tokens_is_respected(tmp_path, budget):
    src = tmp_path / "m.py"
    src.write_text(PY)
    r = _conv(src, max_tokens=budget)
    assert r.output_tokens <= budget
    assert count(r.markdown) <= budget


def test_max_tokens_picks_highest_fitting_level(tmp_path):
    src = tmp_path / "m.py"
    src.write_text(PY)
    sizes = {lv: _conv(src, detail_level=lv).output_tokens for lv in range(1, 6)}
    budget = sizes[2] + 5
    expected = max(lv for lv, n in sizes.items() if n <= budget)
    r = _conv(src, max_tokens=budget)
    assert r.detail_level == expected and not r.warnings
    assert _conv(src, max_tokens=100000).detail_level == 5
    assert _conv(src, max_tokens=100000, detail_level=2).detail_level == 2  # -d caps it


def test_truncation_is_marked(tmp_path):
    src = tmp_path / "m.py"
    src.write_text(PY)
    r = _conv(src, max_tokens=60)
    assert "truncated to fit" in r.markdown and r.warnings


def test_batch_budget_is_shared(tmp_path):
    for i in range(4):
        (tmp_path / f"m{i}.py").write_text(PY)
    (tmp_path / "small.txt").write_text("just a short note")
    results = batch_convert(str(tmp_path), max_tokens=2000, quiet=True, write_output=False,
                            cache_enabled=False)
    assert sum(r.output_tokens for r in results) <= 2000
    small = [r for r in results if r.source_file.endswith("small.txt")][0]
    assert "just a short note" in small.markdown  # small files are kept whole


def test_batch_combined_stdout(tmp_path):
    (tmp_path / "a.py").write_text(PY)
    (tmp_path / "b.txt").write_text("hello")
    res = runner.invoke(app, ["batch", str(tmp_path), "-o", "-", "-t", "1500", "-q", "--no-cache"])
    assert res.exit_code == 0
    assert '<file path="a.py"' in res.stdout and '<file path="b.txt"' in res.stdout
    assert count(res.stdout) <= 1500
    assert not list(tmp_path.glob("*.md"))  # nothing written in combined mode


def test_stdin_and_sniffing():
    assert sniff_format(b'  [{"a": 1}]') == "json"
    assert sniff_format(b'{"a":1}\n{"a":2}\n') == "jsonl"
    assert sniff_format(b"%PDF-1.7") == "pdf"
    assert sniff_format(b"<!DOCTYPE html><html>") == "html"
    assert sniff_format(b"plain words") == "txt"
    m = read_stdin(io.BytesIO(b'[{"name": "x", "n": 1}, {"name": "y", "n": 2}]'))
    try:
        assert m.format == "json" and m.name == "stdin"
    finally:
        m.cleanup()


def test_cli_stdin_to_stdout():
    res = runner.invoke(app, ["convert", "-", "-q"], input='[{"name": "x"}, {"name": "y"}]')
    assert res.exit_code == 0
    assert "name" in res.stdout


def test_cli_json_output(tmp_path):
    src = tmp_path / "a.py"
    src.write_text(PY)
    res = runner.invoke(app, ["convert", str(src), "--json", "-q", "--no-cache"])
    data = json.loads(res.stdout)
    assert data["format"] == "py" and data["detail_level"] == 3 and "func_1" in data["markdown"]


@pytest.fixture
def http_server(tmp_path):
    (tmp_path / "page.html").write_text(
        "<html><head><title>T</title></head><body><nav>Menu items</nav>"
        "<div class='cookie-banner'>Accept cookies</div><main><h1>Article</h1>"
        + "<p>Real article text that matters. </p>" * 20 + "</main>"
        "<div class='sidebar'>Sidebar junk</div></body></html>")
    (tmp_path / "data").write_text('[{"id": 1}, {"id": 2}]')

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(tmp_path), **kw)

        def log_message(self, *a):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()


def test_url_main_content(http_server):
    res = runner.invoke(app, ["convert", f"{http_server}/page.html", "-q"])
    assert res.exit_code == 0
    assert "Real article text" in res.stdout
    for junk in ("Menu items", "Accept cookies", "Sidebar junk"):
        assert junk not in res.stdout


def test_url_without_extension_is_sniffed(http_server):
    m = fetch_url(f"{http_server}/data")
    try:
        assert m.format == "json"
    finally:
        m.cleanup()


def test_bad_url_is_a_clean_error():
    res = runner.invoke(app, ["convert", "http://127.0.0.1:9/nothing", "-q"])
    assert res.exit_code == 1
