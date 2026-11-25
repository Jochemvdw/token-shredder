# Benchmarks

Measured results on real public files are in the [README](../README.md#what-you-get-measured). The script and sample list are in [`benchmarks/`](../benchmarks/).

Summary:

- PDF / DOCX: output is about the same size as plain extracted text (−5% to 0%), and ~15% smaller than MarkItDown.
- HTML: 94% smaller than the raw page, 26% smaller than its plain text, ~70% smaller than MarkItDown; keeps ~80% of the page's words.
- Code: 81–94% smaller, because the output is an outline (signatures and docstrings, no function bodies).
- JSON (default level 3): a schema with example values, 94% smaller on a list of GitHub issues; when the schema would not be smaller, the minified data (18% smaller, lossless).
