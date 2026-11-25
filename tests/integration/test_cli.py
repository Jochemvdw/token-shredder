"""
token_shredder - Integration Test CLI
"""
import pytest
import tempfile
import os
from token_shredder.main import convert_file
from token_shredder.models import ConversionOptions


def test_convert_file_basic():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("# Test\nContent here.")
        path = f.name
    try:
        options = ConversionOptions(detail_level=3)
        # Would need actual converter for real test
    finally:
        os.unlink(path)
