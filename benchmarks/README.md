# Benchmarks

Reproduces the table in the main [README](../README.md#what-you-get-measured). Limitations of the tool itself: [Known gaps and limitations](../README.md#known-gaps-and-limitations).

```bash
pip install -e . "markitdown[pdf,docx,pptx]"
cd benchmarks
./fetch_samples.sh              # downloads the public sample files into ./samples
mkdir -p out
python run.py samples out       # prints a JSON array with one object per file
```

Fields in each object:

- `baseline`: tokens of plain extracted text (PDF via pypdf, DOCX via python-docx, PPTX shape text, HTML via BeautifulSoup text) or of the raw file (everything else).
- `raw_html`: tokens of the raw page (HTML files only).
- `markitdown`: tokens of MarkItDown's output for the same file.
- `shredder`: tokens of Token Shredder's output at default settings (detail level 3).
- `vs_baseline`, `vs_markitdown`: percent fewer tokens than each.
- `retained_words`, `md_retained_words`: share of distinct words (4+ letters) from the baseline that appear in Token Shredder's / MarkItDown's output.
- `self_reported`: the savings percentage Token Shredder itself reports.

Tokens are counted with tiktoken `cl100k_base`, which is close to but not the same as Claude's tokenizer. Web pages and API responses change over time, so expect small differences from the published numbers (measured 2026-11-25).

Other files here:

- `robustness.py CORPUS_DIR [--csv results.csv]`: runs every file at all levels and with budgets and checks invariants (no crash, no empty output, sizes grow with level, budgets respected).
- `qa/`: the 60-question answer test (questions, references, blind grades); see `qa/README.md`.
