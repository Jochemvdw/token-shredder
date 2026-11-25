"""
token_shredder - Test File Handler
"""
import pytest
from token_shredder.utils.file_handler import FileHandler


def test_file_handler_validate_valid():
    handler = FileHandler()
    # Create a temp file
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(b"test")
        path = f.name
    try:
        assert handler.validate_file(path)
    finally:
        import os
        os.unlink(path)


def test_file_handler_validate_not_exists():
    handler = FileHandler()
    assert not handler.validate_file("/nonexistent/file.txt")


def test_paths_with_spaces_and_dotdot_are_accepted(tmp_path):
    from token_shredder.utils.file_handler import FileHandler
    d = tmp_path / "My Docs"
    d.mkdir()
    f = d / "Rapport été.txt"
    f.write_text("hi")
    handler = FileHandler()
    assert handler.validate_file(str(f))
    assert handler.validate_file(str(d / ".." / "My Docs" / "Rapport été.txt"))
    assert handler.check_file(str(tmp_path / "missing.txt")).startswith("File not found")
