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
