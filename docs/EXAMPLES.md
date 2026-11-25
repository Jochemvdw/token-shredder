# Token Shredder - Examples

## Before/After Examples

### PDF Example

**Before:** a PDF containing one sentence, plus fonts, layout and metadata.

**After (Markdown):**
```markdown
# Quick Brown Fox

The quick brown fox jumps over the lazy dog.
```

### PPTX Example

**Before:** a 12-slide deck.

**After:**
```markdown
## Slide 1: Title

## Slide 2: Content
...
```

### Python Code Example

**Before**:
```python
import os
import sys
from typing import List, Optional

class DataProcessor:
    """Process incoming data streams."""
    ...
```

**After (outline; illustrative)**:
```text
Imports: os, sys, typing

class DataProcessor
  Process incoming data streams.
```

Function bodies, signatures and methods are dropped, so this output is not suitable when the model must edit or debug the code.

## Related tools

[Caveman](https://github.com/JuliusBrussee/caveman) is a separate, complementary tool that shortens Claude's replies. Token Shredder only affects the input you send. See [BENCHMARKS.md](BENCHMARKS.md) for measured numbers.
