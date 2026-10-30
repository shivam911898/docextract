"""Generate the 9 fake sample documents in samples/: 5 invoices + 4 receipts (US/UK/EU, USD/GBP/EUR).

* 8 are PDFs with a text layer; one receipt is rendered to a PNG, so the image/vision path is exercised.
* Exactly one invoice (Greenleaf Catering) carries a deliberately wrong printed total, so "Needs review" fires.

Run:  python make_samples.py            (needs reportlab + pypdfium2, both in requirements.txt)
"""
from __future__ import annotations

import io
from datetime import date as _date, timedelta
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfgen import canvas

OUT = Path(__file__).parent / "samples"
WRONG_TOTAL_DELTA = 37.50

DOCS = [
    # ------------------------------------------------------------------ invoices
    dict(kind="invoice", file="inv1_acme_supplies.pdf", style="classic", page="letter", accent="#1f3a5f",
         vendor="Acme Office Supplies Inc.", addr="100 Market Street, Springfield, IL 62701", number="AC-10482",
         date="2025-03-14", date_fmt="%Y-%m-%d", cur="USD", sym="$", tax_label="Tax", rate=0.08,
         items=[("Copy Paper, Letter (500 sheets)", 20, 4.50), ("Ballpoint Pens (box of 50)", 6, 8.25),
                ("Stapler, heavy duty", 3, 14.99)]),
    dict(kind="invoice", file="inv2_nordic_consulting.pdf", style="modern", page="a4",
         vendor="Nordic Cloud Consulting AB", number="2025-0071", date="2025-04-02", date_fmt="%Y-%m-%d",
         cur="EUR", sym="€", tax_label="Tax", rate=0.25,
         items=[("Architecture review (hours)", 12, 140.00), ("Kubernetes migration support (hours)", 30, 125.00),
                ("Documentation", 1, 450.00)]),
    dict(kind="invoice", file="inv3_greenleaf_catering.pdf", style="mono", page="letter", wrong_total=True,
         vendor="Greenleaf Catering Co.", number="GL-5590", date="2025-05-21", date_fmt="%Y-%m-%d",
         cur="USD", sym="$", tax_label="Tax", rate=0.0725,
         items=[("Lunch buffet (per head)", 45, 18.50), ("Coffee & tea service", 1, 120.00),
                ("Dessert platters", 4, 32.00)]),
    dict(kind="invoice", file="inv4_bluepeak_it.pdf", style="vat", page="a4", accent="#0b6e4f",
         vendor="BluePeak IT Services Ltd", addr="14 King Street, Manchester M2 4WU", number="BP-88213",
         date="2025-06-09", date_fmt="%d %B %Y", due_days=14, client="Hartley & Co Solicitors",
         client_addr="22 Albion Road, Leeds LS1 5AB", cur="GBP", sym="£", tax_label="VAT (20%)", rate=0.20,
         items=[("Laptop - 14in business", 5, 899.00), ("USB-C dock", 5, 119.50), ("3-year warranty", 5, 79.00),
                ("Setup & imaging", 5, 25.00)]),
    dict(kind="invoice", file="inv5_sunrise_print.pdf", style="classic", page="letter", accent="#8a3b12",
         vendor="Sunrise Print & Packaging", addr="2200 Industrial Way, Portland, OR 97201", number="SPP-3307",
         date="2025-07-30", date_fmt="%m/%d/%Y", cur="USD", sym="$", tax_label="Sales Tax", rate=0.06,
         items=[("Custom boxes 12x8x4", 500, 1.12), ("Label rolls", 10, 22.40)]),
    # ------------------------------------------------------------------ receipts
    dict(kind="receipt", file="rcpt1_green_valley_market.pdf", style="thermal", vendor="GREEN VALLEY MARKET",
         addr=["4120 Oak Avenue", "Austin, TX 78704", "TEL 512-555-0142"], number="004871", date="2025-03-14",
         date_fmt="%m/%d/%Y", time="10:42 AM", cur="USD", sym="$", rate=0.07, payment="Visa ************4821",
         items=[("ORG BANANAS 1.2LB", 1, 1.74), ("WHOLE MILK 1GAL", 1, 4.29), ("GRANOLA BARS", 2, 3.49),
                ("SOURDOUGH LOAF", 1, 5.99), ("CHICKEN BREAST 2.1LB", 1, 11.48)]),
    dict(kind="receipt", file="rcpt2_daily_grind_cafe.pdf", style="cafe", vendor="The Daily Grind Coffee Co.",
         addr=["8 Castle Street, Edinburgh EH2 3AT", "VAT Reg: GB 123 4567 89"], number="004821",
         date="2025-05-21", date_fmt="%d/%m/%Y", time="08:15", cur="GBP", sym="£", rate=0.20, tax_incl=True,
         payment="Visa Contactless",
         items=[("Flat White", 2, 3.50), ("Almond Croissant", 1, 3.20), ("Bacon Roll", 1, 5.40),
                ("Orange Juice", 1, 3.10)]),
    dict(kind="receipt", file="rcpt3_bistro_rhein.pdf", style="bistro", vendor="BISTRO RHEIN",
         addr=["Rheinstrasse 12, 10115 Berlin"], number="8815", date="2025-06-07", date_fmt="%d.%m.%Y",
         time="19:32", cur="EUR", sym="€", rate=0.19, payment="Mastercard",
         items=[("Currywurst mit Pommes", 2, 9.80), ("Pils 0.5l", 3, 4.20), ("Apfelstrudel", 1, 6.50)]),
    dict(kind="receipt", file="rcpt4_harbor_grill.png", style="grill", vendor="HARBOR STREET GRILL",
         addr=["77 Pier Road, Boston, MA 02110"], number="5521", date="2025-06-21", date_fmt="%b %d, %Y",
         time="7:48 PM", cur="USD", sym="$", rate=0.0725, tip=14.00, payment="Mastercard ****4242",
         items=[("Clam Chowder", 1, 9.50), ("Fish Tacos", 2, 14.25), ("Grilled Salmon", 1, 26.00),
                ("Iced Tea", 2, 3.75)]),
]


