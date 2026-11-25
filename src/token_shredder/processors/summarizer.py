"""
token_shredder - Summarizer Processor
Creates summaries of content based on detail level
"""
from typing import Optional


class Summarizer:
    def __init__(self, max_headings: int = 50):
        self.max_headings = max_headings
    
    def process(self, content: str, detail_level: int = 1) -> str:
        """Create summary based on detail level."""
        lines = content.splitlines()
        output = []
        heading_count = 0
        
        if detail_level == 1:
            # Just headings
            for line in lines:
                if line.startswith('#'):
                    output.append(line)
                    heading_count += 1
                    if heading_count >= self.max_headings:
                        break
        elif detail_level == 2:
            # Headings + first line of each section
            in_section = False
            for line in lines:
                if line.startswith('#'):
                    output.append(line)
                    in_section = True
                    heading_count += 1
                elif in_section and line.strip() and not line.startswith('#'):
                    output.append(line)
                    in_section = False
        else:
            # Full content with blank line compression
            for line in lines:
                if line.strip():
                    output.append(line)
        
        return "\n".join(output)
