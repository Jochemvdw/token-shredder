# Token counter

`TokenCounter` estimates token counts with tiktoken. tiktoken is an OpenAI tokenizer, so counts for Claude are estimates: keep a 10-20% margin near a hard limit. See [Known gaps and limitations](LIMITATIONS.md).

## Methods

- `TokenCounter(model="claude-3-5-sonnet-20241022")`: tiktoken knows no Claude models, so in practice this ends up on the `gpt-4` encoding, which is `cl100k_base`. (If tiktoken is unavailable, counts fall back to characters / 4.)
- `estimate(text: str) -> int`
- `estimate_file(file_path: str) -> int`: reads the file as UTF-8 text (raises on other encodings and binary files).
- `TokenCounter.get_supported_models() -> list`

## Usage

```python
from token_shredder import TokenCounter   # or token_shredder.metrics

counter = TokenCounter()
print(counter.estimate("Hello world. This is a test."))
```

## Notes

- The CLI report ("Source Tokens", "Output Tokens") and `--max-tokens` use this counter.
- No API calls. tiktoken downloads its encoding file on first use if it is not cached; after that it works offline.
