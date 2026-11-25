"""Data file profiles: streaming profiler, CSV / JSONL / XLSX detail levels."""
import json
import random

import pytest

from token_shredder.main import convert_file
from token_shredder.profiling import profile_records, render_profile, MAX_DISTINCT


def _convert(path, tmp_path, level):
    return convert_file(str(path), output_path=str(tmp_path / f"o{level}.md"), detail_level=level,
                        show_metrics=False, cache_enabled=False).markdown


def _all_levels(path, tmp_path):
    return [_convert(path, tmp_path, lv) for lv in range(1, 6)]


def _assert_monotonic(outs, upto=5):
    lengths = [len(o) for o in outs[:upto]]
    assert lengths == sorted(lengths), lengths


def test_profile_stats():
    rows = [{"price": i * 0.5, "n": i, "title": "t" * (3 + i % 5), "opt": 1 if i % 2 else None} for i in range(40)]
    rows[0]["extra"] = True
    p = profile_records(rows)
    assert p.rows == 40
    f = p.fields
    assert f["price"].num_min == 0 and f["price"].num_max == 19.5 and not f["price"].all_int
    assert f["n"].all_int and f["n"].num_max == 39
    assert (f["title"].len_min, f["title"].len_max) == (3, 7)
    assert f["extra"].n == 1 and f["opt"].types["null"] == 20
    out = render_profile(p, 3)
    assert "Rows: 40" in out
    assert "- `price`: number 0–19.5 (int: no)" in out
    assert "`extra`: boolean" in out and "1/40" in out


def test_nested_fields_and_dates():
    rows = [{"user": {"login": f"u{i % 2}"}, "at": f"2024-01-{i + 1:02d}T10:00:00Z"} for i in range(5)]
    out = render_profile(profile_records(rows), 3)
    assert "`user`: object" in out and "`user.login`" in out
    assert "(date) 2024-01-01T10:00:00Z–2024-01-05T10:00:00Z" in out


def test_enum_detection():
    rows = [{"status": "open" if i % 5 < 3 else "closed", "id": f"id{i}"} for i in range(100)]
    out = render_profile(profile_records(rows), 3)
    assert "enum: open ×60 (60%), closed ×40 (40%)" in out
    assert "`id`: string" in out and "enum" not in out.split("`id`")[1]
    # few unique rows -> no enum
    out2 = render_profile(profile_records([{"a": "x"}, {"a": "y"}]), 3)
    assert "enum" not in out2
    # repeated values in few rows -> enum
    assert "enum" in render_profile(profile_records([{"a": "x"}, {"a": "x"}, {"a": "y"}]), 3)


def test_level_1_and_2_detail():
    rows = [{"a": i, "b": "text"} for i in range(30)]
    p = profile_records(rows)
    l1, l2 = render_profile(p, 1), render_profile(p, 2)
    assert "- `a`: number" in l1 and "0–29" not in l1
    assert "0–29" in l2


def test_bounded_memory():
    rows = ({"id": f"unique-{i}-" + "x" * 500, "n": i, "flag": bool(i % 2)} for i in range(200_000))
    p = profile_records(rows)
    assert p.rows == 200_000
    st = p.fields["id"]
    assert st.overflow and len(st.distinct) == 0
    assert len(p.fields["n"].distinct) == 0 and p.fields["n"].overflow
    assert len(st.examples) <= 3
    assert len(p.fields["flag"].distinct) <= MAX_DISTINCT


def test_max_rows():
    p = profile_records(({"a": i} for i in range(100)), max_rows=10)
    assert p.rows == 10 and p.truncated


