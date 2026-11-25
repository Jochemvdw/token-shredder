"""
token_shredder - Test DOCX Converter
"""
import pytest
from token_shredder.converters.docx_converter import DOCXConverter
from token_shredder.models import ConversionOptions


def test_docx_converter_instantiation():
    converter = DOCXConverter()
    assert converter is not None


def test_docx_converter_extensions():
    assert '.docx' in DOCXConverter.get_supported_extensions()
