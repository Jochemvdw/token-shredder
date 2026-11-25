"""
token_shredder - Test Converters
"""
import pytest
from token_shredder.converters import get_converter, detect_file_format
from token_shredder.converters.pdf_converter import PDFConverter
from token_shredder.converters.docx_converter import DOCXConverter
from token_shredder.converters.pptx_converter import PPTXConverter
from token_shredder.converters.code_converter import CodeConverter
from token_shredder.converters.json_converter import JSONConverter
from token_shredder.converters.html_converter import HTMLConverter
from token_shredder.converters.text_converter import TextConverter


def test_detect_format_pdf():
    assert detect_file_format("test.pdf") == "pdf"


def test_detect_format_docx():
    assert detect_file_format("test.docx") == "docx"


def test_detect_format_pptx():
    assert detect_file_format("test.pptx") == "pptx"


def test_detect_format_py():
    assert detect_file_format("test.py") == "py"


def test_detect_format_json():
    assert detect_file_format("test.json") == "json"


def test_detect_format_html():
    assert detect_file_format("test.html") == "html"


def test_detect_format_txt():
    assert detect_file_format("test.txt") == "txt"


def test_get_converter_pdf():
    converter = get_converter("pdf")
    assert isinstance(converter, PDFConverter)


def test_get_converter_docx():
    converter = get_converter("docx")
    assert isinstance(converter, DOCXConverter)


def test_get_converter_pptx():
    converter = get_converter("pptx")
    assert isinstance(converter, PPTXConverter)


def test_get_converter_py():
    converter = get_converter("py")
    assert isinstance(converter, CodeConverter)


def test_get_converter_json():
    converter = get_converter("json")
    assert isinstance(converter, JSONConverter)


def test_get_converter_html():
    converter = get_converter("html")
    assert isinstance(converter, HTMLConverter)


def test_get_converter_txt():
    converter = get_converter("txt")
    assert isinstance(converter, TextConverter)


def test_unsupported_format():
    converter = get_converter("xyz")
    assert converter is None