# --------------------------------------------------------------------------- helpers
def totals(d: dict):
    """Return (subtotal, tax, tip, total) exactly as printed on the document."""
    sub = round(sum(q * p for _, q, p in d["items"]), 2)
    tip = d.get("tip", 0.0)
    if d.get("tax_incl"):  # tax already inside the prices (UK-style receipt)
        tax, total = round(sub * d["rate"] / (1 + d["rate"]), 2), sub
    else:
        tax = round(sub * d["rate"], 2)
        total = round(sub + tax + tip, 2)
    if d.get("wrong_total"):
        total = round(total + WRONG_TOTAL_DELTA, 2)  # deliberate error
    return sub, tax, tip, total


def money(sym, v):
    return f"{sym}{v:,.2f}"


def date_str(d: dict) -> str:
    return _date.fromisoformat(d["date"]).strftime(d["date_fmt"])


def page_size(d: dict):
    if d["kind"] == "invoice":
        return letter if d["page"] == "letter" else A4
    n = len(d["items"])
    return {"thermal": (226, 300 + 13 * n), "cafe": (300, 340 + 16 * n),
            "bistro": (420, 380 + 18 * n), "grill": (300, 360 + 18 * n)}[d["style"]]


# --------------------------------------------------------------------------- invoice layouts
def inv_classic(c, d, W, H):  # left-aligned vendor, coloured table header bar
    sub, tax, _, total = totals(d); s = d["sym"]
    c.setFont("Helvetica-Bold", 20); c.drawString(50, H - 60, d["vendor"])
    c.setFont("Helvetica", 10); c.drawString(50, H - 78, d["addr"])
    c.setFont("Helvetica-Bold", 16); c.drawRightString(W - 50, H - 60, "INVOICE")
    c.setFont("Helvetica", 10)
    c.drawRightString(W - 50, H - 80, f"Invoice #: {d['number']}")
    c.drawRightString(W - 50, H - 94, f"Date: {date_str(d)}")
    c.drawRightString(W - 50, H - 108, f"Currency: {d['cur']}")
    c.setFillColor(colors.HexColor(d["accent"])); c.rect(50, H - 160, W - 100, 20, fill=1, stroke=0)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 10)
    c.drawString(56, H - 154, "Description"); c.drawRightString(330, H - 154, "Qty")
    c.drawRightString(430, H - 154, "Unit Price"); c.drawRightString(W - 56, H - 154, "Amount")
    c.setFillColor(colors.black); c.setFont("Helvetica", 10)
    y = H - 180
    for desc, q, p in d["items"]:
        c.drawString(56, y, desc); c.drawRightString(330, y, str(q))
        c.drawRightString(430, y, money(s, p)); c.drawRightString(W - 56, y, money(s, q * p)); y -= 18
    y -= 15
    for lab, v in (("Subtotal", sub), (d["tax_label"], tax), ("Total", total)):
        c.setFont("Helvetica-Bold" if lab == "Total" else "Helvetica", 11)
        c.drawString(380, y, lab); c.drawRightString(W - 56, y, money(s, v)); y -= 18
    c.setFont("Helvetica", 9); c.drawString(50, 60, "Payment due within 30 days. Thank you for your business.")


