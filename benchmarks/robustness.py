"""
Run every file in a folder through all detail levels and two token budgets, and
check the invariants Token Shredder promises:

- no crash and no empty output for a non-empty input
- output size never shrinks as the detail level goes up
- --max-tokens is never exceeded
- conversion time per file and level

Usage:  python benchmarks/robustness.py CORPUS_DIR [--csv results.csv]
Prints a per-format summary and every violation. Exit code 1 if anything failed.
"""
import argparse
import csv
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

from token_shredder.main import ConversionError, convert_file, find_batch_files
from token_shredder.metrics import TokenCounter

count = TokenCounter().estimate
WORD = re.compile(r"[A-Za-z]{4,}")
BUDGETS = (500, 2000)


def words(text: str) -> set:
    return {w.lower() for w in WORD.findall(text)}


def run_one(path: Path) -> dict:
    row = {"file": str(path), "format": path.suffix.lower().lstrip(".") or path.name,
           "bytes": path.stat().st_size, "problems": []}
    outputs = {}
    for level in range(1, 6):
        t0 = time.time()
        try:
            r = convert_file(str(path), detail_level=level, show_metrics=False,
                             cache_enabled=False, write_output=False)
        except (ConversionError, Exception) as e:  # noqa: B014 - report everything
            row["problems"].append(f"level {level}: {type(e).__name__}: {str(e)[:120]}")
            continue
        row[f"t{level}"] = round(time.time() - t0, 2)
        row[f"L{level}"] = r.output_tokens
        row["source_tokens"] = r.source_tokens
        outputs[level] = r.markdown
        if not r.markdown.strip() and path.stat().st_size > 0:
            row["problems"].append(f"level {level}: empty output")
    sizes = [row.get(f"L{lv}") for lv in range(1, 6)]
    known = [s for s in sizes if s is not None]
    if known != sorted(known):
        row["problems"].append(f"not monotonic: {sizes}")
    if 3 in outputs and 5 in outputs:
        base = words(outputs[5])
        row["kept3"] = round(100 * len(base & words(outputs[3])) / len(base)) if base else 100
    for budget in BUDGETS:
        try:
            r = convert_file(str(path), max_tokens=budget, show_metrics=False,
                             cache_enabled=False, write_output=False)
            row[f"B{budget}"] = r.output_tokens
            if count(r.markdown) > budget:
                row["problems"].append(f"budget {budget} exceeded: {count(r.markdown)}")
        except Exception as e:
            row["problems"].append(f"budget {budget}: {type(e).__name__}: {str(e)[:120]}")
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus")
    ap.add_argument("--csv")
    args = ap.parse_args()

    files = find_batch_files(args.corpus)
    rows = []
    for i, f in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {f}", file=sys.stderr)
        rows.append(run_one(f))

    by_format = defaultdict(list)
    for r in rows:
        by_format[r["format"]].append(r)
    print(f"\n{'format':8} {'files':>5} {'source':>11} {'level 3':>9} {'saved':>6} {'kept':>5} {'max s':>6}")
    for fmt, rs in sorted(by_format.items()):
        src = sum(r.get("source_tokens", 0) for r in rs)
        l3 = sum(r.get("L3", 0) for r in rs)
        kept = [r["kept3"] for r in rs if "kept3" in r]
        slowest = max((r.get(f"t{lv}", 0) for r in rs for lv in range(1, 6)), default=0)
        saved = f"{100 * (1 - l3 / src):.0f}%" if src else "-"
        print(f"{fmt:8} {len(rs):5} {src:11,} {l3:9,} {saved:>6} "
              f"{(sum(kept) / len(kept) if kept else 0):4.0f}% {slowest:6.1f}")

    problems = [(r["file"], p) for r in rows for p in r["problems"]]
    print(f"\n{len(problems)} problem(s)")
    for f, p in problems:
        print(f"  {f}: {p}")

    if args.csv:
        keys = sorted({k for r in rows for k in r if k != "problems"})
        with open(args.csv, "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=keys + ["problems"])
            w.writeheader()
            for r in rows:
                w.writerow({**r, "problems": " | ".join(r["problems"])})
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