def test_jsonl_bad_line(tmp_path):
    src = tmp_path / "e.jsonl"
    lines = [json.dumps({"id": i, "name": f"n{i}"}) for i in range(60)]
    lines[3:3] = ["{not json", "", "oops", "[1,"]
    src.write_text("\n".join(lines) + "\n")
    outs = _all_levels(src, tmp_path)
    assert "3 lines could not be parsed" in outs[2]
    assert "Rows: 60" in outs[2]
    assert "3 lines could not be parsed" in outs[3]
    body = outs[3].split("```jsonl\n")[1].split("\n```")[0].split("\n")
    assert [json.loads(x) for x in body] == [{"id": i, "name": f"n{i}"} for i in range(60)]
    assert src.read_text().strip() in outs[4]


def test_ndjson_registered(tmp_path):
    src = tmp_path / "e.ndjson"
    src.write_text("\n".join(json.dumps({"id": i, "tag": "x" * 40}) for i in range(50)))
    assert "Rows: 50" in _convert(src, tmp_path, 3)


def test_jsonl_monotonic(tmp_path):
    src = tmp_path / "d.jsonl"
    random.seed(1)
    src.write_text("\n".join(json.dumps({"id": i, "status": random.choice(["a", "b"]),
                                         "title": "Fix crash in module " + str(i), "score": random.random()})
                             for i in range(500)))
    outs = _all_levels(src, tmp_path)
    _assert_monotonic(outs)
    assert len(outs[2]) * 10 < len(outs[3])


def test_json_object_with_list_uses_profile(tmp_path):
    data = {"total": 200, "items": [{"id": i, "state": "open" if i % 2 else "closed", "title": f"Issue {i}"}
                                    for i in range(200)]}
    src = tmp_path / "d.json"
    src.write_text(json.dumps(data, indent=2))
    outs = _all_levels(src, tmp_path)
    _assert_monotonic(outs)
    assert "each item (200 items)" in outs[2] and "enum: " in outs[2]
    assert json.loads(outs[3].split("\n", 1)[1].rsplit("```", 1)[0]) == data


def _write_csv(path, n):
    random.seed(2)
    lines = ["id,name,price,status,created"]
    for i in range(n):
        lines.append(f"{i},item {i},{random.random() * 100:.2f},{random.choice(['open', 'closed'])},2024-01-{i % 28 + 1:02d}")
    path.write_text("\n".join(lines) + "\n")


def test_csv_10k_rows(tmp_path):
    src = tmp_path / "big.csv"
    _write_csv(src, 10_000)
    outs = _all_levels(src, tmp_path)
    _assert_monotonic(outs, 5)
    assert "Rows: 10,000" in outs[2]
    assert "enum: " in outs[2]
    assert "`id`" in outs[0] and "number" not in outs[0]
    assert len(outs[2]) * 20 < len(outs[3])
    assert "more rows" not in outs[3] and outs[3].count("\n") >= 10_001  # all rows, as CSV
    assert outs[2].count("\n| ") <= 7  # header + sep + 5 sample rows


def test_csv_small_returns_full_table(tmp_path):
    src = tmp_path / "s.csv"
    src.write_text("a,b\n1,2\n3,4\n")
    outs = _all_levels(src, tmp_path)
    _assert_monotonic(outs, 5)
    assert "3,4" in outs[2]


def test_xlsx_levels(tmp_path):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Data"
    ws.append([])
    ws.append(["id", "name", "price", "status"])
    for i in range(300):
        ws.append([i, f"product number {i}", i * 1.5, "open" if i % 3 else "closed"])
    ws2 = wb.create_sheet("Small")
    ws2.append(["x", "y"])
    ws2.append([1, "a|b"])
    p = tmp_path / "d.xlsx"
    wb.save(p)
    outs = _all_levels(p, tmp_path)
    _assert_monotonic(outs)
    assert "`price`" in outs[0]
    assert "enum: open ×200 (67%), closed ×100 (33%)" in outs[2]
    assert "| 299 | product number 299 | 448.5 | open |" in outs[3]
    assert "| 299 | product number 299 | 448.5 | open |" in outs[4]
    assert "| 1 | a\\|b |" in outs[2]
    assert len(outs[2]) * 5 < len(outs[3])


