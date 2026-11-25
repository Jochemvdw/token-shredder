"""
token_shredder - Validators
"""
from pathlib import Path
from typing import Tuple


def validate_file_exists(file_path: str) -> Tuple[bool, str]:
    path = Path(file_path)
    if not path.exists():
        return False, f"File not found: {file_path}"
    return True, ""


def validate_file_size(file_path: str, max_size: int = 100*1024*1024) -> Tuple[bool, str]:
    size = Path(file_path).stat().st_size
    if size > max_size:
        return False, f"File too large: {size} bytes (max: {max_size})"
    return True, ""


def validate_supported_format(file_path: str) -> Tuple[bool, str]:
    supported = {
        '.pdf', '.docx', '.pptx', '.py', '.js', '.ts', '.tsx', '.jsx',
        '.java', '.go', '.rs', '.json', '.json5', '.csv', '.html', '.htm', '.md',
        '.txt', '.css', '.xlsx', '.xls', '.yaml', '.yml', '.xml', '.sql',
        '.toml', '.env', '.env.local', '.env.example', '.log', '.ini',
        '.cfg', '.conf', '.gitignore', '.dockerignore', '.gitattributes',
        '.svg', '.graphql', '.gql', '.proto', '.sh', '.bash', '.zsh', '.fish',
        '.ps1', '.bat', '.cmd', '.dockerfile', 'Dockerfile',
        '.makefile', '.mk', 'Makefile', 'makefile',
        '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hh', '.hxx'
    }
    ext = Path(file_path).suffix.lower()
    if ext not in supported:
        return False, f"Unsupported format: {ext}"
    return True, ""
