.PHONY: install dev test lint format type clean

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

test-fast:
	pytest tests/ -v --tb=short

lint:
	flake8 src/ tests/ --max-line-length=100

format:
	black src/ tests/

format-check:
	black --check src/ tests/

typecheck:
	mypy src/ --python-version 3.10

isort-check:
	isort --check-only src/ tests/

clean:
	rm -rf build/ dist/ __pycache__ .pytest_cache .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

all: format lint typecheck test
