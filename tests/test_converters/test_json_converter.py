"""
token_shredder - Test JSON Converter
"""
import pytest
from token_shredder.converters.json_converter import JSONConverter
from token_shredder.models import ConversionOptions


def test_json_converter_instantiation():
    converter = JSONConverter()
    assert converter is not None


def test_json_converter_extensions():
    extensions = JSONConverter.get_supported_extensions()
    assert '.json' in extensions