def inv_modern(c, d, W, H):  # centred title on grey band, totals in a box
    sub, tax, _, total = totals(d); s = d["sym"]
    c.setFillColor(colors.HexColor("#eeeeee")); c.rect(0, H - 110, W, 110, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#222222")); c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(W / 2, H - 55, d["vendor"])
    c.setFont("Helvetica", 11); c.drawCentredString(W / 2, H - 78, "Tax Invoice")
    c.setFont("Helvetica", 10)
    c.drawString(60, H - 150, f"Invoice No. {d['number']}")
    c.drawString(60, H - 165, f"Invoice Date: {date_str(d)}")
    c.drawString(60, H - 180, f"All amounts in {d['cur']}")
    y = H - 225
    c.setFont("Helvetica-Bold", 10)
    c.drawString(60, y, "ITEM"); c.drawRightString(340, y, "QTY"); c.drawRightString(430, y, "RATE")
    c.drawRightString(W - 60, y, "LINE TOTAL")
    c.line(60, y - 5, W - 60, y - 5); y -= 24; c.setFont("Helvetica", 10)
    for desc, q, p in d["items"]:
        c.drawString(60, y, desc); c.drawRightString(340, y, str(q))
        c.drawRightString(430, y, f"{p:,.2f}"); c.drawRightString(W - 60, y, f"{q * p:,.2f}"); y -= 20
    y -= 15
    c.rect(300, y - 62, W - 360, 78, stroke=1, fill=0)
    for i, (lab, v) in enumerate((("Subtotal", sub), (d["tax_label"], tax), ("Total", total))):
        c.setFont("Helvetica-Bold" if lab == "Total" else "Helvetica", 11)
        c.drawString(310, y - i * 22, lab); c.drawRightString(W - 70, y - i * 22, money(s, v))


def inv_mono(c, d, W, H):  # monospace, plain-text feel
    sub, tax, _, total = totals(d)
    c.setFont("Courier-Bold", 14); c.drawString(60, H - 60, d["vendor"].upper())
    c.setFont("Courier", 10)
    c.drawString(60, H - 80, "Invoice Number: " + d["number"])
    c.drawString(60, H - 94, "Date: " + date_str(d))
    c.drawString(60, H - 108, "Currency: " + d["cur"])
    c.drawString(60, H - 130, "-" * 70)
    c.drawString(60, H - 144, f"{'Description':<30}{'Qty':>6}{'Price':>12}{'Amount':>14}")
    c.drawString(60, H - 156, "-" * 70)
    y = H - 172
    for desc, q, p in d["items"]:
        c.drawString(60, y, f"{desc:<30}{q:>6}{p:>12,.2f}{q * p:>14,.2f}"); y -= 15
    c.drawString(60, y, "-" * 70); y -= 18
    for lab, v in (("Subtotal", sub), (d["tax_label"], tax), ("Total", total)):
        c.drawString(60, y, f"{lab + ':':<48}{v:>14,.2f}"); y -= 15
    c.drawString(60, y - 10, "Thank you for your business!")


def inv_vat(c, d, W, H):  # UK VAT invoice: coloured banner, Bill To block, zebra table
    sub, tax, _, total = totals(d); s = d["sym"]
    due = (_date.fromisoformat(d["date"]) + timedelta(days=d["due_days"])).strftime(d["date_fmt"])
    c.setFillColor(colors.HexColor(d["accent"])); c.rect(0, H - 95, W, 95, fill=1, stroke=0)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 22); c.drawString(40, H - 52, d["vendor"])
    c.setFont("Helvetica", 9); c.drawString(40, H - 70, d["addr"])
    c.setFont("Helvetica-Bold", 18); c.drawRightString(W - 40, H - 52, "VAT INVOICE")
    c.setFillColor(colors.black)
    y = H - 135
    c.setFont("Helvetica-Bold", 9); c.drawString(40, y, "BILL TO")
    c.setFont("Helvetica", 10); c.drawString(40, y - 15, d["client"]); c.drawString(40, y - 29, d["client_addr"])
    for i, (lab, val) in enumerate((("Invoice No:", d["number"]), ("Invoice Date:", date_str(d)),
                                    ("Due Date:", due))):
        c.setFont("Helvetica-Bold", 10); c.drawString(340, y - i * 15, lab)
        c.setFont("Helvetica", 10); c.drawString(430, y - i * 15, val)
    y -= 85
    c.setFillColor(colors.HexColor("#e6e6e6")); c.rect(40, y - 5, W - 80, 20, fill=1, stroke=0)
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold", 10)
    c.drawString(46, y, "Description"); c.drawRightString(340, y, "Qty")
    c.drawRightString(430, y, "Unit Price"); c.drawRightString(W - 46, y, "Amount")
    y -= 24
    for i, (desc, q, p) in enumerate(d["items"]):
        if i % 2:
            c.setFillColor(colors.HexColor("#f6f6f6")); c.rect(40, y - 6, W - 80, 20, fill=1, stroke=0)
            c.setFillColor(colors.black)
        c.setFont("Helvetica", 10); c.drawString(46, y, desc); c.drawRightString(340, y, str(q))
        c.drawRightString(430, y, money(s, p)); c.drawRightString(W - 46, y, money(s, q * p)); y -= 22
    y -= 14
    for lab, v in (("Subtotal", sub), (d["tax_label"], tax), ("Total Due", total)):
        c.setFont("Helvetica-Bold" if lab == "Total Due" else "Helvetica", 11)
        c.drawString(360, y, lab); c.drawRightString(W - 46, y, money(s, v)); y -= 18
    c.setFont("Helvetica", 9)
    c.drawString(40, 70, "Payment terms: 14 days. Bank transfer: Sort code 20-45-45, Acc 12345678.")
    c.drawString(40, 57, "VAT Reg No. GB 987 6543 21")


