"""Python API: convert a file and use the building blocks.

Usage: python api_usage.py [FILE]   (default: this file)
"""
import sys

from token_shredder import (
    CodeMinifier,
    Deduplicator,
    QualityScorer,
    TokenCounter,
    convert_file,
    detect_file_format,
    get_converter,
)

path = sys.argv[1] if len(sys.argv) > 1 else __file__

# Convert a file; write_output=False only returns the result (no .md file)
result = convert_file(path, detail_level=3, write_output=False, show_metrics=False)
print(f"Format: {result.format}, detail level: {result.detail_level}")
print(f"Source tokens: {result.source_tokens}")
print(f"Output tokens: {result.output_tokens}")
print(f"Tokens saved: {result.tokens_saved} ({result.tokens_saved_pct:.1f}%)")
print(f"Notes: {result.warnings}")

# A token budget and a question
result = convert_file(path, max_tokens=500, query="minifier", write_output=False,
                      show_metrics=False)
print(f"With budget and query: {result.output_tokens} tokens")

# Format detection and converters
print(f"Detected format: {detect_file_format(path)}")
converter = get_converter(detect_file_format(path))
if converter:
    print(f"File info: {converter.get_file_info(path)}")

# Token counting (tiktoken estimate, not Claude's exact count)
print(f"Token count: {TokenCounter().estimate('Hello world. This is a test.')}")

# Quality heuristic (0-100, word overlap, not a measure of meaning kept)
score = QualityScorer().score("# Heading\nContent", "# Heading\nContent here.")
print(f"Quality score: {score}")

# Processors on their own
print(Deduplicator().process("# H1\nText\n# H1\nText"))
print(CodeMinifier().process("# comment\ndef foo():\n    # inner\n    return 1", "python"))
