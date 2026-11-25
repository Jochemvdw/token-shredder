"""
token_shredder - Test Text Converter
"""
import pytest
from token_shredder.converters.text_converter import TextConverter
from token_shredder.models import ConversionOptions


def test_text_converter_instantiation():
    converter = TextConverter()
    assert converter is not None


def test_text_converter_extensions():
    assert '.txt' in TextConverter.get_supported_extensions()