# --------------------------------------------------------------------------- receipt layouts
def rc_thermal(c, d, W, H):  # narrow US thermal-printer receipt, monospace, price-only item lines
    sub, tax, _, total = totals(d); y = H - 28
    c.setFont("Courier-Bold", 11); c.drawCentredString(W / 2, y, d["vendor"]); y -= 14
    c.setFont("Courier", 8)
    for line in d["addr"]:
        c.drawCentredString(W / 2, y, line); y -= 10
    y -= 4; c.drawString(17, y, "-" * 40); y -= 11
    c.drawString(17, y, f"Receipt #: {d['number']}"); y -= 10
    c.drawString(17, y, f"{date_str(d)}  {d['time']}"); y -= 10
    c.drawString(17, y, "-" * 40); y -= 11
    for desc, q, p in d["items"]:
        label = desc if q == 1 else f"{desc} {q} @ {p:.2f}"
        c.drawString(17, y, f"{label:<31}{q * p:>9,.2f}"); y -= 11
    c.drawString(17, y, "-" * 40); y -= 11
    c.drawString(17, y, f"{'SUBTOTAL':<31}{sub:>9,.2f}"); y -= 11
    c.drawString(17, y, f"{'TAX ' + format(d['rate'] * 100, '.1f') + '%':<31}{tax:>9,.2f}"); y -= 12
    c.setFont("Courier-Bold", 9); c.drawString(17, y, f"{'TOTAL':<30}{d['sym']}{total:>9,.2f}"); y -= 13
    c.setFont("Courier", 8); c.drawString(17, y, "-" * 40); y -= 11
    c.drawString(17, y, f"Payment: {d['payment']}"); y -= 10
    c.drawString(17, y, "APPROVED"); y -= 18
    c.drawCentredString(W / 2, y, "THANK YOU FOR SHOPPING!")


