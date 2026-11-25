"""
token_shredder - Test Image Handler
"""
import pytest
from token_shredder.processors.image_handler import ImageHandler


def test_image_handler_instantiation():
    handler = ImageHandler()
    assert handler is not None


def test_image_handler_reference():
    handler = ImageHandler()
    content = "image.png"
    result = handler.process(content, "test.html", embed=False)
    assert result == content
