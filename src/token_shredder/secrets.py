"""
token_shredder - Secret redaction

Token Shredder's output is meant to be pasted into an AI model, so well-known,
high-confidence credential formats are replaced by [REDACTED: kind] in every
output (all levels). This is a safety net, not a secret scanner: it only knows
formats that are unambiguous. Disable with --keep-secrets.
"""
import re
from typing import List, Tuple

_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("private key", re.compile(
        r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----.*?-----END (?:[A-Z]+ )*PRIVATE KEY-----", re.S)),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{50,})\b")),
    ("GitLab token", re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b")),
    ("Slack token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}\b")),
    ("Stripe key", re.compile(r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{20,}\b")),
    ("Anthropic key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("OpenAI key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("PyPI token", re.compile(r"\bpypi-[A-Za-z0-9_-]{50,}\b")),
    ("npm token", re.compile(r"\bnpm_[A-Za-z0-9]{36}\b")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("password in URL", re.compile(r"(?<=://)[^/\s:@]+:[^/\s@]{3,}(?=@)")),
]


def redact(text: str) -> Tuple[str, List[str]]:
    """Return (text with secrets replaced, list of kinds found)."""
    found = []
    for kind, pattern in _PATTERNS:
        text, n = pattern.subn(f"[REDACTED: {kind}]", text)
        if n:
            found.append(f"{kind} x{n}" if n > 1 else kind)
    return text, found
