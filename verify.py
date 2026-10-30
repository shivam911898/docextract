"""One-command self-check:  python verify.py

Runs everything that can be verified offline, with no API key and no network:
  1. CLI on samples/ (no-key mode): 9 processed, wrong-total invoice flagged, clean docs match ground truth,
     CSV + XLSX (documents / needs_review / line_items sheets) written.
  2. ZIP intake: unpacks samples, ignores junk, rejects nested zips and path tricks.
  3. Gemini code path against a local FAKE Gemini server: retries on 503, parses the JSON, and degrades to a
     "Needs review" row (not a crash) when the API keeps failing. This proves our wiring, not Google's accuracy.
  4. Groq code path against a local FAKE OpenAI-compatible server: text PDFs go to the text model (Groq has no vision
     model), scans / photos are OCR'd first (OCR stubbed here) or become Needs review rows when no OCR backend exists,
     Docling beats the lightweight OCR, OCR text lowers confidence, 429 is retried, persistent 500 / malformed JSON /
     401 become Needs review rows, provider selection rules, CLI wiring. Proves our wiring, not Groq's accuracy (see
     smoke_groq.py).
  5. Streamlit app smoke test (AppTest): status pill (demo / Groq / OCR missing), MAX_FILES cap, "Try the 9 sample
     documents" summary cards with "USD 2,259.22" style totals.
  6. OCR helpers (row grouping, spacing repair, Tesseract adapter with a stub) plus, only when an OCR backend imports
     (pip install -r requirements-ocr.txt), the real thing: the PNG receipt is read in no-key mode and through the fake
     Groq server, a scanned PDF is OCR'd, the wrong-total Greenleaf invoice is still flagged. Skipped otherwise.
  7. Only if docling is installed: the optional EXTRACT_BACKEND=docling path (incl. OCR of the PNG receipt).
"""
import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
os.chdir(ROOT)
for _k in ("GEMINI_API_KEY", "GROQ_API_KEY"):
    os.environ[_k] = ""                # empty (not absent) so .env can never switch on real API calls here
sys.path.insert(0, str(ROOT))

import core  # noqa: E402
import llm  # noqa: E402
import make_samples  # noqa: E402
import ocr  # noqa: E402

for _k in ("LLM_PROVIDER", "GEMINI_BASE_URL", "GROQ_BASE_URL", "GROQ_TEXT_MODEL", "GROQ_FALLBACK_MODEL", "OCR_BACKEND"):
    os.environ.pop(_k, None)           # a stray .env must not change what is being verified
core.MAX_FILES = 10

failures = []


def check(cond, msg):
    print(("PASS  " if cond else "FAIL  ") + msg)
    if not cond:
        failures.append(msg)


