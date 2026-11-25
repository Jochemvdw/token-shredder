"""Tests for XLSX/DOCX/CSV/TOML converter fixes."""
from docx import Document
from openpyxl import Workbook

from token_shredder.converters.csv_converter import CSVConverter
from token_shredder.converters.docx_converter import DOCXConverter
from token_shredder.converters.toml_converter import TOMLConverter
from token_shredder.converters.xlsx_converter import XLSXConverter
from token_shredder.models import ConversionOptions

OPTS = ConversionOptions(detail_level=3)


def _xlsx(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.append(["A", "B"])
    ws.append([1, 2])
    ws.append([None, "=SUM(A1:A2)"])
    ws.append(["x|y", "ok"])
    p = tmp_path / "t.xlsx"
    wb.save(p)
    return str(p)


def test_xlsx_formula_row_kept_with_empty_first_cell(tmp_path):
    md = XLSXConverter().convert_to_markdown(_xlsx(tmp_path), OPTS)
    assert "|  | =SUM(A1:A2) |" in md


def test_xlsx_pipe_escaped(tmp_path):
    md = XLSXConverter().convert_to_markdown(_xlsx(tmp_path), OPTS)
    assert "| x\\|y | ok |" in md
    assert "| --- | --- |" in md


def test_xlsx_blank_line_before_table(tmp_path):
    lines = XLSXConverter().convert_to_markdown(_xlsx(tmp_path), OPTS).split("\n")
    idx = lines.index("| A | B |")
    assert lines[idx - 1] == ""


def test_docx_lists(tmp_path):
    d = Document()
    d.add_paragraph("one", style="List Bullet")
    d.add_paragraph("two", style="List Bullet")
    d.add_paragraph("first", style="List Number")
    d.add_paragraph("plain")
    p = tmp_path / "t.docx"
    d.save(p)
    md = DOCXConverter().convert_to_markdown(str(p), OPTS)
    assert "- one\n- two" in md
    assert "1. first" in md
    assert "\nplain" in md


def test_docx_table_pipe_and_blank_lines(tmp_path):
    d = Document()
    d.add_paragraph("intro")
    t = d.add_table(rows=2, cols=2)
    t.cell(0, 0).text = "H1"
    t.cell(0, 1).text = "H2"
    t.cell(1, 0).text = "a|b"
    t.cell(1, 1).text = "c"
    p = tmp_path / "t.docx"
    d.save(p)
    lines = DOCXConverter().convert_to_markdown(str(p), OPTS).split("\n")
    i = lines.index("| H1 | H2 |")
    assert lines[i - 1] == ""
    assert "| a\\|b | c |" in lines
    assert lines[lines.index("| a\\|b | c |") + 1] == ""


def test_csv_newline_pipe_and_blank_line(tmp_path):
    p = tmp_path / "t.csv"
    rows = "".join(f"{i},plain{i}\n" for i in range(300))
    p.write_text('a,b\n"line1\nline2","x|y"\n' + rows, encoding="utf-8")
    md = CSVConverter().convert_to_markdown(str(p), OPTS)  # level 3: profile + sample rows
    lines = md.split("\n")
    assert lines[0] == ""
    assert "| line1 line2 | x\\|y |" in lines
    # Small files: the data itself is shorter than a profile, so it is returned whole.
    small = tmp_path / "small.csv"
    small.write_text('a,b\n"line1\nline2","x|y"\n3,4\n', encoding="utf-8")
    assert '"line1\nline2","x|y"' in CSVConverter().convert_to_markdown(str(small), OPTS)


def test_csv_non_utf8(tmp_path):
    p = tmp_path / "t.csv"
    p.write_bytes(b"a,b\n\xff\xfe,1\n")
    md = CSVConverter().convert_to_markdown(str(p), OPTS)
    assert "Error" not in md


def test_toml_nested_tables(tmp_path):
    p = tmp_path / "t.toml"
    p.write_text('title = "x"\n[tool]\na = 1\nb = "two"\n[tool.sub]\nc = true\n', encoding="utf-8")
    md = TOMLConverter().convert_to_markdown(str(p), OPTS)
    assert "[tool]" in md
    assert "[tool.sub]" in md
    assert "c: True" in md
    assert 'b: "two"' in md


def test_toml_detail5_returns_original(tmp_path):
    p = tmp_path / "t.toml"
    text = "[a]\nb = 1\n"
    p.write_text(text, encoding="utf-8")
    assert TOMLConverter().convert_to_markdown(str(p), ConversionOptions(detail_level=5)) == text


def test_toml_non_utf8_no_error(tmp_path):
    p = tmp_path / "t.toml"
    p.write_bytes(b'# \xff\n[a]\nb = 1\n')
    md = TOMLConverter().convert_to_markdown(str(p), ConversionOptions(detail_level=5))
    assert "[a]" in md


def test_toml_non_utf8_structure(tmp_path):
    p = tmp_path / "t.toml"
    p.write_bytes(b'# \xff\n[a]\nb = 1\n')
    md = TOMLConverter().convert_to_markdown(str(p), OPTS)
    assert "[a]" in md and "Error" not in md
