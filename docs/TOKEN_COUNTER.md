# Token Shredder - Token Counter Module Doc

## TokenCounter

Estimates token counts using tiktoken. tiktoken is an OpenAI tokenizer, so counts for Claude are estimates.

### Methods

- `__init__(model: str = "claude-3-5-sonnet-20241022")`
  Tries the given model name, then falls back to other encodings (ends at cl100k_base).

- `estimate(text: str) -> int`
  Estimate token count for text.

- `estimate_file(file_path: str) -> int`
  Estimate tokens in a file.

### Usage

```python
from token_shredder.metrics import TokenCounter

counter = TokenCounter()
tokens = counter.estimate("Hello world. This is a test.")
print(f"{tokens} tokens")
```

### Accuracy

- Counts are estimates, not Claude's exact token counts
- Runs offline; no API calls required
