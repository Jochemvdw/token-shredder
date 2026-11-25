"""
token_shredder - Test Code Converter
"""
import pytest
from token_shredder.converters.code_converter import CodeConverter
from token_shredder.models import ConversionOptions


def test_code_converter_instantiation():
    converter = CodeConverter()
    assert converter is not None


def test_code_converter_extensions():
    extensions = CodeConverter.get_supported_extensions()
    assert '.py' in extensions
    assert '.js' in extensions
    assert '.ts' in extensions
