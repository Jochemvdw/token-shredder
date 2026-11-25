"""
token_shredder - Configuration Management
"""
import os
import yaml
import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

DEFAULT_CONFIG = {
    "defaults": {
        "detail_level": 3,
        "preserve_images": False,
        "embed_images": False,
        "count_exact": False,
    },
    "performance": {
        "max_workers": 4,
        "chunk_size": 1048576,
        "cache_enabled": True,
        "cache_dir": "~/.token-shredder/cache",
        "cache_ttl": 3600,
    },
    "security": {
        "allow_external_urls": False,
        "max_filename_length": 255,
        "sanitize_output": True,
    },
    "api": {
        "port": 8000,
        "host": "0.0.0.0",
        "max_file_size": 104857600,
    },
}


class CacheManager:
    """Handles caching of converted files using content hash for invalidation."""

    def __init__(self, cache_dir: str = "~/.token-shredder/cache", cache_ttl: int = 3600):
        self.cache_dir = Path(cache_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_ttl = timedelta(seconds=cache_ttl)

    def _get_cache_key(self, content_hash: str, options_hash: str) -> str:
        """Generate cache key for content and options combination."""
        return f"{content_hash}_{options_hash}"

    def _get_content_hash(self, content: str) -> str:
        """Generate content hash for content."""
        hasher = hashlib.md5()
        hasher.update(content.encode('utf-8'))
        return hasher.hexdigest()[:12]

    def _get_file_content(self, file_path: str) -> str:
        """Read file content."""
        with open(file_path, 'rb') as f:
            return f.read()

    def get(self, file_path: str, options_hash: str) -> Optional[str]:
        """Get cached result if exists and content hasn't changed."""
        content = self._get_file_content(file_path)
        content_hash = self._get_content_hash(content.decode('utf-8', errors='ignore'))
        key = self._get_cache_key(content_hash, options_hash)
        cache_file = self.cache_dir / f"{key}.md"
        if cache_file.exists():
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - mtime > self.cache_ttl:
                cache_file.unlink()
                return None
            return cache_file.read_text()
        return None

    def set(self, file_path: str, options_hash: str, content: str) -> None:
        """Store result in cache."""
        file_content = self._get_file_content(file_path).decode('utf-8', errors='ignore')
        content_hash = self._get_content_hash(file_content)
        key = self._get_cache_key(content_hash, options_hash)
        cache_file = self.cache_dir / f"{key}.md"
        cache_file.write_text(content)

    def invalidate(self, file_path: str) -> None:
        """Remove cached entries for a file based on content hash."""
        file_content = self._get_file_content(file_path).decode('utf-8', errors='ignore')
        content_hash = self._get_content_hash(file_content)
        prefix = content_hash
        for cache_file in self.cache_dir.glob(f"{prefix}_*.md"):
            cache_file.unlink()


@dataclass
class Config:
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._deep_copy(DEFAULT_CONFIG)
        self.config_path = config_path
        self._load_config()

    def _deep_copy(self, d: Dict) -> Dict:
        """Deep copy a dict."""
        return json.loads(json.dumps(d))

    def _load_config(self):
        if self.config_path and Path(self.config_path).exists():
            with open(self.config_path) as f:
                user_config = yaml.safe_load(f) or {}
                self._merge_config(user_config)

        if os.getenv("TOKEN_SHREDDER_DETAIL"):
            self.config["defaults"]["detail_level"] = int(os.getenv("TOKEN_SHREDDER_DETAIL"))
        if os.getenv("TOKEN_SHREDDER_CACHE"):
            self.config["performance"]["cache_enabled"] = os.getenv("TOKEN_SHREDDER_CACHE") == "true"
        if os.getenv("TOKEN_SHREDDER_WORKERS"):
            self.config["performance"]["max_workers"] = int(os.getenv("TOKEN_SHREDDER_WORKERS"))
        if os.getenv("TOKEN_SHREDDER_MAX_FILE_SIZE"):
            self.config["api"]["max_file_size"] = int(os.getenv("TOKEN_SHREDDER_MAX_FILE_SIZE"))

    def _merge_config(self, user_config: Dict[str, Any]):
        """Merge user config with defaults, handling nested dicts."""
        for key, value in user_config.items():
            if key in self.config and isinstance(value, dict) and isinstance(self.config[key], dict):
                self.config[key].update(value)
            else:
                self.config[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def get_cache_manager(self) -> CacheManager:
        cache_dir = self.config["performance"].get("cache_dir", "~/.token-shredder/cache")
        cache_ttl = self.config["performance"].get("cache_ttl", 3600)
        return CacheManager(cache_dir, cache_ttl)
