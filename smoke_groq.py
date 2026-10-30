"""Live Groq smoke test (needs a real key and network):   python smoke_groq.py

Runs the 9 bundled samples through the Groq path and prints one row per file: file, type, vendor, total,
needs_review, model used, plus whether the values match what the sample generator printed. Groq reads text only, so
the 8 text-layer PDFs go to the text model; the PNG receipt has no text layer, so it is OCR'd first (RapidOCR, see
ocr.py / requirements-ocr.txt; or Docling) and the OCR text goes to the same model. Without any OCR backend it is
flagged ("scanned image: needs a vision provider (Gemini) or an OCR backend").
`python verify.py` proves the wiring offline against a fake server; this script is the only thing that exercises the
real API and the real model's accuracy.

    $env:GROQ_API_KEY = "gsk_..."      # or put it in .env
    python smoke_groq.py
Optional: GROQ_TEXT_MODEL to try another model (list ids: GET https://api.groq.com/openai/v1/models).
"""
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(errors="replace")

import core  # noqa: E402
import llm  # noqa: E402
import make_samples  # noqa: E402


def main() -> int:
    if not os.getenv("GROQ_API_KEY", "").strip():
        print("GROQ_API_KEY is not set. Get a free key at https://console.groq.com/keys, then run again.")
        return 2
    os.environ["LLM_PROVIDER"] = "groq"            # even if a Gemini key is also present
    print(f"Provider: {core.provider_label()}\nBase URL: {llm.groq_base_url()}\n")
    rows, t0 = [], time.time()
    for g in make_samples.ground_truth():
        r = core.process_file(g["file"], (ROOT / "samples" / g["file"]).read_bytes())
        d = r["document"]
        got = dict(doc_type=d.doc_type, vendor=(d.vendor or "").lower(), number=d.document_number, date=d.date,
                   currency=d.currency, tax=d.tax, total=d.total)
        exp = dict(doc_type=g["doc_type"], vendor=g["vendor"].lower(), number=g["number"], date=g["date"],
                   currency=g["currency"], tax=g["tax"], total=g["total"])
        bad = [k for k in exp if got[k] != exp[k]]
        rows.append((g["file"], d.doc_type or "-", (d.vendor or "-")[:28], "-" if d.total is None else f"{d.total:,.2f}",
                     "YES" if r["needs_review"] else "no", r["model"] or "-", r["source"] or "-",
                     "ok" if not bad else ("not read" if d.total is None and not d.vendor else "differs: " + ",".join(bad)),
                     r["reasons"]))
        print(f"  done {g['file']}", flush=True)
    head = ("file", "type", "vendor", "total", "needs_review", "model", "source", "vs ground truth")
    table = [head] + [r[:8] for r in rows]
    widths = [max(len(str(row[i])) for row in table) for i in range(len(head))]
    print()
    for n, row in enumerate(table):
        print("  ".join(str(c).ljust(w) for c, w in zip(row, widths)))
        if n == 0:
            print("  ".join("-" * w for w in widths))
    flagged = [r for r in rows if r[4] == "YES"]
    print(f"\n{len(rows)} files in {time.time() - t0:.0f}s, {len(flagged)} need review "
          "(expected: inv3_greenleaf_catering.pdf, the deliberately wrong total; plus rcpt4_harbor_grill.png "
          "only if no OCR backend is installed).")
    for r in flagged:
        print(f"  {r[0]}: {r[8]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
