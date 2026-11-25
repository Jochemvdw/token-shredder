"""
token_shredder - Prompts for Claude Integration
"""

CLAUDE_INSTRUCTIONS = """
# Token Shredder - Claude Integration Instructions

When using Token Shredder converted files with Claude:

1. The markdown output preserves all semantic content
2. Formatting overhead has been removed
3. Structure is maintained via headings
4. Token savings: 30-60% reduction

Combined with Caveman: 85-90% total token savings
"""

CONVERSION_PROMPT = """
Convert the following file to efficient markdown:
- Remove formatting overhead
- Preserve structure (headings, lists, tables)
- Strip metadata and redundant content
- Keep all substantive information
"""
