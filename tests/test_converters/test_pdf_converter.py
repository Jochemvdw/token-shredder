"""
token_shredder - Test PDF Converter
"""
import pytest
from token_shredder.converters.pdf_converter import PDFConverter
from token_shredder.models import ConversionOptions


def test_pdf_converter_instantiation():
    converter = PDFConverter()
    assert converter is not None


def test_pdf_converter_extensions():
    assert '.pdf' in PDFConverter.get_supported_extensions()


def test_pdf_converter_get_file_info():
    # This would need a real PDF file
    pass
