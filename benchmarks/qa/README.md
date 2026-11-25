# Question-answering benchmark

- `questions.json`: 60 questions with reference answers about 12 public files (download URLs in `sources.tsv`), written from the original files.
- `grades_head_to_head.json`: blind grades (correct / partial / wrong / not_in_text) for answers given from Token Shredder's default output and from MarkItDown's output. Results are summarised in the main README.

Method: the outputs of both tools were randomly labelled per file; a model answered from one label set at a time using only that text; a separate model graded both answers per question without knowing which tool produced them.
