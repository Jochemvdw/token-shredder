"""
token_shredder - Code Minifier Processor
Strips comments and unnecessary content from code in multiple languages
"""
import ast
import re
from typing import Optional


class CodeMinifier:
    def __init__(self, remove_docstrings: bool = True, remove_blank_lines: bool = True):
        self.remove_docstrings = remove_docstrings
        self.remove_blank_lines = remove_blank_lines

    def process(self, content: str, language: str = 'python') -> str:
        """Minify code content based on language."""
        lang = language.lower()
        if lang in ('python', 'py'):
            return self._minify_python(content)
        elif lang in ('javascript', 'js', 'typescript', 'ts'):
            return self._minify_javascript(content)
        elif lang in ('java', 'go', 'rust', 'c', 'cpp', 'cc', 'cxx', 'h', 'hpp', 'hh', 'hxx'):
            return self._minify_generic(content)
        else:
            return self._minify_generic(content)

    def _minify_python(self, content: str) -> str:
        """Remove comments and docstrings from Python code."""
        lines = content.splitlines()
        output = []
        in_docstring = False
        docstring_type = None

        for line in lines:
            stripped = line.strip()

            if stripped.startswith('"""') or stripped.startswith("'''"):
                if not in_docstring:
                    in_docstring = True
                    docstring_type = stripped[:3]
                    continue
                else:
                    in_docstring = False
                    continue

            if in_docstring:
                continue

            if '#' in stripped and not stripped.startswith('#'):
                code_part = stripped.split('#')[0].rstrip()
                if code_part:
                    output.append(code_part)
            elif stripped and not stripped.startswith('#'):
                output.append(stripped)

        if self.remove_blank_lines:
            output = self._remove_excessive_blanks(output)

        return "\n".join(output)

    def _minify_javascript(self, content: str) -> str:
        """Minify JavaScript/TypeScript - remove comments and compress."""
        lines = content.splitlines()
        output = []
        in_block_comment = False

        for line in lines:
            stripped = line.strip()

            if '/**/' in stripped or '*/' in stripped:
                in_block_comment = False
                continue
            if stripped.startswith('/*') or (in_block_comment and '*/' not in stripped):
                in_block_comment = True
                continue

            if stripped.startswith('//'):
                continue

            if '//' in stripped and not stripped.startswith('//'):
                code_part = stripped.split('//')[0].rstrip()
                if code_part:
                    output.append(code_part)
            elif stripped and not stripped.startswith('*'):
                output.append(stripped)

        if self.remove_blank_lines:
            output = self._remove_excessive_blanks(output)

        return "\n".join(output)

    def _minify_generic(self, content: str) -> str:
        """Generic minification - remove comments and excessive whitespace for C/C++, Java, Go, Rust."""
        lines = content.splitlines()
        output = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith(('#', '//', '/*', '*', ';')):
                continue
            cleaned = re.sub(r'#.*$|//.*$|/\*.*?\*/', '', line).rstrip()
            if cleaned:
                output.append(cleaned)

        if self.remove_blank_lines:
            output = self._remove_excessive_blanks(output)

        return "\n".join(output)

    def _remove_excessive_blanks(self, lines: list) -> list:
        """Remove excessive blank lines."""
        output = []
        for line in lines:
            stripped = line.strip()
            if stripped:
                output.append(stripped)
            elif output and not output[-1].strip():
                continue
            else:
                output.append("")
        return output
