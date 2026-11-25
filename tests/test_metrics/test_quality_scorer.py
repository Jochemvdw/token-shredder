"""
token_shredder - Test Quality Scorer
"""
import pytest
from token_shredder.metrics.quality_scorer import QualityScorer


def test_quality_scorer_instantiation():
    scorer = QualityScorer()
    assert scorer is not None


def test_quality_scorer_score():
    scorer = QualityScorer()
    converted = "# Heading\nContent here."
    original = "# Heading\nContent here. More details."
    score = scorer.score(converted, original)
    assert 0 <= score <= 100
