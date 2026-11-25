"""
token_shredder - Converters Package

Converters are imported on first use, so the CLI starts fast and a format's
libraries (pypdf, python-docx, openpyxl, ...) load only when needed.
"""
import importlib

from token_shredder.converters.base_converter import BaseConverter

# format (file extension) -> "module:Class"
CONVERTERS = {
    'pdf': 'pdf_converter:PDFConverter',
    'docx': 'docx_converter:DOCXConverter',
    'pptx': 'pptx_converter:PPTXConverter',
    'python': 'code_converter:CodeConverter',
    'py': 'code_converter:CodeConverter',
    'js': 'code_converter:CodeConverter',
    'ts': 'code_converter:CodeConverter',
    'mjs': 'code_converter:CodeConverter',
    'cjs': 'code_converter:CodeConverter',
    'tsx': 'code_converter:CodeConverter',
    'jsx': 'code_converter:CodeConverter',
    'java': 'code_converter:CodeConverter',
    'go': 'code_converter:CodeConverter',
    'rs': 'code_converter:CodeConverter',
    'json': 'json_converter:JSONConverter',
    'json5': 'json5_converter:JSON5Converter',
    'jsonl': 'jsonl_converter:JSONLConverter',
    'ndjson': 'jsonl_converter:JSONLConverter',
    'csv': 'csv_converter:CSVConverter',
    'tsv': 'csv_converter:CSVConverter',
    'html': 'html_converter:HTMLConverter',
    'htm': 'html_converter:HTMLConverter',
    'txt': 'text_converter:TextConverter',
    'md': 'markdown_converter:MarkdownConverter',
    'css': 'css_converter:CSSConverter',
    'xlsx': 'xlsx_converter:XLSXConverter',
    'yaml': 'yaml_converter:YAMLConverter',
    'yml': 'yaml_converter:YAMLConverter',
    'xml': 'xml_converter:XMLConverter',
    'sql': 'sql_converter:SQLConverter',
    'toml': 'toml_converter:TOMLConverter',
    'env': 'env_converter:ENVConverter',
    'log': 'log_converter:LOGConverter',
    'ini': 'ini_converter:INIConverter',
    'cfg': 'ini_converter:INIConverter',
    'conf': 'ini_converter:INIConverter',
    'gitignore': 'gitignore_converter:GitignoreConverter',
    'dockerignore': 'gitignore_converter:GitignoreConverter',
    'gitattributes': 'gitignore_converter:GitignoreConverter',
    'svg': 'svg_converter:SVGConverter',
    'graphql': 'graphql_converter:GraphQLConverter',
    'gql': 'graphql_converter:GraphQLConverter',
    'proto': 'proto_converter:ProtoConverter',
    'sh': 'script_converter:ScriptConverter',
    'bash': 'script_converter:ScriptConverter',
    'zsh': 'script_converter:ScriptConverter',
    'fish': 'script_converter:ScriptConverter',
    'ps1': 'script_converter:ScriptConverter',
    'bat': 'script_converter:ScriptConverter',
    'cmd': 'script_converter:ScriptConverter',
    'dockerfile': 'dockerfile_converter:DockerfileConverter',
    'makefile': 'makefile_converter:MakefileConverter',
    'mk': 'makefile_converter:MakefileConverter',
    'c': 'ccpp_converter:CCppConverter',
    'cpp': 'ccpp_converter:CCppConverter',
    'cc': 'ccpp_converter:CCppConverter',
    'cxx': 'ccpp_converter:CCppConverter',
    'h': 'ccpp_converter:CCppConverter',
    'hpp': 'ccpp_converter:CCppConverter',
    'hh': 'ccpp_converter:CCppConverter',
    'hxx': 'ccpp_converter:CCppConverter',
}


def get_converter(format_type: str):
    """Get a converter instance for a format (file extension), or None."""
    spec = CONVERTERS.get(format_type.lower())
    if not spec:
        return None
    module, cls = spec.split(":")
    return getattr(importlib.import_module(f"token_shredder.converters.{module}"), cls)()


def __getattr__(name):
    # Keep `from token_shredder.converters import PDFConverter` working.
    for spec in CONVERTERS.values():
        module, cls = spec.split(":")
        if cls == name:
            return getattr(importlib.import_module(f"token_shredder.converters.{module}"), cls)
    raise AttributeError(name)


def detect_file_format(file_path: str) -> str:
    """Detect file format from extension."""
    import os
    name = os.path.basename(file_path).lower()
    if name in ("dockerfile", "containerfile") or name.startswith("dockerfile."):
        return "dockerfile"
    if name in ("makefile", "gnumakefile"):
        return "makefile"
    if name in (".gitignore", ".dockerignore", ".gitattributes"):
        return name.lstrip(".")
    ext = os.path.splitext(file_path)[1].lower().lstrip('.')
    return ext
