"""
token_shredder - Test PPTX Converter
"""
import pytest
from token_shredder.converters.pptx_converter import PPTXConverter
from token_shredder.models import ConversionOptions


def test_pptx_converter_instantiation():
    converter = PPTXConverter()
    assert converter is not None


def test_pptx_converter_extensions():
    assert '.pptx' in PPTXConverter.get_supported_extensions()