# --------------------------------------------------------------------------- 1. CLI
def stage_cli():
    print("\n[1] CLI on samples/ (no-key mode, OCR switched off so the PNG stays flagged; OCR is tested in [6])")
    with tempfile.TemporaryDirectory() as tmp:
        out, xlsx = Path(tmp) / "out.csv", Path(tmp) / "out.xlsx"
        cp = subprocess.run([sys.executable, "extract.py", "samples", "--out", str(out), "--xlsx", str(xlsx), "--no-key"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace",
                            env={**os.environ, "OCR_BACKEND": "none"})
        print("\n".join("      " + l for l in cp.stdout.splitlines()))
        check(cp.returncode == 0, f"extract.py exit code 0 (got {cp.returncode}) {cp.stderr.strip()[-200:]}")
        df = pd.read_csv(out)
        flagged = df[df.needs_review]
        check(len(df) == 9, f"processed = 9 (got {len(df)})")
        check(len(flagged) >= 1, f"flagged >= 1 (got {len(flagged)})")
        bad = df[df.file == "inv3_greenleaf_catering.pdf"].iloc[0]
        check(bool(bad.needs_review) and "total" in str(bad.review_reason),
              f"wrong-total invoice flagged: {bad.review_reason}")
        check(set(flagged.file) == {"inv3_greenleaf_catering.pdf", "rcpt4_harbor_grill.png"},
              f"flagged set = wrong-total invoice + the PNG receipt (needs key): {sorted(flagged.file)}")
        png = df[df.file == "rcpt4_harbor_grill.png"].iloc[0]
        check(core.SCANNED_MSG in str(png.review_reason), f"PNG without an AI/OCR route: {png.review_reason}")
        check(list(df.columns)[-2:] == ["mode", "source"] and set(df.source.dropna()) == {"text"},
              f"CSV has a source column: text-layer PDFs say 'text', the unreadable PNG is blank ({sorted(df.source.dropna().unique())})")
        check({"invoice", "receipt"} <= set(df.doc_type.dropna()), "both document types detected")
        # accuracy against what the generator actually printed (text-layer files only)
        wrong = []
        for gt in (g for g in make_samples.ground_truth() if g["text_layer"]):
            row = df[df.file == gt["file"]].iloc[0]
            got = dict(doc_type=row.doc_type, vendor=str(row.vendor).lower(), number=str(row.document_number),
                       date=row.date, currency=row.currency, total=round(float(row.total), 2),
                       tax=round(float(row.tax), 2))
            exp = dict(doc_type=gt["doc_type"], vendor=gt["vendor"].lower(), number=gt["number"], date=gt["date"],
                       currency=gt["currency"], total=gt["total"], tax=gt["tax"])
            if got != exp:
                wrong.append((gt["file"], {k: (got[k], exp[k]) for k in exp if got[k] != exp[k]}))
        check(not wrong, f"8 text-layer files match ground truth (doc_type, vendor, number, date, currency, tax, total) {wrong}")
        sheets = pd.read_excel(xlsx, sheet_name=None)
        check(set(sheets) == {"documents", "needs_review", "line_items"}, f"XLSX sheets: {list(sheets)}")
        check(len(sheets["needs_review"]) == len(flagged), "XLSX needs_review sheet row count = flagged count")
        n_items = sum(g["n_items"] for g in make_samples.ground_truth() if g["text_layer"])
        check(len(sheets["line_items"]) == n_items, f"XLSX line_items rows = {n_items} (got {len(sheets['line_items'])})")
        # the MAX_FILES cap protects the UI only: the CLI must process every file it is given
        big = Path(tmp) / "big"
        big.mkdir()
        for i in range(core.MAX_FILES + 3):
            (big / f"copy{i:02d}.pdf").write_bytes(Path("samples/inv1_acme_supplies.pdf").read_bytes())
        cp = subprocess.run([sys.executable, "extract.py", str(big), "--out", str(Path(tmp) / "big.csv"), "--no-key"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace")
        check(cp.returncode == 0 and len(pd.read_csv(Path(tmp) / "big.csv")) == core.MAX_FILES + 3,
              f"CLI is uncapped: {core.MAX_FILES + 3} files in, {core.MAX_FILES + 3} rows out")


# --------------------------------------------------------------------------- 2. ZIP
def stage_zip():
    print("\n[2] ZIP intake")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for p in sorted(Path("samples").iterdir()):
            z.writestr(f"batch/{p.name}", p.read_bytes())
        z.writestr("__MACOSX/._junk.pdf", b"x")
        z.writestr("notes.txt", b"hello")
        z.writestr("../../evil.pdf", b"%PDF-1.4 not really")
        z.writestr("nested.zip", b"PK")
    docs, notes = core.expand_uploads([("batch.zip", buf.getvalue()), ("loose.png", Path("samples/rcpt4_harbor_grill.png").read_bytes()),
                                       ("broken.zip", b"not a zip")])
    names = [n for n, _ in docs]
    check(len(docs) == 11, f"9 samples + evil.pdf (path-sanitised) + loose.png = 11 docs (got {len(docs)})")
    check("evil.pdf" in names and not any(".." in n for n in names), "path traversal stripped from zip member names")
    check(any("notes.txt" in n for n in notes) and any("broken.zip" in n for n in notes), "unsupported / invalid inputs reported, not crashed")


# --------------------------------------------------------------------------- 3. fake Gemini
CANNED = {"doc_type": "invoice", "vendor": "Acme Office Supplies Inc.", "document_number": "AC-10482",
          "date": "2025-03-14", "currency": "USD", "subtotal": 184.47, "tax": 14.76, "total": 199.23,
          "line_items": [{"description": "Copy Paper", "qty": 20, "unit_price": 4.5, "amount": 90.0},
                         {"description": "Pens", "qty": 6, "unit_price": 8.25, "amount": 49.5},
                         {"description": "Stapler", "qty": 3, "unit_price": 14.99, "amount": 44.97}],
          "confidence": 0.95}


class FakeGemini(BaseHTTPRequestHandler):
    calls, fail_first = [], 2

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        FakeGemini.calls.append((self.path, body))
        if len(FakeGemini.calls) <= FakeGemini.fail_first:
            code, payload = 503, {"error": {"code": 503, "message": "The model is overloaded.", "status": "UNAVAILABLE"}}
        else:
            code, payload = 200, {"candidates": [{"content": {"role": "model", "parts": [{"text": json.dumps(CANNED)}]},
                                                  "finishReason": "STOP", "index": 0}]}
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def stage_gemini_mock():
    print("\n[3] Gemini path vs local fake server (retry on 503, JSON parsing, graceful failure)")
    srv = HTTPServer(("127.0.0.1", 0), FakeGemini)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    os.environ["GEMINI_API_KEY"], os.environ["GEMINI_BASE_URL"] = "fake-key", f"http://127.0.0.1:{srv.server_port}"
    core.GEMINI_RETRY_DELAY = 0.05
    data = Path("samples/inv1_acme_supplies.pdf").read_bytes()
    try:
        r = core.process_file("inv1_acme_supplies.pdf", data)
        path, body = FakeGemini.calls[-1]
        check(r["mode"] == "gemini" and len(FakeGemini.calls) == 3, f"2x 503 then success = 3 HTTP calls (got {len(FakeGemini.calls)})")
        check(f"{core.GEMINI_MODEL}:generateContent" in path and core.GEMINI_MODEL == "gemini-3.1-flash-lite", f"model in URL: {path}")
        check(b"inlineData" in body or b"inline_data" in body, "page image sent as inline data")
        d = r["document"]
        check((d.doc_type, d.document_number, d.total) == ("invoice", "AC-10482", 199.23) and not r["needs_review"],
              "model JSON parsed into Document and validated clean")
        FakeGemini.calls.clear(); FakeGemini.fail_first = 99          # API down for good
        r = core.process_file("inv1_acme_supplies.pdf", data)
        check(len(FakeGemini.calls) == core.GEMINI_RETRY_ATTEMPTS, f"gave up after {core.GEMINI_RETRY_ATTEMPTS} attempts (got {len(FakeGemini.calls)})")
        check(r["needs_review"] and "extraction error" in r["reasons"], "persistent failure becomes a Needs review row, no crash")
    finally:
        srv.shutdown()
        os.environ["GEMINI_API_KEY"] = ""
        os.environ.pop("GEMINI_BASE_URL", None)


# --------------------------------------------------------------------------- 4. fake Groq (OpenAI-compatible)
def _canned_from_truth(file):
    """What a perfect model would return for a sample, built from the generator's ground truth."""
    g = next(g for g in make_samples.ground_truth() if g["file"] == file)
    d = next(d for d in make_samples.DOCS if d["file"] == file)
    items = [dict(description=n, qty=q, unit_price=p, amount=round(q * p, 2)) for n, q, p in d["items"]]
    return dict(doc_type=g["doc_type"], vendor=g["vendor"], document_number=g["number"], date=g["date"],
                currency=g["currency"], line_items=items, subtotal=g["subtotal"], tax=g["tax"], tip=g["tip"],
                total=g["total"], payment_method=d.get("payment"), confidence=0.9)


def _chat_ok(content):
    return {"id": "chatcmpl-test", "object": "chat.completion", "model": "fake",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}]}


class FakeGroq(BaseHTTPRequestHandler):
    """Minimal OpenAI-compatible /chat/completions. Scripted replies (status, headers, payload) are consumed from
    `queue`, then `fallback`; None means "answer like a good model": the receipt JSON when the prompt carries the
    Harbor Street Grill text, the invoice JSON otherwise."""
    queue, fallback, seen = [], None, []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        FakeGroq.seen.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body})
        step = FakeGroq.queue.pop(0) if FakeGroq.queue else FakeGroq.fallback
        if step is None:
            receipt = "HARBOR" in body["messages"][0]["content"]       # OCR may print it as HARBORSTREET GRILL
            step = (200, {}, _chat_ok(json.dumps(CANNED_RECEIPT if receipt else CANNED)))
        status, headers, payload = step
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        for k, v in headers.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