def rc_cafe(c, d, W, H):  # UK cafe slip: tax-inclusive prices, "2 x item" lines
    sub, tax, _, total = totals(d); s = d["sym"]; y = H - 36
    c.setFont("Helvetica-Bold", 15); c.drawCentredString(W / 2, y, d["vendor"]); y -= 16
    c.setFont("Helvetica", 8)
    for line in d["addr"]:
        c.drawCentredString(W / 2, y, line); y -= 11
    y -= 8; c.setFont("Helvetica", 9)
    c.drawString(24, y, f"Receipt No: {d['number']}"); y -= 12
    c.drawString(24, y, f"Date: {date_str(d)}   {d['time']}"); y -= 8
    c.line(24, y, W - 24, y); y -= 16
    c.setFont("Helvetica", 10)
    for desc, q, p in d["items"]:
        c.drawString(24, y, f"{q} x {desc}"); c.drawRightString(W - 24, y, money(s, q * p)); y -= 16
    c.line(24, y + 6, W - 24, y + 6); y -= 8
    c.setFont("Helvetica-Bold", 12); c.drawString(24, y, "Total"); c.drawRightString(W - 24, y, money(s, total))
    y -= 16; c.setFont("Helvetica", 9)
    c.drawString(24, y, f"Includes VAT @ {d['rate'] * 100:.0f}%"); c.drawRightString(W - 24, y, money(s, tax))
    y -= 22; c.drawString(24, y, f"Paid: {d['payment']}")
    y -= 24; c.setFont("Helvetica-Oblique", 9); c.drawCentredString(W / 2, y, "Thank you - see you tomorrow!")


def rc_bistro(c, d, W, H):  # EU restaurant bill: serif font, qty/price/amount columns, net + VAT
    sub, tax, _, total = totals(d); s = d["sym"]; y = H - 46
    c.setFont("Times-Bold", 22); c.drawCentredString(W / 2, y, d["vendor"]); y -= 16
    c.setFont("Times-Roman", 9)
    for line in d["addr"]:
        c.drawCentredString(W / 2, y, line); y -= 12
    y -= 10; c.setFont("Times-Roman", 10)
    c.drawString(36, y, f"Receipt No. {d['number']}"); c.drawRightString(W - 36, y, f"{date_str(d)}  {d['time']}")
    y -= 10; c.line(36, y, W - 36, y); y -= 16
    c.setFont("Times-Bold", 10)
    c.drawString(36, y, "Description"); c.drawRightString(250, y, "Qty")
    c.drawRightString(320, y, "Price"); c.drawRightString(W - 36, y, "Amount")
    y -= 18; c.setFont("Times-Roman", 10)
    for desc, q, p in d["items"]:
        c.drawString(36, y, desc); c.drawRightString(250, y, str(q))
        c.drawRightString(320, y, f"{p:,.2f}"); c.drawRightString(W - 36, y, f"{q * p:,.2f}"); y -= 18
    y -= 4; c.line(36, y + 8, W - 36, y + 8); y -= 6
    for lab, v in (("Subtotal", sub), (f"VAT {d['rate'] * 100:.0f}%", tax)):
        c.setFont("Times-Roman", 11); c.drawString(250, y, lab); c.drawRightString(W - 36, y, money(s, v)); y -= 16
    c.setFont("Times-Bold", 13); c.drawString(250, y, "TOTAL"); c.drawRightString(W - 36, y, money(s, total))
    y -= 28; c.setFont("Times-Roman", 10); c.drawString(36, y, f"Paid by: {d['payment']}")
    y -= 24; c.setFont("Times-Italic", 10); c.drawCentredString(W / 2, y, "Vielen Dank fuer Ihren Besuch!")


