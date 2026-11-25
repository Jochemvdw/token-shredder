# Benchmarks

Measured results on real public files are in the [README](../README.md#what-you-get-measured). The script and sample list are in [`benchmarks/`](../benchmarks/).

Summary:

- PDF / DOCX: output is about the same size as plain extracted text (−6% to 0%), and 14–16% smaller than MarkItDown.
- HTML: 94% smaller than the raw page, 26% smaller than its plain text, ~70% smaller than MarkItDown; keeps ~80% of the page's words.
- Code: 81–94% smaller, because the output is an outline (signatures and docstrings, no function bodies).
- Data files (default level 3): a profile. 10 GitHub issues: 83% smaller; an 8.8 MB CSV (86k rows): 3.8M → 799 tokens. When the profile would not be smaller, the data itself, minified (GitHub repo response: 18% smaller, lossless).
