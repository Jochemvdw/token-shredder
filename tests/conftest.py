"""
token_shredder - Pytest Configuration
"""
import pytest
import tempfile
import os


@pytest.fixture
def temp_file():
    """Create a temporary file."""
    fd, path = tempfile.mkstemp()
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def sample_markdown():
    """Sample markdown content."""
    return """# Test Document

## Section 1

This is some content.

## Section 2

More content here.
"""


@pytest.fixture
def sample_pdf():
    """Create a minimal PDF-like file for testing."""
    # Note: Real PDF testing would need actual PDF files
    return None
