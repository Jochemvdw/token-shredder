# Benchmarks

The measured results are in the [README](../README.md#what-you-get-measured): token counts on nine real public files against a plain-text baseline and MarkItDown, and a 60-question answer test (with its caveats). To reproduce them, see [`benchmarks/README.md`](../benchmarks/README.md). Questions, references and grades: [`benchmarks/qa/`](../benchmarks/qa/).

Reading the numbers:

- Tokens are counted with tiktoken `cl100k_base`, not Claude's tokenizer: expect 10-20% difference.
- The baseline is plain extracted text for PDF/DOCX, the page's plain text for HTML, and the raw file for everything else.
- PDF/DOCX savings are small (cleaned text, same content); the big savings come from web pages, code outlines and data profiles, where content is deliberately left out ([limitations](../README.md#known-gaps-and-limitations)).

## Wider test set

`benchmarks/robustness.py CORPUS_DIR` converts every file at all levels and with token budgets and checks: no crash, no empty output, size never shrinks as the level goes up, budgets never exceeded. On 98 public files (17.3 million tokens) the default level gives 492,638 tokens with 0 problems; on 18 real government Word/PowerPoint/Excel files the same checks pass. It checks invariants, not whether answers survive.
