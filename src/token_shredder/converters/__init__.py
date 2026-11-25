"""
token_shredder - Converters Package Init
"""
from token_shredder.converters.pdf_converter import PDFConverter
from token_shredder.converters.docx_converter import DOCXConverter
from token_shredder.converters.pptx_converter import PPTXConverter
from token_shredder.converters.code_converter import CodeConverter
from token_shredder.converters.json_converter import JSONConverter
from token_shredder.converters.html_converter import HTMLConverter
from token_shredder.converters.text_converter import TextConverter
from token_shredder.converters.css_converter import CSSConverter
from token_shredder.converters.xlsx_converter import XLSXConverter
from token_shredder.converters.yaml_converter import YAMLConverter
from token_shredder.converters.xml_converter import XMLConverter
from token_shredder.converters.sql_converter import SQLConverter
from token_shredder.converters.toml_converter import TOMLConverter
from token_shredder.converters.env_converter import ENVConverter
from token_shredder.converters.log_converter import LOGConverter
from token_shredder.converters.markdown_converter import MarkdownConverter
from token_shredder.converters.ini_converter import INIConverter
from token_shredder.converters.csv_converter import CSVConverter
from token_shredder.converters.gitignore_converter import GitignoreConverter
from token_shredder.converters.svg_converter import SVGConverter
from token_shredder.converters.graphql_converter import GraphQLConverter
from token_shredder.converters.proto_converter import ProtoConverter
from token_shredder.converters.script_converter import ScriptConverter
from token_shredder.converters.dockerfile_converter import DockerfileConverter
from token_shredder.converters.makefile_converter import MakefileConverter
from token_shredder.converters.json5_converter import JSON5Converter
from token_shredder.converters.ccpp_converter import CCppConverter
from token_shredder.converters.base_converter import BaseConverter


def get_converter(format_type: str):
    """Get converter for a given file format."""
    converters = {
        'pdf': PDFConverter,
        'docx': DOCXConverter,
        'pptx': PPTXConverter,
        'python': CodeConverter,
        'py': CodeConverter,
        'js': CodeConverter,
        'ts': CodeConverter,
        'mjs': CodeConverter,
        'cjs': CodeConverter,
        'tsx': CodeConverter,
        'jsx': CodeConverter,
        'java': CodeConverter,
        'go': CodeConverter,
        'rs': CodeConverter,
        'json': JSONConverter,
        'json5': JSON5Converter,
        'csv': CSVConverter,
        'html': HTMLConverter,
        'htm': HTMLConverter,
        'txt': TextConverter,
        'md': MarkdownConverter,
        'css': CSSConverter,
        'xlsx': XLSXConverter,
        'xls': XLSXConverter,
        'yaml': YAMLConverter,
        'yml': YAMLConverter,
        'xml': XMLConverter,
        'sql': SQLConverter,
        'toml': TOMLConverter,
        'env': ENVConverter,
        'log': LOGConverter,
        'ini': INIConverter,
        'cfg': INIConverter,
        'conf': INIConverter,
        'gitignore': GitignoreConverter,
        'dockerignore': GitignoreConverter,
        'gitattributes': GitignoreConverter,
        'svg': SVGConverter,
        'graphql': GraphQLConverter,
        'gql': GraphQLConverter,
        'proto': ProtoConverter,
        'sh': ScriptConverter,
        'bash': ScriptConverter,
        'zsh': ScriptConverter,
        'fish': ScriptConverter,
        'ps1': ScriptConverter,
        'bat': ScriptConverter,
        'cmd': ScriptConverter,
        'dockerfile': DockerfileConverter,
        'makefile': MakefileConverter,
        'mk': MakefileConverter,
        'c': CCppConverter,
        'cpp': CCppConverter,
        'cc': CCppConverter,
        'cxx': CCppConverter,
        'h': CCppConverter,
        'hpp': CCppConverter,
        'hh': CCppConverter,
        'hxx': CCppConverter,
    }

    converter_class = converters.get(format_type.lower())
    if converter_class:
        return converter_class()
    return None


def detect_file_format(file_path: str) -> str:
    """Detect file format from extension."""
    import os
    ext = os.path.splitext(file_path)[1].lower().lstrip('.')
    return ext
