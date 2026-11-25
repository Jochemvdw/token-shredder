# Benchmarks

Measured results on real public files are in the [README](../README.md#what-you-get-measured). The script and sample list are in [`benchmarks/`](../benchmarks/).

Summary:

- PDF / DOCX: cleaned text 5–7% below plain extraction (DOCX: list markers make it slightly larger), 14–21% below MarkItDown; `-d 2` ≈ 40% of the text, `-d 1` the outline.
- HTML: 97% smaller than the raw page, 65% smaller than its plain text (reference sections dropped), 86% smaller than MarkItDown.
- Code: 81–94% smaller, because the output is an outline (signatures and docstrings, no function bodies).
- Data files (default level 3): a profile. 10 GitHub issues: 83% smaller; an 8.8 MB CSV (86k rows): 3.8M → 799 tokens. When the profile would not be smaller, the data itself, minified (GitHub repo response: 18% smaller, lossless).

## Wider test set

`benchmarks/robustness.py CORPUS` runs every file through all levels and two budgets and checks: no crash, no empty output, sizes never shrink as the level goes up, budgets never exceeded. On 98 public files (17.3M tokens) the default level gives 466,634 tokens (was 1,026,775 before the corpus-driven tuning), with 0 problems.
