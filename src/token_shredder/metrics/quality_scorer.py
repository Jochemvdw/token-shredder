"""
token_shredder - Quality Scorer
Scores semantic preservation quality with structure-aware analysis
"""
import re
from typing import Optional, Dict


class QualityScorer:
    def __init__(self, use_claude_api: bool = False, api_key: Optional[str] = None):
        self.use_claude_api = use_claude_api
        self.api_key = api_key

    def _without_code_blocks(self, text: str) -> str:
        """Strip fenced code blocks to avoid false structure positives."""
        return re.sub(r'```[\s\S]*?```', '', text)

    def score(self, converted: str, original: str) -> float:
        """Score quality of conversion (0-100)."""
        if not original:
            return 0.0

        if self.use_claude_api:
            return self._score_with_api(converted, original)

        converted_clean = self._without_code_blocks(converted)
        converted_lower = converted_clean.lower()
        original_lower = original.lower()

        converted_words = set(converted_lower.split())
        original_words = set(original_lower.split())

        if not original_words:
            return 0.0

        overlap = converted_words & original_words
        ratio = len(overlap) / len(original_words)

        score = min(ratio * 100, 100.0)

        structure_bonus = 0.0
        if re.search(r'^#{1,6}\s', converted_clean, re.MULTILINE):
            structure_bonus += 15.0
        if '```' in converted:
            structure_bonus += 10.0
        if re.search(r'^\|.+\|', converted_clean, re.MULTILINE):
            structure_bonus += 8.0
        if re.search(r'^[-*]\s', converted_clean, re.MULTILINE):
            structure_bonus += 5.0
        if re.search(r'^\d+\.\s', converted_clean, re.MULTILINE):
            structure_bonus += 5.0

        if any(kw in converted_clean for kw in ['def ', 'class ', 'function ', 'import ', 'from ']):
            structure_bonus += 10.0

        list_items = len(re.findall(r'(?:^|\n)[-*]\s', converted_clean)) + len(re.findall(r'(?:^|\n)\d+\.\s', converted_clean))
        if list_items > 0:
            structure_bonus += min(list_items * 0.5, 10.0)

        score = min(score + structure_bonus, 100.0)

        return round(score, 1)

    def score_detailed(self, converted: str, original: str) -> dict:
        """Detailed quality scoring breakdown."""
        if not original:
            return {'overall': 0.0, 'structure': 0.0, 'content': 0.0, 'tables': 0.0, 'code': 0.0}

        converted_clean = self._without_code_blocks(converted)
        converted_lower = converted_clean.lower()
        original_lower = original.lower()

        converted_words = set(converted_lower.split())
        original_words = set(original_lower.split())
        content_score = 0.0
        if original_words:
            overlap = converted_words & original_words
            content_score = min(len(overlap) / len(original_words) * 100, 100.0)

        structure_score = 0.0
        if re.search(r'^#{1,6}\s', converted_clean, re.MULTILINE):
            structure_score += 30.0
        if '```' in converted:
            structure_score += 20.0
        if re.search(r'^\|.+\|', converted_clean, re.MULTILINE):
            structure_score += 15.0
        if re.search(r'^[-*]\s', converted_clean, re.MULTILINE):
            structure_score += 10.0

        code_score = 0.0
        if any(kw in converted_clean for kw in ['def ', 'class ', 'function ', 'import ', 'from ', '=> ', 'const ', 'let ']):
            code_score = 30.0
        if '```' in converted:
            code_score += 20.0

        tables_score = 0.0
        table_lines = re.findall(r'^\|.+\|$', converted_clean, re.MULTILINE)
        if table_lines:
            tables_score = min(len(table_lines) * 2, 30.0)

        overall = min(content_score * 0.4 + structure_score * 0.3 + code_score * 0.2 + tables_score * 0.1, 100.0)

        return {
            'overall': round(overall, 1),
            'structure': round(structure_score, 1),
            'content': round(content_score, 1),
            'tables': round(tables_score, 1),
            'code': round(code_score, 1)
        }

    def _score_with_api(self, converted: str, original: str) -> float:
        """Score using Claude API for semantic verification."""
        if not self.api_key:
            return self.score(converted, original)

        try:
            from anthropic import Anthropic
            client = Anthropic(api_key=self.api_key)

            response = client.messages.create(
                model="claude-haiku-5-5",
                max_tokens=100,
                messages=[
                    {
                        "role": "user",
                        "content": f"Compare these two texts and rate semantic preservation 0-100:\n\nOriginal: {original[:2000]}\n\nConverted: {converted[:2000]}"
                    }
                ]
            )

            return float(response.content[0].text)
        except Exception:
            return self.score(converted, original)
