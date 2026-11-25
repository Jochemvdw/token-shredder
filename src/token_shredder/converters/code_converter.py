"""
token_shredder - Code Converter
Converts Python/JS/TS code to semantic markdown
"""
import ast
import re
import os
from pathlib import Path
from typing import Optional
from token_shredder.converters.base_converter import BaseConverter
from token_shredder.models import ConversionResult, ConversionOptions
from token_shredder.utils.logger import setup_logger

logger = setup_logger(__name__)


class CodeConverter(BaseConverter):
    @staticmethod
    def get_supported_extensions() -> list:
        return ['.py', '.js', '.ts', '.java', '.go', '.rs']

    def convert(self, file_path: str, options: ConversionOptions) -> ConversionResult:
        markdown = self.convert_to_markdown(file_path, options)
        return ConversionResult(
            markdown=markdown,
            source_file=file_path,
            target_file=str(Path(file_path).with_suffix('.md')),
            format=self._get_ext(file_path).lstrip('.'),
            detail_level=options.detail_level,
            preserve_images=options.preserve_images,
        )

    def convert_to_markdown(self, file_path: str, options: ConversionOptions) -> str:
        markdown_parts = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                source = f.read()

            ext = self._get_ext(file_path)

            if ext == '.py':
                markdown_parts = self._convert_python(source, options)
            else:
                markdown_parts = self._convert_generic(source, file_path, options)

        except Exception as e:
            logger.error(f"Error reading code: {e}")
            markdown_parts.append(f"[Error reading code: {e}]")

        return "\n".join(markdown_parts)

    def get_file_info(self, file_path: str) -> dict:
        try:
            with open(file_path, encoding='utf-8', errors='replace') as f:
                source = f.read()
            return {
                'lines': len(source.splitlines()),
                'functions': self._count_functions(source),
                'classes': self._count_classes(source),
            }
        except Exception as e:
            return {'lines': 0, 'functions': 0, 'classes': 0}

    # Detail levels for code:
    #   1  names only (classes, functions, methods)
    #   2  + signatures
    #   3  + first paragraph of each docstring / doc comment (default)
    #   4  + full docstrings / doc comments
    #   5  full source (handled in main.convert_file)

    def _convert_python(self, source: str, options: ConversionOptions) -> list:
        level = options.detail_level
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return [f"```python\n{source}\n```"]

        parts = []
        module_doc = ast.get_docstring(tree)
        if module_doc and level >= 3:
            parts += [self._doc(module_doc, level), ""]

        imports = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                imports += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                imports.append("." * node.level + (node.module or ""))
        if imports and level >= 2:
            parts += ["## Imports", ", ".join(dict.fromkeys(imports)), ""]

        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                bases = ", ".join(ast.unparse(b) for b in node.bases)
                head = f"class {node.name}({bases})" if bases and level >= 2 else f"class {node.name}"
                parts.append(f"## {head}")
                self._add_doc(parts, node, level)
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        parts.append(f"- `{self._sig(item, level)}`")
                        doc = ast.get_docstring(item)
                        if doc and level >= 3:
                            parts.append("  " + self._doc(doc, level).replace("\n", "\n  "))
                parts.append("")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                parts.append(f"## {self._sig(node, level)}")
                self._add_doc(parts, node, level)
                parts.append("")
        return parts

    @staticmethod
    def _sig(node, level: int) -> str:
        prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
        if level < 2:
            return f"{prefix} {node.name}"
        ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""
        decorators = "".join(f"@{ast.unparse(d)} " for d in node.decorator_list)
        return f"{decorators}{prefix} {node.name}({ast.unparse(node.args)}){ret}"

    def _add_doc(self, parts: list, node, level: int) -> None:
        doc = ast.get_docstring(node)
        if doc and level >= 3:
            parts.append(self._doc(doc, level))

    @staticmethod
    def _doc(doc: str, level: int) -> str:
        doc = doc.strip()
        return doc if level >= 4 else doc.split("\n\n")[0]

    _DECL_RE = re.compile(
        r"^\s*(?:export\s+)?(?:default\s+)?(?:(?:public|private|protected|static|final|abstract|"
        r"async|override|pub(?:\([^)]*\))?|unsafe|inline|virtual|declare)\s+)*"
        r"(?:function\b|(?:class|interface|enum|struct|trait|impl|func|fn|mod|namespace)\s+[\w$<(]|"
        r"type\s+\w+(?:<[^>]*>)?\s*=|type\s+\w+\s+\w"
        r"|(?:const|let|var)\s+[\w$]+\s*(?::[^=]+)?=\s*(?:async\s*)?"
        r"(?:function\b|\([^)]*\)\s*(?::[^=]+)?=>|[\w$]+\s*=>))"
        r"|^\s*[\w$.]+\s*=\s*(?:async\s+)?function\b"
        r"|^\s*(?:public|private|protected)\s[^;=]*\("
    )
    # Class members such as "  async find(id: string): Promise<User> {" (JS/TS/Java/C#).
    _MEMBER_RE = re.compile(
        r"^\s+(?:(?:public|private|protected|static|async|readonly|get|set|override|abstract)\s+)*"
        r"(?!(?:if|for|while|switch|catch|return|function|else)\b)[\w$]+\s*(?:<[^>]*>)?\s*\([^;]*\)"
        r"\s*(?::\s*[^={;]+)?\{\s*$"
    )
    # Name position for level 1: the first "(" right after an identifier
    # (skips Go receivers like "func (s *Server) Handle(").
    _PARAMS_RE = re.compile(r"(?<=[\w$>])\(.*$")

    def _convert_generic(self, source: str, file_path: str, options: ConversionOptions) -> list:
        level = options.detail_level
        lines = source.splitlines()
        parts = [f"## Declarations ({len(lines)} lines)"]
        for i, line in enumerate(lines):
            if not (self._DECL_RE.match(line) or self._MEMBER_RE.match(line)):
                continue
            decl = line.strip().rstrip("{").rstrip()
            if level < 2:
                decl = self._PARAMS_RE.sub("", decl)
            if level >= 3:
                doc = self._leading_comment(lines, i, full=level >= 4)
                if doc:
                    parts.append(f"// {doc}")
            parts.append(decl)
        return parts

    @staticmethod
    def _leading_comment(lines: list, i: int, full: bool) -> str:
        """The /** */ or // comment directly above line i, as plain text."""
        j = i - 1
        block = []
        while j >= 0 and lines[j].strip().startswith(("*", "/*", "//", "*/")):
            block.insert(0, lines[j].strip())
            j -= 1
        text = []
        for raw in block:
            t = re.sub(r"^(/\*\*?|\*/|\*|///?|//!)\s?", "", raw).strip().rstrip("*/").strip()
            if t.startswith("@") and not full:
                break
            if t:
                text.append(t)
            elif text and not full:
                break
        return " ".join(text)

    def _get_ext(self, file_path: str) -> str:
        return os.path.splitext(file_path)[1].lower()

    def _count_functions(self, source: str) -> int:
        try:
            tree = ast.parse(source)
            return sum(1 for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)))
        except:
            return 0

    def _count_classes(self, source: str) -> int:
        try:
            tree = ast.parse(source)
            return sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))
        except:
            return 0
