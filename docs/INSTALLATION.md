# Installation

Python 3.10 or newer (3.10-3.13 are tested in CI on Linux, macOS and Windows). Known limitations: [LIMITATIONS.md](LIMITATIONS.md).

## From PyPI

```bash
pip install token-shredder
```

Or, to get the `token-shredder` command without touching other Python environments: `pipx install token-shredder`, or run it once with `uvx token-shredder convert file.pdf`.

Extras:

| Extra | Adds |
|---|---|
| `token-shredder[api]` | FastAPI, uvicorn, python-multipart for the HTTP API ([API.md](API.md)) |
| `token-shredder[claude]` | the `anthropic` package; only used by `QualityScorer(use_claude_api=True)` in Python, not by any CLI command |
| `token-shredder[dev]` | pytest, httpx, fastapi, black, flake8, mypy, isort, build, twine |

## From source

```bash
git clone https://github.com/Jochemvdw/token-shredder.git
cd token-shredder
pip install -e ".[dev]"
python -m pytest
```

Contributing: [CONTRIBUTING.md](../CONTRIBUTING.md).

## Check

```bash
token-shredder version
token-shredder --help
```

Dependencies (pypdf, python-docx, python-pptx, openpyxl, beautifulsoup4, tiktoken, typer, rich, pyyaml, json5) are installed automatically; the first run of tiktoken may need network access to fetch its encoding file, after which it works offline.
