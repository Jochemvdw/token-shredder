"""
token_shredder - Test Token Counter
"""
import pytest
from token_shredder.metrics.token_counter import TokenCounter


def test_token_counter_instantiation():
    counter = TokenCounter()
    assert counter is not None


def test_token_counter_estimate():
    counter = TokenCounter()
    text = "Hello world. This is a test."
    tokens = counter.estimate(text)
    assert tokens > 0
    assert isinstance(tokens, int)


def test_token_counter_empty():
    counter = TokenCounter()
    assert counter.estimate("") == 0