def test_csv_semicolon_and_tsv_and_monotonic_with_raw(tmp_path):
    from token_shredder.main import convert_file
    rows = "\n".join(f"{i};name{i};{i * 1.5}" for i in range(300))
    semi = tmp_path / "s.csv"
    semi.write_text("id;name;score\n" + rows + "\n")
    tsv = tmp_path / "t.tsv"
    tsv.write_text("id\tname\tscore\n" + rows.replace(";", "\t") + "\n")
    for f in (semi, tsv):
        outs = [convert_file(str(f), detail_level=lv, show_metrics=False, cache_enabled=False,
                             write_output=False).markdown for lv in range(1, 6)]
        assert "score" in outs[0] and "name" in outs[0]
        assert [len(o) for o in outs] == sorted(len(o) for o in outs)


# --- map-like dicts, constants, examples ------------------------------------------

def _lock(n=300):
    return {"name": "app", "lockfileVersion": 3,
            "packages": {f"node_modules/p{i}": {"version": f"1.{i}.0", "resolved": f"https://registry.npmjs.org/p{i}/-/p{i}-1.{i}.0.tgz",
                                                "integrity": "sha512-" + "a" * 60, **({"dev": True} if i % 8 == 0 else {})}
                         for i in range(n)}}


def test_map_like_dict_is_profiled_not_listed(tmp_path):
    f = tmp_path / "lock.json"
    f.write_text(json.dumps(_lock(), indent=2))
    for level in (2, 3):
        out = _convert(f, tmp_path, level)
        assert "300 entries" in out
        assert "`version`" in out and "`resolved`" in out and "`dev`" in out
    l2 = _convert(f, tmp_path, 2)
    assert "node_modules/p150" not in l2 and len(l2) < 2500          # level 2: examples only
    l3 = _convert(f, tmp_path, 3)
    assert "p150: 1.150.0" in l3                                       # level 3: version index
    assert len(l3) < len(json.dumps(_lock())) / 2
    l3 = _convert(f, tmp_path, 3)
    assert "`dev`: boolean = true, 38/300" in l3


def test_small_dict_of_records_is_not_a_map(tmp_path):
    f = tmp_path / "small.json"
    f.write_text(json.dumps({"a": {"x": 1}, "b": {"x": 2}, "c": {"x": 3}}))
    assert "map of" not in _convert(f, tmp_path, 3)


def test_varying_nested_keys_are_not_flattened():
    rows = [{"deps": {f"lib{i}-{j}": "1.0" for j in range(20)}, "id": i} for i in range(5)]
    out = render_profile(profile_records(rows), 3)
    assert "`deps`: object" in out and "deps.lib" not in out


def test_constant_field_renders_as_equals():
    rows = [{"type": "Feature", "ok": True, "n": 7, "id": i} for i in range(10)]
    out = render_profile(profile_records(rows), 3)
    assert "- `type`: string = Feature" in out
    assert "- `ok`: boolean = true" in out
    assert "- `n`: number = 7" in out
    assert "enum" not in out.split("`id`")[0]


def test_examples_one_for_urls_and_ids_three_for_short_text():
    rows = [{"url": f"https://example.com/items/{i}", "uid": f"3f2b8c1e-0000-4000-8000-{i:012d}",
             "word": w} for i, w in enumerate(["red", "green", "blue", "cyan"] * 3)]
    rows += [{"url": f"https://example.com/items/x{i}", "uid": f"3f2b8c1e-0000-4000-8000-9{i:011d}",
              "word": f"w{i}"} for i in range(30)]
    out = render_profile(profile_records(rows), 3)
    url_line = next(l for l in out.splitlines() if l.startswith("- `url`"))
    uid_line = next(l for l in out.splitlines() if l.startswith("- `uid`"))
    word_line = next(l for l in out.splitlines() if l.startswith("- `word`"))
    assert url_line.count('"') == 2 and uid_line.count('"') == 2
    assert word_line.count('"') == 6
