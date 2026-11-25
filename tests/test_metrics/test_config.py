"""
token_shredder - Test Config
"""
import pytest
from token_shredder.config import Config


def test_config_instantiation():
    config = Config()
    assert config is not None


def test_config_get():
    config = Config()
    detail = config.get("defaults.detail_level")
    assert detail == 3
