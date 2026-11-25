"""
token_shredder - Token Counter
Estimates token counts using tiktoken with configurable model and fallbacks
"""
import tiktoken
from typing import Optional


class TokenCounter:
    def __init__(self, model: str = "claude-3-5-sonnet-20241022"):
        self.model = model
        self.encoding = None
        self._initialize_encoding()

    def _initialize_encoding(self):
        """Initialize encoding with fallback chain."""
        model_fallbacks = [
            self.model,
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "gpt-4",
            "gpt-3.5-turbo",
            "cl100k_base",
        ]

        for model_name in model_fallbacks:
            try:
                self.encoding = tiktoken.encoding_for_model(model_name)
                return
            except KeyError:
                continue

        try:
            self.encoding = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.encoding = None

    def estimate(self, text: str) -> int:
        """Estimate token count for text."""
        if not text:
            return 0
        if self.encoding:
            try:
                tokens = self.encoding.encode(text)
                return len(tokens)
            except Exception:
                pass
        return len(text) // 4

    def estimate_file(self, file_path: str) -> int:
        """Estimate tokens in a file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        return self.estimate(text)

    @staticmethod
    def get_supported_models() -> list:
        """Get list of supported model names."""
        return [
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "gpt-4",
            "gpt-3.5-turbo",
        ]
