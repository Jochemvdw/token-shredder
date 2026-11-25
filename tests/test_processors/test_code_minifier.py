"""
token_shredder - Test Code Minifier
"""
import pytest
from token_shredder.processors.code_minifier import CodeMinifier


def test_code_minifier_instantiation():
    minifier = CodeMinifier()
    assert minifier is not None


def test_code_minifier_removes_comments():
    code = """# This is a comment
def foo():
    # Another comment
    return 42
"""
    minifier = CodeMinifier()
    result = minifier.process(code, 'python')
    assert '# This is a comment' not in result
    assert 'def foo():' in result


def test_convert_keeps_python_outline_headings(tmp_path):
    from token_shredder.main import convert_file

    src = tmp_path / "svc.py"
    src.write_text(
        'class UserService:\n    """Manage users."""\n\n'
        '    def authenticate(self, name):\n        """Check a login."""\n        return True\n\n'
        'def helper():\n    """Do a thing."""\n    pass\n'
    )
    result = convert_file(
        str(src), output_path=str(tmp_path / "out.md"), show_metrics=False, cache_enabled=False
    )
    assert "UserService" in result.markdown
    assert "helper" in result.markdown


def test_cached_convert_still_writes_output(tmp_path, monkeypatch):
    from token_shredder.main import convert_file

    monkeypatch.setenv("HOME", str(tmp_path))
    src = tmp_path / "notes.txt"
    src.write_text("hello world\n")
    out = tmp_path / "notes.md"
    convert_file(str(src), output_path=str(out), show_metrics=False)
    out.unlink()
    convert_file(str(src), output_path=str(out), show_metrics=False)
    assert out.exists()