def rc_grill(c, d, W, H):  # US restaurant guest check with tip line (rendered to PNG)
    sub, tax, tip, total = totals(d); s = d["sym"]; y = H - 40
    c.setFont("Helvetica-Bold", 16); c.drawCentredString(W / 2, y, d["vendor"]); y -= 14
    c.setFont("Helvetica", 8.5)
    for line in d["addr"]:
        c.drawCentredString(W / 2, y, line); y -= 11
    y -= 8; c.drawString(26, y, f"Check #{d['number']}   Server: Dana   Table 12   Guests: 2"); y -= 12
    c.drawString(26, y, f"{date_str(d)}  {d['time']}"); y -= 8
    c.line(26, y, W - 26, y); y -= 16
    c.setFont("Helvetica", 10)
    for desc, q, p in d["items"]:
        c.drawString(26, y, f"{q}  {desc}"); c.drawRightString(W - 26, y, f"{q * p:,.2f}"); y -= 16
    y -= 2; c.line(26, y + 6, W - 26, y + 6); y -= 8
    for lab, v in (("Subtotal", sub), (f"Sales Tax {d['rate'] * 100:.2f}%", tax), ("Tip", tip)):
        c.drawString(150, y, lab); c.drawRightString(W - 26, y, f"{v:,.2f}"); y -= 15
    c.setFont("Helvetica-Bold", 12); c.drawString(150, y, "TOTAL"); c.drawRightString(W - 26, y, money(s, total))
    y -= 26; c.setFont("Helvetica", 9.5); c.drawString(26, y, f"Paid: {d['payment']}")
    y -= 24; c.setFont("Helvetica-Oblique", 9); c.drawCentredString(W / 2, y, "Thank you! Come back soon.")


STYLES = {"classic": inv_classic, "modern": inv_modern, "mono": inv_mono, "vat": inv_vat,
          "thermal": rc_thermal, "cafe": rc_cafe, "bistro": rc_bistro, "grill": rc_grill}


# --------------------------------------------------------------------------- build
def build_pdf(d: dict) -> bytes:
    W, H = page_size(d)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(W, H))
    STYLES[d["style"]](c, d, W, H)
    c.save()
    return buf.getvalue()


def pdf_to_png(pdf: bytes, scale: float = 2.5) -> bytes:
    import pypdfium2 as pdfium
    img = pdfium.PdfDocument(pdf)[0].render(scale=scale).to_pil().convert("RGB")
    buf = io.BytesIO(); img.save(buf, "PNG")
    return buf.getvalue()


def ground_truth() -> list[dict]:
    """What a perfect extractor should return per file (the printed values, including the wrong total)."""
    rows = []
    for d in DOCS:
        sub, tax, tip, total = totals(d)
        rows.append(dict(file=d["file"], doc_type=d["kind"], vendor=d["vendor"], number=d["number"], date=d["date"],
                         currency=d["cur"], subtotal=sub, tax=tax, tip=tip, total=total,
                         n_items=len(d["items"]), text_layer=d["file"].endswith(".pdf"),
                         wrong_total=bool(d.get("wrong_total"))))
    return rows


def main(out: Path = OUT) -> list[Path]:
    out.mkdir(exist_ok=True)
    written = []
    for d in DOCS:
        pdf = build_pdf(d)
        data = pdf_to_png(pdf) if d["file"].endswith(".png") else pdf
        (out / d["file"]).write_bytes(data)
        written.append(out / d["file"])
        print("wrote", d["file"])
    return written


if __name__ == "__main__":
    main()
