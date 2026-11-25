"""
token_shredder - Structure Optimizer Processor
Collapses redundant structure and optimizes layout
"""
import re
from typing import List


class StructureOptimizer:
    def __init__(self, collapse_headings: bool = True, merge_paragraphs: bool = True, max_consecutive_blanks: int = 1):
        self.collapse_headings = collapse_headings
        self.merge_paragraphs = merge_paragraphs
        self.max_consecutive_blanks = max_consecutive_blanks
    
    def process(self, content: str) -> str:
        """Optimize markdown structure."""
        lines = content.splitlines()
        output = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Collapse heading levels (e.g. ### -> ## when redundant nesting)
            if self.collapse_headings and re.match(r'^#{1,6}\s', line):
                heading_text = line.lstrip('#').strip()
                output.append(line)
                i += 1
                continue
            
            # Remove empty sections (heading followed immediately by another heading)
            if re.match(r'^#{1,6}\s', line):
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines) and re.match(r'^#{1,6}\s', lines[j]):
                    i = j
                    continue
            
            # Merge short paragraphs separated by single blank line
            if self.merge_paragraphs and line.strip():
                j = i + 1
                if j < len(lines) and not lines[j].strip():
                    k = j + 1
                    if k < len(lines) and lines[k].strip() and not re.match(r'^#{1,6}\s', lines[k]):
                        if len(line) + len(lines[k]) < 200:
                            output.append(line + ' ' + lines[k].strip())
                            i = k + 1
                            while i < len(lines) and not lines[i].strip():
                                i += 1
                            continue
            
            # Remove excessive blank lines
            if not line.strip():
                blank_count = 0
                k = i
                while k < len(lines) and not lines[k].strip():
                    blank_count += 1
                    k += 1
                
                if blank_count <= self.max_consecutive_blanks:
                    output.append("")
                i = k
                continue
            
            output.append(line)
            i += 1
        
        result = "\n".join(output)
        return result