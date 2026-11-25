"""--query: keep the parts that match a question, in full."""
from typer.testing import CliRunner

from token_shredder import query as q
from token_shredder.main import app, batch_convert, convert_file
from token_shredder.metrics import TokenCounter

count = TokenCounter().estimate

TS = "\n".join(
    f"/** Helper number {i}. */\nexport function helper{i}(x: number): number {{\n"
    + "\n".join(f"  const v{j} = x * {j};" for j in range(15)) + "\n  return x;\n}\n"
    for i in range(40)
) + ("/** Cut a string. */\nexport function truncate(value: string, max: number): string {\n"
     "  if (value.length <= max) { return value; }\n  return value.substring(0, max) + '…';\n}\n")


def _conv(path, **kw):
    return convert_file(str(path), show_metrics=False, cache_enabled=False, write_output=False, **kw)


def test_terms_split_identifiers():
    t = q.terms("truncateMiddle parse_dict_header HTTPServer")
    for expected in ("truncatemiddle", "truncate", "middle", "parse", "dict", "header", "http", "server"):
        assert expected in t


def test_named_function_included_in_full(tmp_path):
    f = tmp_path / "s.ts"
    f.write_text(TS)
    r = _conv(f, query="how does truncate work?")
    assert "value.substring(0, max)" in r.markdown          # the body, not just the signature
    assert "const v3 = x * 3" not in r.markdown              # other bodies stay out
    assert r.output_tokens < count(TS) / 2


def test_query_respects_budget(tmp_path):
    f = tmp_path / "s.ts"
    f.write_text(TS)
    for budget in (300, 1000, 3000):
        r = _conv(f, query="truncate", max_tokens=budget)
        assert count(r.markdown) <= budget
        assert "substring" in r.markdown


def test_prose_section_named_in_question(tmp_path):
    f = tmp_path / "doc.md"
    sections = "\n\n".join(f"## {name}\n\n" + f"Text about {name.lower()} and other things. " * 30
                           for name in ("Install", "Usage", "Trace", "License", "Credits"))
    f.write_text("# Guide\n\n" + sections)
    r = _conv(f, query="what does trace do")
    rel = r.markdown.split("## Relevant to", 1)[1]
    assert "### Guide > Trace" in rel and "Text about install" not in rel


def test_no_match_is_said(tmp_path):
    f = tmp_path / "s.ts"
    f.write_text(TS)
    r = _conv(f, query="kubernetes ingress")
    assert "No part of the file matches" in r.markdown


def test_secrets_redacted_in_relevant_parts(tmp_path):
    f = tmp_path / "cfg.py"
    key = "AKIA" + "ABCDEFGHIJKLMNOP"
    f.write_text("def connect():\n    '''Connect to AWS.'''\n    return '" + key + "'\n"
                 + "\n".join(f"def other{i}():\n    return {i}\n" for i in range(40)))
    r = _conv(f, query="how does connect work")
    assert key not in r.markdown and "REDACTED" in r.markdown


def test_batch_query_ranks_across_files(tmp_path):
    (tmp_path / "a.ts").write_text(TS)
    (tmp_path / "b.py").write_text("\n".join(f"def unrelated{i}(x):\n    return x + {i}\n" for i in range(50)))
    results = batch_convert(str(tmp_path), query="truncate", max_tokens=3000, quiet=True,
                            write_output=False, cache_enabled=False)
    by_name = {r.source_file.split("/")[-1]: r for r in results}
    assert "substring" in by_name["a.ts"].markdown
    assert "Relevant to" not in by_name["b.py"].markdown
    assert sum(r.output_tokens for r in results) <= 3000 + 200


def test_cli_query_flag(tmp_path):
    f = tmp_path / "s.ts"
    f.write_text(TS)
    res = CliRunner().invoke(app, ["convert", str(f), "-Q", "truncate", "-o", "-", "-q", "--no-cache"])
    assert res.exit_code == 0 and "substring" in res.stdout
