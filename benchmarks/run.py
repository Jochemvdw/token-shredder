import sys, re, json, io, contextlib
from pathlib import Path
import tiktoken
from token_shredder.main import convert_file
from markitdown import MarkItDown

enc = tiktoken.get_encoding("cl100k_base")
tok = lambda s: len(enc.encode(s, disallowed_special=()))
words = lambda s: set(w.lower() for w in re.findall(r"[A-Za-z]{4,}", s))
samples, out = Path(sys.argv[1]), Path(sys.argv[2])
md = MarkItDown()

def plain(p):
    ext = p.suffix.lower()
    if ext == ".pdf":
        import pypdf; return "\n".join(pg.extract_text() or "" for pg in pypdf.PdfReader(p).pages)
    if ext == ".docx":
        import docx; d = docx.Document(p)
        parts = [x.text for x in d.paragraphs]
        for t in d.tables:
            for r in t.rows: parts.append(" | ".join(c.text for c in r.cells))
        return "\n".join(parts)
    if ext == ".pptx":
        import pptx; pr = pptx.Presentation(p)
        return "\n".join(sh.text_frame.text for s in pr.slides for sh in s.shapes if sh.has_text_frame)
    if ext in (".html", ".htm"):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(p.read_text(errors="replace"), "html.parser")
        for t in soup(["script", "style", "noscript"]): t.decompose()
        return re.sub(r"\n\s*\n+", "\n\n", soup.get_text("\n"))
    return p.read_text(errors="replace")

rows = []
for p in sorted(samples.iterdir()):
    base = plain(p)
    try: mid = md.convert(str(p)).text_content
    except Exception as e: mid = ""
    with contextlib.redirect_stdout(io.StringIO()):
        r = convert_file(str(p), output_path=str(out / (p.name + ".md")), show_metrics=False, cache_enabled=False)
    ts = r.markdown
    (out / (p.name + ".markitdown.md")).write_text(mid)
    bw = words(base)
    raw = tok(p.read_text(errors='replace')) if p.suffix in ('.html', '.htm') else None
    rows.append(dict(file=p.name, raw_html=raw, baseline=tok(base), markitdown=tok(mid), shredder=tok(ts),
        vs_baseline=round(100*(1-tok(ts)/tok(base)),1) if tok(base) else None,
        vs_markitdown=round(100*(1-tok(ts)/tok(mid)),1) if tok(mid) else None,
        retained_words=round(100*len(bw & words(ts))/len(bw),1) if bw else None,
        md_retained_words=round(100*len(bw & words(mid))/len(bw),1) if bw else None,
        self_reported=round(r.tokens_saved_pct,1)))
print(json.dumps(rows, indent=1))
