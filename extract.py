"""CLI:  python extract.py samples --out out.csv --xlsx out.xlsx

Inputs can be folders, PDF/PNG/JPG files, or .zip files (any mix).
"""
import argparse
import sys
from pathlib import Path

import core


def collect(paths):
    items = []
    for p in map(Path, paths):
        if p.is_dir():
            items += [(f.name, f.read_bytes()) for f in sorted(p.iterdir())
                      if f.is_file() and f.suffix.lower() in core.EXTS | {".zip"}]
        elif p.is_file():
            items.append((p.name, p.read_bytes()))
        else:
            sys.exit(f"Not found: {p}")
    return core.expand_uploads(items)


def run(paths, force_heuristic=False, log=print):
    """Process everything under `paths`. Returns (results, notes)."""
    docs, notes = collect(paths)
    if not docs:
        sys.exit("No PDF/PNG/JPG files found.")
    results = []
    for name, data in docs:
        r = core.process_file(name, data, force_heuristic=force_heuristic)
        log(f"{'REVIEW' if r['needs_review'] else 'ok    '} {name}  {r['reasons']}")
        results.append(r)
    return results, notes


def main():
    sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description="Extract invoices and receipts to CSV / XLSX.")
    ap.add_argument("inputs", nargs="+", help="folder(s), file(s) or .zip(s)")
    ap.add_argument("--out", default="out.csv")
    ap.add_argument("--xlsx", help="also write an XLSX file (documents / needs_review / line_items sheets)")
    ap.add_argument("--sheet", action="store_true", help="append to Google Sheet if env configured")
    ap.add_argument("--no-key", action="store_true", help="force the offline heuristic extractor even if a key is set")
    a = ap.parse_args()
    if a.no_key or core.active_provider() == "none":
        scans = ("scans and photos are read by OCR (" + core.ocr_label() + ", confidence capped)"
                 if core.ocr_available() else
                 "scans and photos are flagged (they need GEMINI_API_KEY or an OCR backend: requirements-ocr.txt)")
        print("NOTE: heuristic text extractor (no AI key: set GROQ_API_KEY or GEMINI_API_KEY). "
              "Lower confidence; " + scans + ".")
    else:
        print("AI provider -", core.provider_label())
    results, notes = run(a.inputs, force_heuristic=a.no_key)
    for n in notes:
        print("NOTE:", n)
    df = core.to_df(results)
    df.to_csv(a.out, index=False)
    if a.xlsx:
        Path(a.xlsx).write_bytes(core.xlsx_bytes(df, core.items_df(results)))
    if a.sheet:
        print(core.push_to_sheet(df))
    s = core.summarize(df)
    totals = ", ".join(f"{c} {v:,.2f}" for c, v in s["totals"].items())
    print(f"Wrote {a.out}: {s['files']} processed, {s['flagged']} need review. Totals: {totals}")


if __name__ == "__main__":
    main()