CANNED_RECEIPT = _canned_from_truth("rcpt4_harbor_grill.png")


def stage_groq_mock():
    print("\n[4] Groq path vs local fake OpenAI-compatible server (text model only; scans need OCR or Gemini)")
    import re

    from PIL import Image

    def fake(queue=(), fallback=None):
        FakeGroq.queue, FakeGroq.fallback = list(queue), fallback
        FakeGroq.seen.clear()

    def err(status, msg, headers=None):
        return (status, headers or {}, {"error": {"message": msg, "type": "test_error"}})

    def run(name, data=None):
        return core.process_file(name, data if data is not None else (Path("samples") / name).read_bytes())

    def content_of(i=-1):
        return FakeGroq.seen[i]["body"]["messages"][0]["content"]

    # provider selection rules (no server needed)
    def prov(**env):
        saved = {k: os.environ.get(k) for k in ("LLM_PROVIDER", "GROQ_API_KEY", "GEMINI_API_KEY")}
        for k in saved:
            os.environ[k] = env.get(k, "")
        try:
            return llm.provider()
        finally:
            for k, v in saved.items():
                os.environ[k] = v or ""
    check(prov() == "none", "provider: no keys -> none")
    check(prov(GROQ_API_KEY="g") == "groq" and prov(GEMINI_API_KEY="m") == "gemini", "provider: the one key that is set wins")
    check(prov(GROQ_API_KEY="g", GEMINI_API_KEY="m") == "groq", "provider: both keys -> groq is the default")
    check(prov(GROQ_API_KEY="g", GEMINI_API_KEY="m", LLM_PROVIDER="gemini") == "gemini", "provider: LLM_PROVIDER=gemini overrides")
    check(prov(GROQ_API_KEY="g", LLM_PROVIDER="none") == "none", "provider: LLM_PROVIDER=none forces the offline mode")
    check(prov(GEMINI_API_KEY="m", LLM_PROVIDER="groq") == "none", "provider: LLM_PROVIDER=groq without a Groq key -> none")
    keys = set(re.findall(r'"(\w+)":', core.SCHEMA_HINT))
    check(keys == set(core.Document.model_fields) | set(core.LineItem.model_fields),
          "prompt schema hint lists exactly the Document + LineItem fields")
    check((llm.groq_text_model(), llm.groq_base_url(), llm.GROQ_MAX_TOKENS >= 2048) ==
          ("openai/gpt-oss-120b", "https://api.groq.com/openai/v1", True),
          "default Groq text model, base URL, max_tokens >= 2048 (reasoning models need headroom)")

    srv = HTTPServer(("127.0.0.1", 0), FakeGroq)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    os.environ["GROQ_API_KEY"], os.environ["GROQ_BASE_URL"] = "fake-groq-key", f"http://127.0.0.1:{srv.server_port}/openai/v1"
    llm.GROQ_RETRY_DELAY = 0.01
    try:
        # --- text-layer PDF -> text model
        fake()
        r = run("inv1_acme_supplies.pdf")
        req, c = FakeGroq.seen[-1], content_of()
        check(len(FakeGroq.seen) == 1 and req["path"] == "/openai/v1/chat/completions" and req["auth"] == "Bearer fake-groq-key",
              f"text PDF: one POST to /chat/completions with the bearer key ({req['path']})")
        b = req["body"]
        check(b["model"] == "openai/gpt-oss-120b" and b["response_format"] == {"type": "json_object"} and b["temperature"] == 0
              and b["max_tokens"] >= 2048, f"text PDF: gpt-oss text model, JSON mode, temperature 0, max_tokens {b['max_tokens']}")
        check(isinstance(c, str) and "JSON" in c and "doc_type" in c and "Acme Office Supplies" in c,
              "text PDF: prompt (plain string) names JSON + the schema and carries the PDF text")
        d = r["document"]
        check(r["mode"] == "groq" and r["model"] == b["model"] and (d.doc_type, d.document_number, d.total) == ("invoice", "AC-10482", 199.23)
              and not r["needs_review"], "text PDF: JSON parsed into Document, validated clean, result tagged groq + model")

        # --- scans / photos: Groq has no vision model, so no API call is made for the image itself. The text comes
        # from OCR (Docling if installed, else RapidOCR / Tesseract); with neither -> Needs review.
        real_avail, real_docling, real_ocr_text, real_ocr_ok = core.docling_available, core.docling_text, core.ocr_text, ocr.available
        src = Image.open(io.BytesIO(core.render_first_page(Path("samples/inv1_acme_supplies.pdf").read_bytes(), "x.pdf"))).convert("RGB")
        pdf = io.BytesIO(); src.save(pdf, "PDF", save_all=True, append_images=[src] * 3)
        no_text = core.pdf_text(pdf.getvalue(), "scan.pdf").strip() == ""
        want = "extraction error: " + core.SCANNED_MSG
        ocr_text = "HARBOR STREET GRILL\n77 Pier Road, Boston, MA 02110\nCheck 5521  Jun 21, 2025\nClam Chowder 9.50\nTotal 90.68"
        try:
            core.docling_available = lambda: False
            os.environ["OCR_BACKEND"] = "none"
            fake()
            r1 = run("rcpt4_harbor_grill.png")
            r2 = run("scan.pdf", pdf.getvalue())
            check(not FakeGroq.seen and r1["reasons"] == want and r2["reasons"] == want and r1["needs_review"] and r2["needs_review"],
                  f"PNG photo and scanned PDF with no OCR backend: no API call, Needs review: {r1['reasons']}")
            check(no_text and r1["model"] == "" and r1["mode"] == "groq" and r1["source"] == "",
                  "scanned PDF really has no text layer; row tagged groq, no model used, no source")
            check("off" in core.provider_label() or "need Gemini or an OCR backend" in core.provider_label(),
                  f"provider label says scans need OCR when it is off: {core.provider_label()}")

            # --- lightweight OCR (stubbed, so this runs without the package): OCR text -> Groq text model
            os.environ.pop("OCR_BACKEND", None)
            ocr.available = lambda: True
            ocr_calls = []
            core.ocr_text = lambda data, name: (ocr_calls.append(name), (ocr_text, 0.97))[1]
            fake()
            r = run("rcpt4_harbor_grill.png")
            check(len(FakeGroq.seen) == 1 and "HARBOR STREET GRILL" in content_of() and "read from an image by OCR" in content_of()
                  and FakeGroq.seen[0]["body"]["model"] == "openai/gpt-oss-120b" and ocr_calls == ["rcpt4_harbor_grill.png"]
                  and r["document"].vendor == CANNED_RECEIPT["vendor"] and not r["needs_review"] and r["mode"] == "groq",
                  "PNG photo with OCR (stub): OCR text (+ an OCR caution) -> Groq text model, receipt parsed and validated clean")
            check(r["source"] == "ocr" and r["document"].confidence == core.OCR_CONFIDENCE_CAP == 0.85,
                  f"OCR rows are marked source=ocr and confidence is capped (model said 0.9, row says {r['document'].confidence})")
            core.ocr_text = lambda data, name: (ocr_text, 0.6)
            fake()
            r = run("rcpt4_harbor_grill.png")
            check(r["needs_review"] and "low confidence 0.60" in r["reasons"], f"OCR engine unsure (0.60) -> flagged: {r['reasons']}")
            fake()
            core.ocr_text = lambda data, name: (ocr_text, 0.97)
            run("inv1_acme_supplies.pdf")
            check(len(FakeGroq.seen) == 1 and "OCR" not in content_of(), "text-layer PDF never goes through OCR")

            # --- Docling wins over the lightweight OCR when both exist
            core.docling_available, core.docling_text = (lambda: True), (lambda data, name: ocr_text)
            core.ocr_text = lambda data, name: ("should not be used", 1.0)
            fake()
            r = run("rcpt4_harbor_grill.png")
            check(len(FakeGroq.seen) == 1 and "HARBOR STREET GRILL" in content_of() and "should not be used" not in content_of()
                  and r["source"] == "ocr" and not r["needs_review"], "Docling installed: used before the lightweight OCR")
            core.docling_available, core.docling_text = (lambda: False), real_docling

            # --- no key: the same OCR text feeds the heuristic parser
            core.ocr_text = lambda data, name: ("HARBOR STREET GRILL\n77 Pier Road\nJun 21, 2025\n1 Clam Chowder   9.50\nSubtotal   9.50\nSales Tax   0.69\nTOTAL   $10.19\nPaid: Visa ****1111", 0.97)
            r = core.process_file("rcpt4_harbor_grill.png", Path("samples/rcpt4_harbor_grill.png").read_bytes(), force_heuristic=True)
            check(r["mode"] == "heuristic" and r["source"] == "ocr" and r["document"].total == 10.19 and r["document"].confidence <= 0.72
                  and not r["needs_review"], f"no key: OCR text parsed by the heuristic parser ({r['document'].total}, {r['reasons']})")

            core.docling_text = lambda data, name: "  .  "
            core.docling_available = lambda: True
            fake()
            r = run("rcpt4_harbor_grill.png")
            check(not FakeGroq.seen and r["needs_review"] and "no readable text" in r["reasons"], "OCR that finds nothing -> Needs review, no API call")
        finally:
            core.docling_available, core.docling_text, core.ocr_text, ocr.available = real_avail, real_docling, real_ocr_text, real_ocr_ok
            os.environ.pop("OCR_BACKEND", None)

        # --- 429 then success: retried
        fake([err(429, "Rate limit reached for model", {"Retry-After": "0"})])
        r = run("inv1_acme_supplies.pdf")
        check(len(FakeGroq.seen) == 2 and not r["needs_review"] and r["document"].total == 199.23,
              f"429 then 200 = 2 calls, row clean (got {len(FakeGroq.seen)} calls)")

        # --- persistent 500: gives up after GROQ_RETRY_ATTEMPTS, Needs review row
        fake(fallback=err(500, "internal error"))
        r = run("inv1_acme_supplies.pdf")
        check(len(FakeGroq.seen) == llm.GROQ_RETRY_ATTEMPTS and r["needs_review"] and "extraction error" in r["reasons"] and "500" in r["reasons"],
              f"persistent 500: {len(FakeGroq.seen)} attempts then Needs review ({r['reasons'][:70]}...)")

        # --- malformed JSON: no retry, Needs review
        fake([(200, {}, _chat_ok('{"doc_type": "invoice", "vendor": "Acme", total: 12.5,}'))])
        r = run("inv1_acme_supplies.pdf")
        check(len(FakeGroq.seen) == 1 and r["needs_review"] and "malformed JSON" in r["reasons"], f"malformed JSON -> Needs review ({r['reasons'][:70]})")
        fake([(200, {}, _chat_ok("Sorry, I cannot read this document."))])
        r = run("inv1_acme_supplies.pdf")
        check(r["needs_review"] and "no JSON object" in r["reasons"], "reply without any JSON -> Needs review")
        fake([(200, {}, _chat_ok(json.dumps({**CANNED, "total": "a lot"})))])
        r = run("inv1_acme_supplies.pdf")
        check(r["needs_review"] and "extraction error" in r["reasons"], "JSON that breaks the schema (total='a lot') -> Needs review")

        # --- bad key: fail fast, quota exhausted: fail fast
        fake(fallback=err(401, "Invalid API Key"))
        r = run("inv1_acme_supplies.pdf")
        check(len(FakeGroq.seen) == 1 and r["needs_review"] and "401" in r["reasons"], "401 invalid key: no retries, Needs review")
        fake(fallback=err(429, "Rate limit reached (tokens per day)", {"Retry-After": "3600"}))
        with contextlib.redirect_stderr(io.StringIO()):
            r = run("inv1_acme_supplies.pdf")
        check(len(FakeGroq.seen) == 2 and r["needs_review"] and "quota" in r["reasons"] and "fallback" in r["reasons"],
              "daily cap on both models (Retry-After of an hour): one fallback try, then fail fast with a clear reason")

        # --- daily token cap (TPD) on the primary model: the same request is retried ONCE on GROQ_FALLBACK_MODEL
        tpd = ("Rate limit reached for model `openai/gpt-oss-120b` in organization `org_test` service tier `on_demand` on tokens per day "
               "(TPD): Limit 200000, Used 199724, Requested 923. Please try again in 4m39.504s. Need more tokens? Upgrade to Dev Tier")
        fake([err(429, tpd, {"Retry-After": "280"}), None])
        log = io.StringIO()
        with contextlib.redirect_stderr(log):
            r = run("inv1_acme_supplies.pdf")
        a, b = (s["body"] for s in FakeGroq.seen[:2])
        check(len(FakeGroq.seen) == 2 and a["model"] == "openai/gpt-oss-120b" and b["model"] == "openai/gpt-oss-20b"
              and a["messages"] == b["messages"] and r["model"] == "openai/gpt-oss-20b" and r["mode"] == "groq"
              and r["document"].total == 199.23 and not r["needs_review"],
              f"TPD 429 on the primary: same request retried on {llm.GROQ_DEFAULT_FALLBACK_MODEL}, row clean, row reports the fallback model")
        check(log.getvalue().count("fallback") == 1 and "fake-groq-key" not in log.getvalue(), "fallback logs exactly one line, no API key in it")
        fake([err(429, tpd), None])
        with contextlib.redirect_stderr(io.StringIO()):
            r = run("inv1_acme_supplies.pdf")
        check(r["model"] == "openai/gpt-oss-20b" and not r["needs_review"], "TPD 429 without a Retry-After header: fallback too")
        fake([err(429, "Rate limit reached for model on requests per minute")] * llm.GROQ_RETRY_ATTEMPTS + [None])
        with contextlib.redirect_stderr(io.StringIO()):
            r = run("inv1_acme_supplies.pdf")
        check(len(FakeGroq.seen) == llm.GROQ_RETRY_ATTEMPTS + 1 and r["model"] == "openai/gpt-oss-20b" and not r["needs_review"],
              f"a 429 that survives all {llm.GROQ_RETRY_ATTEMPTS} retries: one more try on the fallback ({len(FakeGroq.seen)} calls)")
        fake(fallback=err(500, "internal error"))
        r = run("inv1_acme_supplies.pdf")
        check(len(FakeGroq.seen) == llm.GROQ_RETRY_ATTEMPTS and r["needs_review"], "persistent 500 does not use the fallback model")
        os.environ["GROQ_FALLBACK_MODEL"] = ""
        try:
            fake([err(429, tpd), None])
            r = run("inv1_acme_supplies.pdf")
            check(len(FakeGroq.seen) == 1 and llm.groq_fallback_model() == "" and r["needs_review"] and "429" in r["reasons"],
                  "GROQ_FALLBACK_MODEL empty: fallback disabled, TPD 429 fails as before")
        finally:
            os.environ.pop("GROQ_FALLBACK_MODEL", None)

        # --- tolerated model quirks
        fake([(200, {}, _chat_ok("Here you go:\n```json\n" + json.dumps(CANNED) + "\n```"))])
        check(not run("inv1_acme_supplies.pdf")["needs_review"], "JSON wrapped in a code fence is accepted")
        quirky = {**CANNED, "confidence": 95, "line_items": CANNED["line_items"] + [{"description": None, "amount": None}]}
        fake([(200, {}, _chat_ok(json.dumps(quirky)))])
        r = run("inv1_acme_supplies.pdf")
        check(r["document"].confidence == 0.95 and not r["needs_review"], "confidence given as 95 is read as 0.95; null description tolerated")
        fake([err(400, "'response_format' : json_object is not supported with this model"), None])
        r = run("inv1_acme_supplies.pdf")
        check(len(FakeGroq.seen) == 2 and "response_format" not in FakeGroq.seen[1]["body"] and not r["needs_review"],
              "400 about response_format: retried once without JSON mode")

        # --- the CLI end to end
        with tempfile.TemporaryDirectory() as tmp:
            fake()
            out = Path(tmp) / "o.csv"
            cp = subprocess.run([sys.executable, "extract.py", "samples/inv1_acme_supplies.pdf", "--out", str(out)],
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
            df = pd.read_csv(out)
            check(cp.returncode == 0 and "AI provider - Groq" in cp.stdout and set(df["mode"]) == {"groq"} and not df.needs_review.any()
                  and len(FakeGroq.seen) == 1, f"CLI with GROQ_API_KEY: the PDF goes through Groq, not flagged {cp.stderr.strip()[-150:]}")

        # --- smoke_groq.py (the owner's live test) runs end to end against the fake: 9 rows, the model shown.
        # (With no OCR backend the PNG makes no API call and is flagged; with RapidOCR / Docling it is really OCR'd.)
        has_ocr = core.ocr_available()
        fake()
        cp = subprocess.run([sys.executable, "smoke_groq.py"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        rows = [l for l in cp.stdout.splitlines() if re.match(r"(inv|rcpt)\d_\S+\.(pdf|png)\s", l)]
        n_png = [l for l in rows if l.startswith("rcpt4")]
        check(cp.returncode == 0 and len(rows) == 9 and len(FakeGroq.seen) == (9 if has_ocr else 8)
              and sum("openai/gpt-oss-120b" in l for l in rows) == (9 if has_ocr else 8)
              and ((has_ocr and " ocr " in n_png[0]) or ("YES" in n_png[0] and "scanned image" in cp.stdout)),
              f"smoke_groq.py vs fake: 9 table rows, text model shown, scanned PNG {'OCR' if has_ocr else 'flagged'} {cp.stderr.strip()[-150:]}")
        # Windows drops empty env vars from a child's environment, and the child would then load a developer's
        # local .env via python-dotenv - so remove the key AND disable dotenv for this subprocess.
        nokey_env = {k: v for k, v in os.environ.items() if k != "GROQ_API_KEY"}
        nokey_env["PYTHON_DOTENV_DISABLED"] = "1"
        cp = subprocess.run([sys.executable, "smoke_groq.py"], capture_output=True, text=True, encoding="utf-8", errors="replace", env=nokey_env)
        check(cp.returncode == 2 and "GROQ_API_KEY is not set" in cp.stdout, "smoke_groq.py without a key exits 2 with instructions, no API call")
        os.environ["GROQ_API_KEY"] = "fake-groq-key"
    finally:
        srv.shutdown()
        os.environ["GROQ_API_KEY"] = ""
        os.environ.pop("GROQ_BASE_URL", None)
        llm.GROQ_RETRY_DELAY = 2.0


# --------------------------------------------------------------------------- 5. Streamlit smoke test
def stage_app():
    print("\n[5] Streamlit app smoke test (AppTest)")
    import logging
    from streamlit.testing.v1 import AppTest
    for name in ("streamlit", "streamlit.runtime.scriptrunner_utils.script_run_context"):
        logging.getLogger(name).setLevel(logging.ERROR)   # silence "missing ScriptRunContext" bare-mode noise
    def md(t):
        return " ".join(m.value for m in t.markdown)
    has_ocr = core.ocr_available()
    at = AppTest.from_file("app.py", default_timeout=120).run()
    check(not at.exception, f"app loads without exception {[e.value for e in at.exception]}")
    check("dx-pill--warn" in md(at) and "Demo mode" in md(at), "amber status pill 'Demo mode' when provider is none")
    check("How it reads your documents" in [e.label for e in at.expander] and "GROQ_API_KEY" in md(at),
          "the long explanation lives in the 'How it reads your documents' expander")
    check(any("AI provider: none" in c.value for c in at.caption), "footer shows the provider (none)")
    check(f"OCR: {core.ocr_label()}" in md(at) if has_ocr else "OCR: not installed" in md(at), f"pill shows the OCR ({core.ocr_label()})")
    os.environ["GROQ_API_KEY"] = "fake-groq-key"
    try:
        g = AppTest.from_file("app.py", default_timeout=120).run()
        os.environ["OCR_BACKEND"] = "none"                  # the app must still work without any OCR package
        nog = AppTest.from_file("app.py", default_timeout=120).run()
    finally:
        os.environ["GROQ_API_KEY"] = ""
        os.environ.pop("OCR_BACKEND", None)
    check(not g.exception and "dx-pill--ok" in md(g) and "Groq gpt-oss-120b" in md(g) and "Demo mode" not in md(g)
          and "Groq (openai/gpt-oss-120b)" in md(g),
          "with GROQ_API_KEY: green pill naming Groq and the model, explanation names the model, no demo pill")
    check(any("AI provider: Groq" in c.value for c in g.caption), "footer shows the Groq provider and models")
    check(not nog.exception and "OCR: not installed" in md(nog) and "no OCR backend is installed" in md(nog)
          and "scans and photos need Gemini or an OCR backend" in "".join(c.value for c in nog.caption),
          "OCR missing (OCR_BACKEND=none): app still loads, pill and explanation say so")
    core.MAX_FILES = 5
    try:
        cap = AppTest.from_file("app.py", default_timeout=120).run()
        cap.button(key="sample_btn").click().run()
    finally:
        core.MAX_FILES = 10
    check(not cap.exception and any("Only the first 5 of 9" in w.value for w in cap.warning)
          and {x.label: x.value for x in cap.metric}.get("Files processed") == "5",
          "MAX_FILES=5: UI processes 5 of 9 and shows a friendly warning")
    at.button(key="sample_btn").click().run()
    check(not at.exception, f"sample run without exception {[e.value for e in at.exception]}")
    m = {x.label: x.value for x in at.metric}
    totals = [x.value for x in at.metric if x.label == "Total amount"]
    print("      cards:", m, totals)
    check(m.get("Files processed") == "9" and int(m.get("Needs review", 0)) >= 1, "summary cards: 9 processed, >= 1 flagged")
    check(sorted(t.split()[0] for t in totals) == ["EUR", "GBP", "USD"] and all(re.fullmatch(r"[A-Z]{3} [\d,]+\.\d{2}", t) for t in totals),
          f"per-currency total cards read like 'USD 2,259.22' (USD, GBP, EUR): {totals}")
    check(any(t.label.startswith("Needs review (") for t in at.tabs), f"Needs review tab carries the count: {[t.label for t in at.tabs]}")


# --------------------------------------------------------------------------- 6. OCR (lightweight backend)
def stage_ocr():
    print("\n[6] OCR: helpers always, the real backend when installed")
    from types import SimpleNamespace

    from PIL import Image

    # --- pure helpers (no OCR package needed)
    check(ocr.respace("77PierRoad,Boston,MA 02110") == "77 Pier Road, Boston, MA 02110"
          and ocr.respace("Jun 21,2025 7:48PM") == "Jun 21, 2025 7:48 PM" and ocr.respace("1Clam Chowder") == "1 Clam Chowder",
          "respace puts back the spaces the recogniser drops (PierRoad, 21,2025, 7:48PM, 1Clam)")
    check(ocr.respace("McDonald's iPhone 1,234.56 AC-10482") == "McDonald's iPhone 1,234.56 AC-10482",
          "respace leaves brand names, thousands separators and ids alone")
    boxes = [(620, 52, 690, 72, "28.50", .9), (60, 10, 200, 30, "Clam Chowder", .99), (60, 50, 150, 70, "Fish Tacos", .9),
             (620, 12, 680, 32, "9.50", .99), (10, 100, 50, 120, "Sales", .9), (55, 101, 90, 121, "Tax", .9)]
    check(ocr.boxes_to_text(boxes) == "Clam Chowder   9.50\nFish Tacos   28.50\nSales Tax",
          f"boxes become reading-order rows, a wide gap becomes a 3-space column: {ocr.boxes_to_text(boxes)!r}")
    check(ocr.boxes_to_text([]) == "" and ocr.boxes_to_text([(0, 0, 5, 5, "  ", 1.0)]) == "", "no text -> empty string")

    # --- backend selection (OCR_BACKEND)
    real_ready, real_backend = ocr._ready, ocr.backend
    try:
        ocr._ready = lambda name: True
        sel = {}
        for want in ("", "auto", "rapidocr", "tesseract", "none", "bogus"):
            os.environ["OCR_BACKEND"] = want
            sel[want] = ocr.backend()
        check(sel == {"": "rapidocr", "auto": "rapidocr", "rapidocr": "rapidocr", "tesseract": "tesseract", "none": "none",
                      "bogus": "rapidocr"}, f"OCR_BACKEND selection when both are installed: {sel}")
        ocr._ready = lambda name: name == "tesseract"
        os.environ["OCR_BACKEND"] = "auto"
        a = ocr.backend()
        os.environ["OCR_BACKEND"] = "rapidocr"
        check(a == "tesseract" and ocr.backend() == "none" and not ocr.available(),
              "auto falls back to Tesseract; an explicit rapidocr that is not installed means none")
        # --- Tesseract adapter with a stub pytesseract (no binary needed)
        os.environ["OCR_BACKEND"] = "tesseract"
        sys.modules["pytesseract"] = SimpleNamespace(
            Output=SimpleNamespace(DICT="dict"),
            image_to_data=lambda img, lang, output_type: {"text": ["Total", "", "$90.68", "Tip"], "conf": ["96", "-1", "95", "90"],
                                                          "left": [380, 0, 590, 380], "top": [544, 0, 544, 510],
                                                          "width": [95, 0, 95, 40], "height": [28, 0, 28, 28]})
        buf = io.BytesIO(); Image.new("RGB", (800, 600), "white").save(buf, "PNG")
        text, score = ocr.read_pages([buf.getvalue()])
        check(text == "Tip\nTotal   $90.68" and score == 0.937, f"Tesseract adapter (stub): words -> rows, mean confidence: {text!r} {score}")
    finally:
        sys.modules.pop("pytesseract", None)
        ocr._ready, ocr.backend = real_ready, real_backend
        os.environ.pop("OCR_BACKEND", None)
    check(ocr._scale((4000, 3000)) < 1 and ocr._scale((744, 1052)) == 1.0 and 4000 * 3000 * ocr._scale((4000, 3000)) ** 2 <= ocr.MAX_PIXELS * 1.01,
          "big phone photos are shrunk to the pixel budget; the 744x1052 sample is left alone")

    # --- the real backend
    if not ocr.available():
        print("SKIP  no OCR backend installed (pip install -r requirements-ocr.txt, then pip install --no-deps "
              "rapidocr-onnxruntime==1.4.4; or OCR_BACKEND=tesseract with the tesseract binary)")
        return
    print(f"      real OCR backend: {ocr.label()}")
    png = Path("samples/rcpt4_harbor_grill.png").read_bytes()
    r = core.process_file("rcpt4_harbor_grill.png", png, force_heuristic=True)
    d = r["document"]
    check("HARBOR" in (d.vendor or "").upper() and d.total is not None and abs(d.total - 90.68) <= 0.05,
          f"no key, real OCR: PNG receipt read: vendor {d.vendor!r}, total {d.total}")
    check(r["source"] == "ocr" and r["mode"] == "heuristic" and d.confidence <= core.OCR_CONFIDENCE_CAP and not r["needs_review"],
          f"... marked source=ocr, confidence {d.confidence} (<= {core.OCR_CONFIDENCE_CAP}), validated clean ({r['reasons']})")
    gl = Path("samples/inv3_greenleaf_catering.pdf").read_bytes()
    r = core.process_file("inv3_greenleaf_catering.pdf", gl, force_heuristic=True)
    check(r["needs_review"] and "total" in r["reasons"] and r["source"] == "text", f"Greenleaf wrong-total PDF still flagged: {r['reasons']}")
    page = Image.open(io.BytesIO(core.render_first_page(gl, "x.pdf"))).convert("RGB")
    scan = io.BytesIO(); page.save(scan, "PDF")
    r = core.process_file("greenleaf_scan.pdf", scan.getvalue(), force_heuristic=True)
    check(r["source"] == "ocr" and r["needs_review"] and "total" in r["reasons"],
          f"... and the same invoice as an image-only scan (OCR'd) is flagged too: {r['reasons'][:90]}")

    srv = HTTPServer(("127.0.0.1", 0), FakeGroq)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    os.environ["GROQ_API_KEY"], os.environ["GROQ_BASE_URL"] = "fake-groq-key", f"http://127.0.0.1:{srv.server_port}/openai/v1"
    try:
        FakeGroq.queue, FakeGroq.fallback = [], None
        FakeGroq.seen.clear()
        r = core.process_file("rcpt4_harbor_grill.png", png)
        content = FakeGroq.seen[-1]["body"]["messages"][0]["content"]
        d = r["document"]
        check(r["mode"] == "groq" and "HARBOR" in content and "TOTAL" in content and "90.68" in content,
              "Groq + real OCR: the PNG's OCR text (HARBOR ... TOTAL 90.68) is what the text model receives")
        check((d.vendor, d.total, r["source"], d.confidence, r["needs_review"]) == ("HARBOR STREET GRILL", 90.68, "ocr", 0.85, False),
              f"... parsed, source=ocr, confidence capped at 0.85, not flagged ({d.vendor}, {d.total}, {d.confidence})")
        FakeGroq.seen.clear()
        invoice = io.BytesIO(); Image.open(io.BytesIO(core.render_first_page(Path("samples/inv1_acme_supplies.pdf").read_bytes(), "x.pdf"))).convert("RGB").save(invoice, "PDF")
        r = core.process_file("acme_scan.pdf", invoice.getvalue())
        content = FakeGroq.seen[-1]["body"]["messages"][0]["content"]
        check("Acme" in content and r["source"] == "ocr" and r["document"].total == 199.23,
              "Groq + real OCR: an image-only PDF is rendered (pypdfium2), OCR'd and sent as text")
    finally:
        srv.shutdown()
        os.environ["GROQ_API_KEY"] = ""
        os.environ.pop("GROQ_BASE_URL", None)


# --------------------------------------------------------------------------- 7. optional Docling backend
def stage_docling():
    print("\n[7] Optional Docling backend (EXTRACT_BACKEND=docling)")
    import importlib.util
    if importlib.util.find_spec("docling") is None:
        print("SKIP  docling not installed (pip install -r requirements-docling.txt to include this stage)")
        return
    os.environ["EXTRACT_BACKEND"] = "docling"
    try:
        gt, flagged, wrong = make_samples.ground_truth(), [], []
        for g in gt:
            r = core.process_file(g["file"], (Path("samples") / g["file"]).read_bytes(), force_heuristic=True)
            d = r["document"]
            if r["needs_review"]:
                flagged.append(g["file"])
            got = (d.doc_type, (d.vendor or "").lower(), d.document_number, d.date, d.currency, d.tax, d.total)
            exp = (g["doc_type"], g["vendor"].lower(), g["number"], g["date"], g["currency"], g["tax"], g["total"])
            if got != exp:
                wrong.append(g["file"])
        check(not wrong, f"all 9 files incl. the PNG receipt (OCR) match ground truth {wrong}")
        check(flagged == ["inv3_greenleaf_catering.pdf"], f"only the wrong-total invoice is flagged: {flagged}")
    finally:
        os.environ.pop("EXTRACT_BACKEND", None)


if __name__ == "__main__":
    for stage in (stage_cli, stage_zip, stage_gemini_mock, stage_groq_mock, stage_app, stage_ocr, stage_docling):
        try:
            stage()
        except Exception as e:  # a crashing stage is a failure, not a traceback wall
            import traceback
            traceback.print_exc()
            failures.append(f"{stage.__name__} crashed: {type(e).__name__}: {e}")
    print("\n" + ("ALL CHECKS PASSED" if not failures else f"{len(failures)} CHECK(S) FAILED"))
    sys.exit(1 if failures else 0)
