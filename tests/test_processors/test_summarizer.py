"""
token_shredder - Test Summarizer
"""
import pytest
from token_shredder.processors.summarizer import Summarizer


def test_summarizer_instantiation():
    summarizer = Summarizer()
    assert summarizer is not None


def test_summarizer_detail_level_1():
    summarizer = Summarizer()
    content = """# Heading 1

Some content line 1
Some content line 2

# Heading 2

More content
"""
    result = summarizer.process(content, detail_level=1)
    assert "# Heading 1" in result
    assert "# Heading 2" in result
