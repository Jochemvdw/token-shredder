# Benchmarks

## Token savings on real files

Real public files at the default level; tokens counted with tiktoken `cl100k_base`. "Baseline" is what you'd otherwise paste: plain extracted text for PDF/DOCX, the page's plain text for HTML, the raw file for everything else.

| File | Baseline | MarkItDown | Token Shredder | Smaller than baseline by | Words kept |
|---|---:|---:|---:|---:|---:|
| *Attention Is All You Need* (arXiv PDF, 15 p.) | 10,168 | 12,175 | 9,640 | **5%** | 99% |
| IRS form W-9 (PDF) | 9,009 | 9,058 | 8,417 | **7%** | 100% |
| Calibre demo document (DOCX) | 2,386 | 2,943 | 2,525 | −6% | 100% |
| Wikipedia "Python" article (HTML; raw page 325,067) | 27,535 | 71,099 | 9,684 | **65%** | 58% ¹ |
| `requests/sessions.py` (Python) | 7,336 | — | 1,288 | **82%** | 28% |
| Express `router/index.js` (JS) | 3,859 | — | 223 | **94%** | 17% |
| GitHub issues API, 10 issues (JSON) | 15,234 | — | 1,115 | **93%** | 20% |
| GitHub repo API response (JSON) | 1,863 | — | 915 | **51%** | 52% |
| Airport codes, 86,343 rows, 8.8 MB (CSV) | 3,841,232 | — | 887 | **99.98%** | profile |

¹ The article is kept; the reference list, "See also" and external links are dropped (`-d 4` keeps them).

On a wider set of 98 public files (papers, RFCs, READMEs, web pages, code in 6 languages, lockfiles, feeds, spreadsheets, configs) the default level gives 492,638 tokens from 17.3 million, with no crashes, budget overruns or size inversions (`benchmarks/robustness.py`). 18 real government Word/PowerPoint/Excel files pass the same checks.

## Do the answers survive? Head-to-head with MarkItDown

60 questions about 12 of those files, written from the originals. A model (Claude Sonnet) answered them from each tool's output without knowing which tool made which text; a separate model graded blind against reference answers.

| | Tokens given to the model | Fully correct | Partly correct | Not answerable |
|---|---:|---:|---:|---:|
| MarkItDown | 1,201,114 | 52 / 60 | 3 | 5 ¹ |
| Token Shredder (default level) | **166,711** | **54 / 60** ² | 3 | 3 |
| *without the lockfile* | | | | |
| MarkItDown | 369,915 | **52 / 55** | 3 | 0 |
| Token Shredder | **142,808** | 49 / 55 ² | 3 | 3 |

¹ MarkItDown's version of the 831k-token lockfile doesn't fit in a 200k context window, so those questions couldn't be asked.
² The blind run gave 52/60; after the record index gained comment counts, dates and authors, the 5 GitHub-issue questions were re-asked under the same rules and all were answered correctly (graded by us against the references, not blind).

- **Token Shredder loses** on how code works inside ("how does `truncate` work?") — the outline has signatures, not bodies. With `--query` set to the question, 5 of those 6 missed questions were answered correctly (one needed a constant defined elsewhere in the file); again graded by us, not blind.
- **MarkItDown loses** on exact counts in big tables (a model can't count 891 rows of a pasted CSV reliably; the profile states the counts) and on files that don't fit at all.

Caveats: one answering model, 60 questions written by a model, and the answering model read parts of four long files instead of all of it. Questions, references and grades: [`benchmarks/qa/`](../benchmarks/qa/).


## Reproduce

- `benchmarks/fetch_samples.sh` + `benchmarks/run.py`: the token table above.
- `benchmarks/robustness.py FOLDER`: runs every file at all levels and two budgets; checks no crash, no empty output, sizes never shrinking as the level goes up, budgets never exceeded.
- `benchmarks/qa/`: the 60 questions, reference answers and per-question grades.
