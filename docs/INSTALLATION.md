# Installation

## From PyPI

```bash
pip install token-shredder
```

Or, to get the `token-shredder` command without touching other Python environments: `pipx install token-shredder`.

## From Source

```bash
git clone https://github.com/Jochemvdw/token-shredder.git && cd token-shredder && pip install -e .
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Format code
black src/
isort src/

# Lint
flake8 src/
```

## Requirements

Python 3.10+; dependencies are installed automatically (see pyproject.toml).
