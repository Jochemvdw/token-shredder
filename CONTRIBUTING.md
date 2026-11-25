# Contributing

Issues and pull requests are welcome. Token Shredder is alpha software: see [Known gaps and limitations](README.md#known-gaps-and-limitations) for what is out of scope today.

## Setup

```bash
git clone https://github.com/Jochemvdw/token-shredder.git
cd token-shredder
pip install -e ".[dev]"
python -m pytest
```

CI (`.github/workflows/ci.yml`) runs `python -m pytest -q` on Python 3.10-3.13 (Linux, plus macOS and Windows). The `Makefile` has shortcuts (`make test`, `make lint`, `make format`, `make typecheck`); black, isort, flake8 and mypy are available in the dev extra but are not enforced by CI. Line length is 100.

## Guidelines

- Add a test for new behaviour or a fixed bug (`tests/`).
- Keep the invariants: a higher detail level never gives less content, level 5 is the full content, a summary is never larger than the file. `python benchmarks/robustness.py <folder>` checks them on any folder of real files.
- Update the docs and `CHANGELOG.md` when behaviour changes. Every statement in `docs/` should be checkable against the code.
- Keep changes focused.

## Adding a format

There is no plugin system. Add a converter class in `src/token_shredder/converters/` (subclass `BaseConverter`), register its extension in `CONVERTERS` in `converters/__init__.py`, and add the extension to `SUPPORTED_SUFFIXES` in `main.py` so `batch` picks it up. Then add tests and an entry in [docs/FILE_FORMATS.md](docs/FILE_FORMATS.md).

By contributing you agree to license your work under the MIT License.
