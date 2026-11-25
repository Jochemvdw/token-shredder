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
                if not any(p.startswith("## ") and not p.startswith("## Imports") for p in markdown_parts):
                    # A script without functions or classes: say so instead of
                    # returning (almost) nothing.
                    lines = len(source.splitlines())
                    markdown_parts.append(
                        f"Script without functions or classes ({lines} lines). "
                        "Use --detail-level 5 for the full source.")
            else:
                markdown_parts = self._convert_generic(source, file_path, options)

        except Exception as e:
            logger.debug(f"Error reading code: {e}")
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
                if self._py_private(node.name) and level <= 2:
                    continue
                bases = ", ".join(ast.unparse(b) for b in node.bases)
                head = f"class {node.name}({bases})" if bases and level >= 2 else f"class {node.name}"
                parts.append(f"## {head}")
                self._add_doc(parts, node, level)
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        private = self._py_private(item.name)
                        if private and level <= 2:
                            continue
                        parts.append(f"- `{self._sig(item, level)}`")
                        doc = ast.get_docstring(item)
                        if doc and (level >= 4 or (level == 3 and not private)):
                            parts.append("  " + self._doc(doc, level).replace("\n", "\n  "))
                parts.append("")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                private = self._py_private(node.name)
                if private and level <= 2:
                    continue
                parts.append(f"## {self._sig(node, level)}")
                if not private or level >= 4:
                    self._add_doc(parts, node, level)
                parts.append("")
        return parts

    @staticmethod
    def _py_private(name: str) -> bool:
        """_helper and most dunders; __init__ and __call__ describe the public API."""
        if name in ("__init__", "__call__"):
            return False
        return name.startswith("_")

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
        doc = CodeConverter._clean_doc(doc)
        return doc if level >= 4 else CodeConverter._summary(doc)

    @staticmethod
    def _clean_doc(text: str) -> str:
        """Strip Javadoc/HTML/Sphinx markup that costs tokens but adds no meaning."""
        text = re.sub(r"\{@(?:code|link|linkplain|literal|value)\s+([^}]*)\}", r"\1", text)
        text = re.sub(r":(?:class|func|meth|attr|mod|obj|exc|data|ref):`~?([^`]+)`", r"\1", text)
        text = re.sub(r"</?(?:em|i|b|strong|code|tt)>", "", text)
        text = re.sub(r"</?(?:p|br|ul|ol|li|pre)\s*/?>", " ", text)
        text = text.replace("``", "`")
        return "\n".join(re.sub(r"[ \t]+", " ", ln).strip() for ln in text.strip().splitlines())

    @staticmethod
    def _summary(text: str, max_chars: int = 200) -> str:
        """First sentence of the first paragraph, on one line."""
        para = re.sub(r"\s+", " ", text.strip().split("\n\n")[0]).strip()
        m = re.search(r"(?<=[.!?])\s+(?=[A-Z`(\[])", para)
        first = para[: m.start()] if m else para
        return first if len(first) <= max_chars else first[: max_chars - 1].rstrip() + "…"

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
        ext = self._get_ext(file_path)
        if lines and (len(source) / len(lines) > 300 or max(map(len, lines)) > 5000):
            return [f"Minified or bundled code ({len(source) // 1024:,} KB on {len(lines):,} lines): "
                    "no outline possible. Use --detail-level 5 for the full source."]
        parts = [f"## Declarations ({len(lines)} lines)"]
        seen_docs, names = set(), {}
        for i, line in enumerate(lines):
            if not (self._DECL_RE.match(line) or self._MEMBER_RE.match(line)):
                continue
            decl = line.strip().rstrip("{").rstrip()
            private = self._is_private(decl, ext)
            if private and level <= 2:
                continue
            if level <= 3 and ext in (".java", ".ts", ".tsx", ".cs", ".kt"):
                # "public" is the assumed default and annotations rarely matter for an outline.
                decl = re.sub(r"^public\s+", "", decl)
                decl = re.sub(r"@\w+(?:\([^)]*\))?\s+", "", decl)
            if level < 2:
                decl = self._PARAMS_RE.sub("", decl)
                if decl in names:  # overloads: "assertTrue (x5)"
                    names[decl] += 1
                    continue
                names[decl] = 1
            if level >= 4 or (level == 3 and not private):
                doc = self._leading_comment(lines, i, full=level >= 4)
                doc = self._clean_doc(doc).replace("\n", " ") if doc else ""
                if level == 3:
                    doc = self._summary(doc)
                if doc and doc not in seen_docs:
                    seen_docs.add(doc)
                    parts.append(f"// {doc}")
            parts.append(decl)
        if level < 2:
            parts = [parts[0]] + [f"{d} (x{n})" if n > 1 else d for d, n in names.items()]
        return parts

    @staticmethod
    def _is_private(decl: str, ext: str) -> bool:
        """Best-effort 'not part of the public API' per language."""
        if ext == ".go":
            m = re.match(r"(?:func\s+(?:\([^)]*\)\s*)?|type\s+)(\w)", decl)
            return bool(m and m.group(1).islower())
        if ext == ".rs":
            return bool(re.match(r"(?:(?:async|unsafe|const)\s+)*fn\s", decl))
        if ext in (".java", ".ts", ".tsx", ".cs", ".kt"):
            return bool(re.match(r"(?:\w+\s+)*private\b", decl)) or decl.startswith("#")
        if ext in (".js", ".mjs", ".cjs", ".jsx"):
            m = re.search(r"(?:function\s+|class\s+|(?:const|let|var)\s+|^)([\w$]+)", decl)
            return bool(m and m.group(1).startswith("_"))
        return False

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
