#!/bin/sh
# Token Shredder CLI examples. Edit the file names, then run the lines you want.
set -e

pip install token-shredder

# One file: writes document.md and prints a token report
token-shredder convert document.pdf
token-shredder convert document.pdf -d 2 -o output.md     # detail level 1-5, named output
token-shredder convert document.pdf -o -                  # markdown on stdout
token-shredder convert document.pdf --copy                # clipboard

# Fit a token budget, or ask a question
token-shredder convert app.py -t 2000
token-shredder convert app.py -Q "how are errors handled"

# URLs and stdin
token-shredder convert https://example.com/article
curl -s https://api.github.com/repos/python/cpython | token-shredder convert - --type json

# A folder
token-shredder batch ./documents -o ./converted           # one NAME.EXT.md per file
token-shredder batch ./documents -d 1 -o ./summary        # names and headings only
token-shredder batch ./src -t 20000 -o - | pbcopy         # one budgeted document with <file> blocks

# Inspect without writing
token-shredder preview document.pdf
token-shredder quality document.pdf
token-shredder analyze document.pdf
token-shredder version

# HTTP API (optional extra)
pip install "token-shredder[api]"
uvicorn token_shredder.api:app &
curl -F file=@document.pdf "http://127.0.0.1:8000/convert?detail_level=3"
