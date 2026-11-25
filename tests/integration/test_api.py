"""
token_shredder - Test Main
"""
import pytest
from token_shredder.main import convert_file, display_report
from token_shredder.models import ConversionResult


def test_display_report():
    result = ConversionResult(
        markdown="# Test",
        source_file="test.pdf",
        target_file="test.md",
        format="pdf",
        source_tokens=100,
        output_tokens=50,
        tokens_saved=50,
        tokens_saved_pct=50.0,
        quality_score=95.0,
        processing_time_ms=100.0,
    )
    # Should not raise
    display_report(result)
