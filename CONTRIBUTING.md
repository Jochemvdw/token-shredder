# Contributing to Token Shredder

Thank you for your interest in contributing! 

## How to Contribute

1. **Fork the repository**
2. **Create a branch**: `git checkout -b feature/my-feature`
3. **Make changes** and add tests
4. **Run tests**: `python -m pytest tests/ -v`
5. **Submit a pull request**

## Development Setup

```bash
# Clone and install
git clone https://github.com/Jochemvdw/token-shredder.git
cd token-shredder
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# Format code
black src/
isort src/

# Lint
flake8 src/
```

## Code Standards

- Follow PEP 8
- Write tests for new features
- Update documentation as needed
- Keep changes focused

## License

By contributing, you agree to the MIT License terms.
