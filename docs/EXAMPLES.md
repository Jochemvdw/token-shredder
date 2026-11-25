# Examples

Real output from the default level. Limitations: see [Known gaps and limitations](LIMITATIONS.md). Measured sizes on real files: [BENCHMARKS.md](BENCHMARKS.md).

## Python file

Input `ex.py`: a module with imports, a class with `__init__` and `run`, and a helper function.

```bash
token-shredder convert ex.py -o -
```

```text
Simple module.

## Imports
os, typing

## class DataProcessor
Process incoming data streams.
- `def __init__(self, retries: int=3)`
- `def run(self, items: List[str]) -> Optional[str]`
  Run all items through the pipeline.

## def helper(x)
```

Signatures and the first doc line are kept, function bodies are not. `-d 1` lists names only, `-d 5` gives the file.

## A question about the code

```bash
token-shredder convert ex.py -Q "how are retries handled" -o -
```

Prints the outline above, then the matching class or function in full as a fenced code block.

## A data file

A JSON list of 30 issues, `token-shredder convert issues.json -o -`:

```text
# JSON File: issues.json

Top level: array(30 items)
- each item (30 items):
  - `id`: number 0-29 (int: yes), mean 14.5
  - `status`: string, enum: closed x15 (50%), open x15 (50%)
  - `title`: string 7-8 chars, e.g. "Issue 0", "Issue 1", "Issue 2"
  index (title per item; also status):
    0: Issue 0 [closed]
    ...

_Summary; use `--detail-level 4` for the data._
```

## A folder within a budget

```bash
token-shredder batch ./src -t 20000 -o - | pbcopy
```

One document of `<file path="..." detail_level="N">` blocks, 20,000 tokens in total.

## A web page or stdin

```bash
token-shredder convert https://example.com/article -o article.md
cat notes.txt | token-shredder convert -
```
