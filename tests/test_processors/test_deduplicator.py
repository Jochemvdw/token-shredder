"""
token_shredder - Test Deduplicator
"""
import pytest
from token_shredder.processors.deduplicator import Deduplicator


def test_deduplicator_instantiation():
    dedup = Deduplicator()
    assert dedup is not None


def test_deduplicator_removes_duplicates():
    para = "This is a long paragraph that repeats verbatim later in the document body."
    content = f"""# Heading 1

{para}

# Heading 1

{para}

More content
"""
    dedup = Deduplicator()
    result = dedup.process(content)
    assert result.count(para) == 1
    assert len(result) < len(content)


def test_deduplicator_never_grows_output():
    content = "Google Research\nAuthor A\nGoogle Research\nAuthor B\nGoogle Research\n"
    result = Deduplicator().process(content)
    assert len(result) <= len(content)
    assert result.count("Google Research") == 3


def test_deduplicator_preserves_unique():
    content = """# Heading 1

Content A

# Heading 2

Content B
"""
    dedup = Deduplicator()
    result = dedup.process(content)
    assert "Content A" in result
    assert "Content B" in result


def test_deduplicator_leaves_code_and_tables_alone():
    content = "| a | 1 |\n| a | 1 |\n```py\nreturn None\nreturn None\n```"
    assert Deduplicator().process(content) == content
