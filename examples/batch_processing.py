"""
token_shredder - Batch Processing Example
"""
from pathlib import Path
from token_shredder import convert_file, batch_convert

# Single file conversion
result = convert_file(
    "document.pdf",
    output_path="output.md",
    detail_level=3
)
print(f"Saved {result.tokens_saved} tokens ({result.tokens_saved_pct}%)")

# Batch processing
results = batch_convert(
    directory="./documents",
    output_dir="./converted",
    detail_level=3,
    workers=4
)

for r in results:
    print(f"{r.source_file}: {r.tokens_saved_pct:.1f}% saved")
