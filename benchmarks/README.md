# Benchmarks

Reproduces the table in the main README.

```bash
pip install -e . "markitdown[pdf,docx,pptx]"
cd benchmarks
./fetch_samples.sh
mkdir -p out
python run.py samples out      # prints one JSON row per file
```

Columns in the output:

- `baseline`: tokens of plain extracted text (PDF via pypdf, DOCX via python-docx) or of the raw file (everything else).
- `markitdown`: tokens of MarkItDown's output for the same file.
- `shredder`: tokens of Token Shredder's output at default settings (detail level 3).
- `retained_words`: share of distinct words (4+ letters) from the baseline that appear in the output.

Tokens are counted with tiktoken `cl100k_base`, which is close to but not the same as Claude's tokenizer. Web pages and API responses change over time, so expect small differences from the published numbers (measured 2026-11-25).
