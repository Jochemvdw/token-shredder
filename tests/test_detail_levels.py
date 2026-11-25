"""Detail levels mean the same thing for every format: 1 = smallest, 5 = full content."""
import json

import pytest
from typer.testing import CliRunner

from token_shredder.main import app, convert_file

PY = '''"""Module doc."""
import os


class UserService(Base):
    """Manage users.

    Longer explanation that only level 4 shows.
    """

    def authenticate(self, name: str, password: str) -> bool:
        """Check a login."""
        return name == "x" and password == os.environ.get("PW")


def helper(a, b=2):
    """Add things."""
    return a + b
'''

JS = '''/**
 * Route a request.
 * @param req the request
 */
function route(req, res) {
  return handle(req, res);
}

const add = (a, b) => a + b;

class Router {
  use(fn) { this.fns.push(fn); }
}
'''

DATA = [{"id": i, "name": f"user{i}", "tags": ["a", "b"], "bio": "x" * 60} for i in range(20)]


def _sizes(path, tmp_path):
    out = []
    for level in range(1, 6):
        r = convert_file(str(path), output_path=str(tmp_path / f"o{level}.md"), detail_level=level,
                         show_metrics=False, cache_enabled=False)
        out.append(r.markdown)
    return out


@pytest.mark.parametrize("name,content", [("svc.py", PY), ("router.js", JS),
                                          ("data.json", json.dumps(DATA, indent=2))])
def test_higher_level_never_gives_less(tmp_path, name, content):
    src = tmp_path / name
    src.write_text(content)
    outputs = _sizes(src, tmp_path)
    lengths = [len(o) for o in outputs]
    assert lengths == sorted(lengths), lengths
    assert all(o.strip() for o in outputs), "no level may produce empty output"
    # Level 5 is the file itself.
    assert content.strip() in outputs[4]


def test_python_levels_content(tmp_path):
    src = tmp_path / "svc.py"
    src.write_text(PY)
    l1, l2, l3, l4, _ = _sizes(src, tmp_path)
    assert "UserService" in l1 and "authenticate" in l1 and "helper" in l1
    assert "name: str" not in l1 and "name: str" in l2
    assert "Check a login." not in l2 and "Check a login." in l3
    assert "only level 4" not in l3 and "only level 4" in l4


def test_json_level4_is_lossless(tmp_path):
    src = tmp_path / "data.json"
    src.write_text(json.dumps(DATA, indent=2))
    r = convert_file(str(src), output_path=str(tmp_path / "o.md"), detail_level=4,
                     show_metrics=False, cache_enabled=False)
    body = r.markdown.split("\n", 1)[1].rsplit("```", 1)[0]
    assert json.loads(body) == DATA


def test_dedup_keeps_similar_but_different_lines(tmp_path):
    src = tmp_path / "d.json"
    src.write_text(json.dumps({"comments_url": "https://x/comments", "events_url": "https://x/events"}))
    r = convert_file(str(src), output_path=str(tmp_path / "o.md"), detail_level=2,
                     show_metrics=False, cache_enabled=False)
    assert "events_url" in r.markdown and "comments_url" in r.markdown


def test_invalid_level_rejected(tmp_path):
    src = tmp_path / "a.txt"
    src.write_text("hi")
    with pytest.raises(ValueError):
        convert_file(str(src), detail_level=0, show_metrics=False)
    result = CliRunner().invoke(app, ["convert", str(src), "-d", "6"])
    assert result.exit_code != 0


def test_quiet_prints_nothing(tmp_path):
    src = tmp_path / "svc.py"
    src.write_text(PY)
    runner = CliRunner()
    result = runner.invoke(app, ["convert", str(src), "-q", "--no-cache", "-o", str(tmp_path / "o.md")])
    assert result.exit_code == 0
    assert result.output == ""
    assert (tmp_path / "o.md").exists()


def test_report_compares_with_original_file(tmp_path):
    src = tmp_path / "svc.py"
    src.write_text(PY)
    r = convert_file(str(src), output_path=str(tmp_path / "o.md"), show_metrics=False,
                     cache_enabled=False)
    from token_shredder.metrics import TokenCounter
    assert r.source_tokens == TokenCounter().estimate(PY)
