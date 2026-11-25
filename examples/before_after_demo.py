"""Before/after on a real file: token counts of the original text and Token Shredder's output.

Usage: python before_after_demo.py FILE [DETAIL_LEVEL]
"""
import sys

from token_shredder import TokenCounter, convert_file

path = sys.argv[1]
level = int(sys.argv[2]) if len(sys.argv) > 2 else 3

result = convert_file(path, detail_level=level, write_output=False, show_metrics=False)
counter = TokenCounter()

print(f"{path} at detail level {level}")
print(f"Source tokens (the file as read): {result.source_tokens}")
print(f"Output tokens: {result.output_tokens} ({result.tokens_saved_pct:.1f}% fewer)")
print("For PDF/DOCX the source count is the extracted text; the savings are small there.")
print("---")
print(result.markdown[:800])
