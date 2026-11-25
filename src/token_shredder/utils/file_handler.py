"""
token_shredder - File Handler
Handles file validation, security checks, and path operations
"""
import os
import re
from pathlib import Path
from typing import Tuple


class FileHandler:
    """Handles file validation and security checks."""

    def __init__(self, max_file_size: int = 100 * 1024 * 1024):
        self.max_file_size = max_file_size

    def check_file(self, file_path: str):
        """Return None if the file can be converted, else a reason for the user.

        Paths with spaces, non-ASCII names or '..' are fine: this is a local CLI
        working on the user's own files. (validate_path_traversal and
        validate_filename remain for callers that handle untrusted names.)
        """
        path = Path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"
        if not path.is_file():
            return f"Not a file: {file_path}"
        if not os.access(path, os.R_OK):
            return f"File is not readable: {file_path}"
        if not self.validate_file_size(file_path):
            return f"File is larger than {self.max_file_size // (1024 * 1024)} MB: {file_path}"
        return None

    def validate_file(self, file_path: str) -> bool:
        """True if the file exists, is readable and within the size limit."""
        return self.check_file(file_path) is None

    def validate_file_exists(self, file_path: str) -> bool:
        """Check if file exists."""
        path = Path(file_path)
        return path.exists()

    def validate_file_size(self, file_path: str) -> bool:
        """Check if file is within size limits."""
        size = Path(file_path).stat().st_size
        if size > self.max_file_size:
            return False
        return True

    def validate_path_traversal(self, file_path: str) -> bool:
        """Prevent path traversal attacks."""
        if '..' in file_path:
            return False
        if '\x00' in file_path:
            return False
        try:
            resolved = Path(file_path).resolve()
            return resolved.exists()
        except Exception:
            return False

    def validate_filename(self, file_path: str) -> bool:
        """Check for allowed characters in filename - block .. and null bytes."""
        if not re.match(r'^[\w.\-\/\\]+$', file_path):
            return False
        if '..' in file_path or '\x00' in file_path:
            return False
        return True

    def is_readonly(self, file_path: str) -> bool:
        """Check if file is read-only."""
        return not os.access(file_path, os.W_OK)

    def get_temp_path(self, file_path: str) -> str:
        """Get temporary path for processing."""
        ext = Path(file_path).suffix
        return f"/tmp/token_shredder_{os.getpid()}{ext}"

    def cleanup_temp(self, temp_path: str) -> None:
        """Clean up temporary file."""
        try:
            Path(temp_path).unlink(missing_ok=True)
        except Exception:
            pass
