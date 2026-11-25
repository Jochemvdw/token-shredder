#!/bin/sh
# Downloads the public sample files used in the README table into ./samples
set -e
mkdir -p samples && cd samples
curl -sSL -o attention.pdf https://arxiv.org/pdf/1706.03762v7
curl -sSL -o irs-w9.pdf https://www.irs.gov/pub/irs-pdf/fw9.pdf
curl -sSL -o calibre-demo.docx https://calibre-ebook.com/downloads/demos/demo.docx
curl -sSL -o wiki-python.html "https://en.wikipedia.org/wiki/Python_(programming_language)"
curl -sSL -o requests-sessions.py https://raw.githubusercontent.com/psf/requests/main/src/requests/sessions.py
curl -sSL -o express-router.js https://raw.githubusercontent.com/expressjs/express/4.x/lib/router/index.js
curl -sSL -o gh-repo.json https://api.github.com/repos/python/cpython
curl -sSL -o gh-issues.json "https://api.github.com/repos/psf/requests/issues?per_page=10"
curl -sSL -o airports.csv https://raw.githubusercontent.com/datasets/airport-codes/main/data/airport-codes.csv
