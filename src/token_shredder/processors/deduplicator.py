"""
token_shredder - Deduplicator Processor
Removes duplicate content from markdown using n-gram fingerprint with Jaccard similarity
"""
import re
from typing import Optional, Dict, Set
from collections import defaultdict


class Deduplicator:
    def __init__(self, threshold: float = 1.0, use_ngram: bool = True, ngram_size: int = 3):
        self.threshold = threshold
        self.use_ngram = use_ngram
        self.ngram_size = ngram_size

    def process(self, content: str) -> str:
        """Collapse repeated lines.

        The default threshold 1.0 only collapses exact repeats. Lower values
        also merge near-duplicates, which can silently drop different data
        (e.g. two JSON keys that differ by one word), so use them with care.
        """
        lines = content.splitlines()
        output = []

        fingerprints: Dict[str, str] = {}

        in_fence = False
        for line in lines:
            line_stripped = line.strip()
            if line_stripped.startswith(("```", "~~~")):
                in_fence = not in_fence
                output.append(line)
                continue
            # Never touch code, table rows or blank lines: a repeated row or
            # statement there is data, not redundancy.
            if in_fence or not line_stripped or line_stripped.startswith("|"):
                output.append(line)
                continue

            normalized = self._normalize(line_stripped)

            is_duplicate = False
            if self.threshold >= 1.0:
                # Exact (case/whitespace-insensitive) repeats only.
                is_duplicate = normalized in fingerprints.values()
            elif self.use_ngram:
                fingerprint = self._get_fingerprint(normalized)
                for existing_fp in fingerprints:
                    if self._similarity_fingerprint(fingerprint, existing_fp) >= self.threshold:
                        is_duplicate = True
                        break
            else:
                for existing_text in fingerprints.values():
                    if self._similarity(normalized, existing_text) >= self.threshold:
                        is_duplicate = True
                        break

            if not is_duplicate:
                fingerprints[self._get_fingerprint(normalized)] = normalized
                output.append(line)
            else:
                marker = f"[See above: {normalized[:30]}...]"
                # Only collapse when the marker is actually shorter than the
                # repeated line; otherwise the "dedup" would add tokens.
                output.append(marker if len(marker) < len(line_stripped) else line)

        return "\n".join(output)

    def _normalize(self, text: str) -> str:
        """Normalize text for comparison."""
        return re.sub(r'\s+', ' ', text.lower())

    def _get_fingerprint(self, text: str) -> str:
        """Generate n-gram fingerprint for efficient similarity comparison."""
        if len(text) < self.ngram_size:
            return text
        ngrams = [text[i:i+self.ngram_size] for i in range(len(text) - self.ngram_size + 1)]
        return "_".join(sorted(set(ngrams)))

    def _similarity_fingerprint(self, fp1: str, fp2: str) -> float:
        """Compare two fingerprints for similarity using Jaccard."""
        if fp1 == fp2:
            return 1.0
        set1 = set(fp1.split("_"))
        set2 = set(fp2.split("_"))
        if not set1 or not set2:
            return 0.0
        overlap = set1 & set2
        return len(overlap) / max(len(set1), len(set2))

    def _similarity(self, s1: str, s2: str) -> float:
        """Simple word overlap similarity."""
        if s1 == s2:
            return 1.0
        if len(s1) < 10 or len(s2) < 10:
            return 0.0
        words1 = set(s1.split())
        words2 = set(s2.split())
        if not words1 or not words2:
            return 0.0
        overlap = words1 & words2
        return len(overlap) / max(len(words1), len(words2))
