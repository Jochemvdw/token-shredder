"""
token_shredder - Logger Utility

All module loggers are children of the "token_shredder" logger, which owns the
single stderr handler. The default level is WARNING so normal CLI runs print
only the report; `--verbose` shows INFO, `--quiet` shows errors only.
Override with the TOKEN_SHREDDER_LOG_LEVEL environment variable.
"""
import logging
import os

_ROOT = "token_shredder"


def _configure_root() -> logging.Logger:
    root = logging.getLogger(_ROOT)
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("token-shredder: %(levelname)s: %(message)s"))
        root.addHandler(handler)
        root.propagate = False
        level = os.getenv("TOKEN_SHREDDER_LOG_LEVEL", "WARNING").upper()
        root.setLevel(getattr(logging, level, logging.WARNING))
        # pypdf warns about every odd font; that is noise for a CLI user.
        for noisy in ("pypdf", "pdfminer"):
            logging.getLogger(noisy).setLevel(logging.ERROR)
    return root


def setup_logger(name: str) -> logging.Logger:
    _configure_root()
    if not name.startswith(_ROOT):
        name = f"{_ROOT}.{name}"
    return logging.getLogger(name)


def set_log_level(level: int) -> None:
    """Set the level for token_shredder and the third-party parsers it uses."""
    _configure_root().setLevel(level)
