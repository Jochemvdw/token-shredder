"""Convert a folder, optionally within one token budget.

Usage: python batch_processing.py FOLDER OUTPUT_FOLDER
Writes OUTPUT_FOLDER/<same structure>/NAME.EXT.md (e.g. report.pdf.md).
"""
import sys

from token_shredder import batch_convert, ConversionError

folder, out = sys.argv[1], sys.argv[2]

try:
    results = batch_convert(folder, output_dir=out, workers=4)
except ConversionError as e:   # some files failed; the others were still written
    print(f"Error: {e}")
    sys.exit(1)

for r in results:
    print(f"{r.source_file}: {r.source_tokens} -> {r.output_tokens} tokens (level {r.detail_level})")

# One budget for the whole folder, nothing written to disk:
results = batch_convert(folder, max_tokens=20000, write_output=False, quiet=True)
print(f"Within budget: {sum(r.output_tokens for r in results)} tokens in {len(results)} files")
