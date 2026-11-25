"""
token_shredder - Test Structure Optimizer
"""
import pytest
from token_shredder.processors.structure_optimizer import StructureOptimizer


def test_structure_optimizer_instantiation():
    optimizer = StructureOptimizer()
    assert optimizer is not None


def test_structure_optimizer_removes_excess_blanks():
    content = """# Heading

Text



More text
"""
    optimizer = StructureOptimizer()
    result = optimizer.process(content)
    # Should have fewer blank lines
    assert result.count('\n\n\n') == 0


def test_structure_optimizer_never_fuses_structure():
    content = "Intro text\n\n- item1\n- item2\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n```py\nx=1\n\n\n\ny=2\n```\n\nEnd"
    result = StructureOptimizer().process(content)
    assert "- item2\n\n| a | b |" in result
    assert "x=1\n\n\n\ny=2" in result  # code block untouched
    assert "Intro text\n\n- item1" in result
