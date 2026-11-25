"""
token_shredder - Package Init
"""
from token_shredder.main import app, convert_file
from token_shredder.api import app as api_app
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.converters import get_converter, detect_file_format
from token_shredder.processors import Deduplicator, CodeMinifier, StructureOptimizer
from token_shredder.metrics import TokenCounter, QualityScorer

from importlib.metadata import PackageNotFoundError, version as _version

try:
    __version__ = _version("token-shredder")  # single source: pyproject.toml
except PackageNotFoundError:  # running from a source tree without install
    __version__ = "0.0.0"
__all__ = [
    'app',
    'convert_file',
    'api_app',
    'ConversionResult',
    'ConversionOptions',
    'get_converter',
    'detect_file_format',
    'Deduplicator',
    'CodeMinifier',
    'StructureOptimizer',
    'TokenCounter',
    'QualityScorer',
]
