"""
token_shredder - Before/After Demo

This demonstrates the token savings from conversion.
"""
from token_shredder import convert_file, TokenCounter
from token_shredder.models import ConversionOptions

# Example: PDF conversion
result = convert_file(
    "document.pdf",
    output_path="document.md",
    detail_level=3
)

counter = TokenCounter()

# Before (raw PDF text)
raw_text = """
[PDF Binary Format]
- Font definitions: Times New Roman, Arial, Courier (30 tokens)
- Page layout: margins, spacing, indentation (25 tokens)
- Metadata: creation date, author, version (20 tokens)
- The quick brown fox jumps over the lazy dog. (10 tokens)
Total: ~85 tokens for 1 sentence
"""

# After (markdown)
markdown_text = """# Quick Brown Fox

The quick brown fox jumps over the lazy dog.
"""

raw_tokens = counter.estimate(raw_text)
md_tokens = counter.estimate(markdown_text)

print(f"Raw tokens: {raw_tokens}")
print(f"Markdown tokens: {md_tokens}")
print(f"Savings: {raw_tokens - md_tokens} tokens ({(1 - md_tokens/raw_tokens)*100:.1f}%)")

# Caveman (github.com/JuliusBrussee/caveman) is a separate tool that shortens
# Claude's replies. Its effect is on output and is not added to the above.
