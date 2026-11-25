"""
token_shredder - Python API Usage Example
"""
from token_shredder import (
    convert_file,
    get_converter,
    detect_file_format,
    TokenCounter,
    QualityScorer,
    Deduplicator,
    CodeMinifier,
)
from token_shredder.models import ConversionOptions

# Convert a file
result = convert_file(
    "document.pdf",
    output_path="output.md",
    detail_level=3,
    preserve_images=False,
    deduplicate=True,
    minify_code=False,
)

print(f"Source tokens: {result.source_tokens}")
print(f"Output tokens: {result.output_tokens}")
print(f"Tokens saved: {result.tokens_saved} ({result.tokens_saved_pct}%)")
print(f"Quality: {result.quality_score}%")

# Analyze file format
format_type = detect_file_format("document.pdf")
print(f"Format: {format_type}")

# Get specific converter
converter = get_converter("pdf")
if converter:
    info = converter.get_file_info("document.pdf")
    print(f"File info: {info}")

# Token counting
counter = TokenCounter()
tokens = counter.estimate("Hello world. This is a test.")
print(f"Token count: {tokens}")

# Quality scoring
scorer = QualityScorer()
score = scorer.score("# Heading\nContent", "# Heading\nContent here.")
print(f"Quality score: {score}%")

# Processors
dedup = Deduplicator()
content = "# H1\nText\n# H1\nText"
clean = dedup.process(content)
print(f"Deduplicated: {clean}")

minifier = CodeMinifier()
code = "# comment\ndef foo():\n    # inner\n    return 1"
clean_code = minifier.process(code, "python")
print(f"Minified: {clean_code}")
