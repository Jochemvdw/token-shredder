"""
token_shredder - Processors Package Init
"""
from token_shredder.processors.deduplicator import Deduplicator
from token_shredder.processors.code_minifier import CodeMinifier
from token_shredder.processors.structure_optimizer import StructureOptimizer
from token_shredder.processors.summarizer import Summarizer
from token_shredder.processors.image_handler import ImageHandler

__all__ = ['Deduplicator', 'CodeMinifier', 'StructureOptimizer', 'Summarizer', 'ImageHandler']
