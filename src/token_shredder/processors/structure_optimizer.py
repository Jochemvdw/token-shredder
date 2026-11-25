"""
token_shredder - Structure Optimizer Processor
Collapses runs of blank lines without touching code blocks, tables or lists.
"""
import re

_FENCE = re.compile(r"^\s*(```|~~~)")
# Lines that carry markdown structure and must never be joined with a neighbour.
_STRUCTURAL = re.compile(r"^\s*(#{1,6}\s|[-*+]\s|\d+[.)]\s|\||>|```|~~~|\s{4})")


class StructureOptimizer:
    def __init__(self, collapse_headings: bool = True, merge_paragraphs: bool = False,
                 max_consecutive_blanks: int = 1):
        # collapse_headings is kept for API compatibility; headings are never changed.
        self.collapse_headings = collapse_headings
        self.merge_paragraphs = merge_paragraphs
        self.max_consecutive_blanks = max_consecutive_blanks

    def process(self, content: str) -> str:
        """Collapse blank-line runs outside fenced code blocks.

        With merge_paragraphs=True, two short plain-prose paragraphs separated by
        one blank line are joined. Off by default: it saves almost nothing and
        changes paragraph boundaries.
        """
        output = []
        blanks = 0
        in_fence = False
        for line in content.splitlines():
            if _FENCE.match(line):
                in_fence = not in_fence
                blanks = 0
                output.append(line)
                continue
            if in_fence:
                output.append(line)
                continue
            if not line.strip():
                blanks += 1
                if blanks <= self.max_consecutive_blanks:
                    output.append("")
                continue
            if (self.merge_paragraphs and blanks == 1 and len(output) >= 2
                    and self._is_prose(output[-2]) and self._is_prose(line)
                    and len(output[-2]) + len(line) < 200):
                output.pop()  # the blank line
                output[-1] = output[-1] + " " + line.strip()
            else:
                output.append(line)
            blanks = 0
        return "\n".join(output)

    @staticmethod
    def _is_prose(line: str) -> bool:
        return bool(line.strip()) and not _STRUCTURAL.match(line)
