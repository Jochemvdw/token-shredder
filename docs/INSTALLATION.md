# Installation

## From Source

```bash
git clone https://github.com/OWNER/token-shredder.git && cd token-shredder && pip install .
```

PyPI release coming soon.

For an editable install, use `pip install -e .` instead.

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
