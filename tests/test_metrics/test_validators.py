"""
token_shredder - Test Validators
"""
import pytest
from token_shredder.utils.validators import validate_file_exists, validate_file_size, validate_supported_format
import tempfile
import os


def test_validate_file_exists():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        path = f.name
    try:
        valid, msg = validate_file_exists(path)
        assert valid
        assert msg == ""
    finally:
        os.unlink(path)


def test_validate_file_not_exists():
    valid, msg = validate_file_exists("/nonexistent")
    assert not valid
    assert "not found" in msg


def test_validate_supported_format():
    valid, msg = validate_supported_format("test.pdf")
    assert valid


def test_validate_unsupported_format():
    valid, msg = validate_supported_format("test.xyz")
    assert not valid
