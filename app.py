"""DocExtract - Streamlit UI. Run: streamlit run app.py"""
import os
from pathlib import Path

import pandas as pd
import streamlit as st

import core
import llm
import ui

SAMPLES = Path(__file__).parent / "samples"
VIEW_COLS = ["file", "status", "vendor", "document_number", "date", "currency", "subtotal", "tax", "tip", "total",
             "confidence", "source", "doc_type", "payment_method", "review_reason"]
REVIEW_COLS = ["file", "vendor", "document_number", "total", "confidence", "source"]
MONEY = ("subtotal", "tax", "tip", "total", "unit_price", "amount")
SOURCE_NAMES = {"text": "Text layer", "ocr": "OCR", "vision": "Vision", "": ""}
N_SAMPLES = 9

st.set_page_config(page_title="DocExtract", page_icon=":material/receipt_long:", layout="wide",
                   initial_sidebar_state="collapsed")


def sample_docs():
    """Bundled demo files (regenerated on the fly if the folder is missing)."""
    if not any(SAMPLES.glob("*")):
        try:
            import make_samples
            make_samples.main()
        except Exception:
            return []
    return [(p.name, p.read_bytes()) for p in sorted(SAMPLES.iterdir()) if p.suffix.lower() in core.EXTS]


def run_batch(docs, slot):
    """Process documents one by one with a live progress bar (drawn in `slot`); returns result dicts."""
    with slot:
        bar = st.progress(0.0, text="Starting...")
        results = []
        for n, (name, data) in enumerate(docs, 1):
            bar.progress((n - 1) / len(docs), text=f"Reading {name}  ({n} of {len(docs)})")
            results.append(core.process_file(name, data))
        bar.progress(1.0, text=f"Done - {len(docs)} document(s) processed")
    return results


# ---------------------------------------------------------------- table formatting
def frame_for_view(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    """Display copy of the results table: a status label instead of the boolean, a readable source name."""
    view = df.assign(status=df.needs_review.map({True: "Needs review", False: "Clean"}),
                     source=df.source.fillna("").map(lambda s: SOURCE_NAMES.get(s, s)))
    return view[cols].reset_index(drop=True)


def style_view(view: pd.DataFrame, flagged: list):
    """Pandas Styler: flagged rows get the danger-soft background, status and source cells get pill-like colours,
    money columns show exactly two decimals (no 184.470000), missing values are blank."""
    def rows(row):
        bad = flagged[row.name]
        out = ["background-color: #FEE2E2" if bad else ""] * len(row)
        for i, col in enumerate(row.index):
            if col == "status":
                out[i] = ("background-color: #FECACA; color: #991B1B; font-weight: 600" if bad
                          else "background-color: #DCFCE7; color: #166534; font-weight: 600")
            elif col == "source" and row[col] == "OCR":
                out[i] = "background-color: #CCFBF1; color: #0F766E; font-weight: 600"
        return out
    money = {c: "{:,.2f}" for c in MONEY if c in view.columns}
    return view.style.apply(rows, axis=1).format(na_rep="").format(money, na_rep="")


def table_config(view_cols) -> dict:
    labels = {"file": "File", "status": "Status", "vendor": "Vendor", "document_number": "Document no.",
              "date": "Date", "currency": "Cur.", "subtotal": "Subtotal", "tax": "Tax", "tip": "Tip", "total": "Total",
              "source": "Source", "doc_type": "Type", "payment_method": "Payment", "review_reason": "Why it was flagged"}
    cfg = {c: st.column_config.TextColumn(labels[c]) for c in view_cols if c in labels}
    if "confidence" in view_cols:
        cfg["confidence"] = st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1, format="%.2f")
    if "review_reason" in view_cols:
        cfg["review_reason"] = st.column_config.TextColumn("Why it was flagged", width=520)
    return cfg


def plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


# ---------------------------------------------------------------- header
PROVIDER = core.active_provider()
OCR_NAME = core.ocr_label()
OCR_OK = core.ocr_available()
if PROVIDER == "groq":
    model = llm.groq_text_model()
    pill = ("ok", f"AI mode: Groq {model.split('/')[-1]}", f"OCR: {OCR_NAME}" if OCR_OK else "OCR: not installed", OCR_OK)
elif PROVIDER == "gemini":
    pill = ("ok", f"AI mode: Gemini {core.GEMINI_MODEL}", "Reads scans with vision", True)
else:
    pill = ("warn", "Demo mode: no AI key", f"OCR: {OCR_NAME}" if OCR_OK else "OCR: not installed", OCR_OK)

ui.inject_css()
st.markdown(ui.header(pill[0], pill[1], pill[2], pill[3], core.provider_label()), unsafe_allow_html=True)

with st.expander("How it reads your documents"):
    if PROVIDER == "groq":
        extract = (f"**Text PDFs** go straight to Groq ({llm.groq_text_model()}), which returns the fields as JSON; "
                   "text-layer PDFs are never rasterised.")
    elif PROVIDER == "gemini":
        extract = (f"**PDFs, scans and photos** are read by Gemini vision ({core.GEMINI_MODEL}) from the page images, "
                   "with the PDF text as a hint.")
    else:
        extract = ("**Demo mode.** No `GROQ_API_KEY` or `GEMINI_API_KEY` is set, so a regex/heuristic extractor reads the "
                   "text of text-layer PDFs (lower confidence, capped at 0.72). Add a Groq key for AI extraction of "
                   "text PDFs with unusual layouts.")
    if PROVIDER == "gemini":
        scans = "**Scans and phone photos** need no OCR here: the vision model reads the picture directly."
    elif OCR_OK:
        scans = (f"**Scans and phone photos** have no text layer, so **{OCR_NAME}** (OCR, on this server, no data leaves "
                 f"it for this step) reads the page text first, and then {'Groq' if PROVIDER == 'groq' else 'the heuristic parser'} "
                 "extracts the fields. These rows are marked `source: OCR` and their confidence is capped at "
                 f"{core.OCR_CONFIDENCE_CAP:.2f}.")
    else:
        scans = ("**Scans and phone photos** have no text layer and **no OCR backend is installed here**, so they are "
                 "sent to Needs review instead of being guessed. Install `requirements-ocr.txt` (RapidOCR), or add a "
                 "Gemini key to read them.")
    st.markdown(f"- {extract}\n- {scans}\n"
                "- **Validation.** Every document is cross-checked (line items against the subtotal, subtotal + tax + tip "
                "against the total, missing fields, confidence). Whatever does not add up lands in **Needs review** with "
                "the reason in plain English.\n"
                "- Your files are processed in memory. In AI mode the document text (Groq) or page images (Gemini) are "
                "sent to that provider, so use sample data on a public demo.")

# ---------------------------------------------------------------- input
with st.container(border=True, key="input-card"):
    files = st.file_uploader("Invoices and receipts", type=["pdf", "png", "jpg", "jpeg", "zip"],
                             accept_multiple_files=True, label_visibility="collapsed")
    hint = (f"PDF, PNG, JPG or one ZIP. Up to {core.MAX_FILES} files per batch, "
            f"{core.MAX_PAGES} pages per document, {core.MAX_FILE_BYTES // 1024 // 1024} MB per file.")
    if PROVIDER != "gemini" and not OCR_OK:
        hint += " No OCR is installed, so scans and photos will be flagged for review."
    st.markdown(f'<p class="dx-hint">{ui.esc(hint)}</p>', unsafe_allow_html=True)
    b1, b2 = st.columns(2)
    run_clicked = b1.button("Extract data", type="primary", disabled=not files, key="run_btn",
                            use_container_width=True, icon=":material/play_arrow:")
    sample_clicked = b2.button(f"Try the {N_SAMPLES} sample documents", key="sample_btn", use_container_width=True,
                               icon=":material/auto_awesome:",
                               help="9 fake invoices and receipts (USD/GBP/EUR); one has a wrong total on purpose.")
    st.markdown('<p class="dx-next"><b>What happens next:</b> each file is read in turn with a progress bar, anything '
                'that does not add up is flagged for review, and you download the result as CSV or XLSX.</p>',
                unsafe_allow_html=True)
    progress_slot = st.container()

# Empty state first (so its sample button is read before the batch runs), cleared as soon as a batch starts.
empty_slot = st.empty()
has_results = bool(st.session_state.get("results"))
sample_clicked2 = False
if not has_results:
    with empty_slot.container():
        st.markdown(ui.steps([("Upload", "Drop in PDFs, scans or phone photos, or a single ZIP of them."),
                              ("Extract", "Each document is read and every total is cross-checked."),
                              ("Review and download", "Flagged rows are set apart. Export CSV or XLSX.")]),
                    unsafe_allow_html=True)
        sample_clicked2 = st.columns([1, 1.4, 1])[1].button(f"Try the {N_SAMPLES} sample documents", key="sample_btn2",
                                                            use_container_width=True, icon=":material/auto_awesome:")

if run_clicked or sample_clicked or sample_clicked2:
    empty_slot.empty()
    raw = sample_docs() if (sample_clicked or sample_clicked2) else [(f.name, f.getvalue()) for f in files]
    docs, notes = core.expand_uploads(raw, max_files=core.MAX_FILES)
    if not docs:
        st.error("No PDF, PNG or JPG files found in that upload.")
    else:
        st.session_state.update(results=run_batch(docs, progress_slot), docs=dict(docs), notes=notes)

# ---------------------------------------------------------------- results
results = st.session_state.get("results")
if results:
    for n in st.session_state.get("notes", []):
        if n.startswith("Only the first"):             # batch cap: make it hard to miss
            st.warning(n, icon=":material/warning:")
        else:
            st.caption(f":material/warning: {n}")
    df, items = core.to_df(results), core.items_df(results)
    s = core.summarize(df)
    review = df[df.needs_review]

    st.markdown('<div class="dx-section">Results</div>', unsafe_allow_html=True)
    totals = list(s["totals"].items())[:3]
    with st.container(key="metrics-counts"):           # two rows of cards: counts, then one total per currency
        cols = st.columns(3)
        cols[0].metric("Files processed", s["files"], border=True)
        cols[1].metric("Clean", s["clean"], border=True)
        cols[2].metric("Needs review", s["flagged"], border=True)
    with st.container(key="metrics-totals"):
        for col, (cur, amt) in zip(st.columns(3), totals):
            col.metric("Total amount", f"{cur} {amt:,.2f}", border=True)
    n_ocr = int((df.source == "ocr").sum())
    kinds = df.doc_type.fillna("unreadable").value_counts()
    summary = ", ".join(plural(n, k) for k, n in kinds.items()) + "."
    if n_ocr:
        summary += f" {n_ocr} read with OCR."
    st.caption(summary + "  Totals include flagged documents."
               + (f"  {len(s['totals']) - 3} more currencies are in the table." if len(s["totals"]) > 3 else ""))

    if len(review):
        st.markdown(ui.callout("bad", f"<b>{plural(len(review), 'document')} {'needs' if len(review) == 1 else 'need'} "
                                      "a human look.</b> Open the Needs review tab to see why, and compare with the "
                                      "original in Preview."), unsafe_allow_html=True)
    else:
        st.markdown(ui.callout("ok", "<b>Every document passed validation.</b> Totals, line items and required fields "
                                     "are consistent."), unsafe_allow_html=True)
    if len(review):                                    # make the tab itself read as a warning
        ui.style('[data-baseweb="tab"]:nth-of-type(2) { color: #DC2626; font-weight: 600; }')

    t_all, t_rev, t_items, t_prev = st.tabs(["All documents", f"Needs review ({len(review)})", "Line items", "Preview"])
    with t_all:
        view = frame_for_view(df, VIEW_COLS)
        st.dataframe(style_view(view, df.needs_review.tolist()), column_config=table_config(VIEW_COLS), hide_index=True)
    with t_rev:
        if review.empty:
            st.success("Nothing needs review.")
        else:
            st.caption("Compare each of these with the original in the Preview tab before booking it.")
            rv = frame_for_view(review, REVIEW_COLS)
            st.dataframe(style_view(rv, [True] * len(rv)), column_config=table_config(REVIEW_COLS), hide_index=True)
            st.markdown('<div class="dx-card-title" style="margin-top:16px">Why each one was flagged</div>',
                        unsafe_allow_html=True)
            for _, row in review.iterrows():
                st.markdown(ui.callout("bad", f"<b>{ui.esc(row['file'])}</b><br>{ui.esc(row['review_reason'])}"),
                            unsafe_allow_html=True)
    with t_items:
        st.dataframe(items.style.format(na_rep="").format({c: "{:,.2f}" for c in MONEY if c in items.columns}, na_rep=""),
                     column_config={"qty": st.column_config.NumberColumn("qty", format="%g")}, hide_index=True)
    with t_prev:
        pick = st.selectbox("Document", [r["file"] for r in results], key="preview_pick")
        r = next(x for x in results if x["file"] == pick)
        d = r["document"]
        left, right = st.columns(2)
        try:
            left.image(core.render_first_page(st.session_state["docs"][pick], pick), use_container_width=True)
        except Exception as e:
            left.write(f"No preview: {e}")
        if r["reasons"]:
            right.markdown(ui.callout("bad", f"<b>Needs review.</b> {ui.esc(r['reasons'])}"), unsafe_allow_html=True)
        else:
            right.markdown(ui.callout("ok", "<b>Clean.</b> It passed every validation check."), unsafe_allow_html=True)
        money = f"{d.currency or ''} {d.total:,.2f}".strip() if d.total is not None else "-"
        right.markdown(ui.facts([("Vendor", ui.esc(d.vendor or "-")), ("Document no.", ui.esc(d.document_number or "-")),
                                 ("Date", ui.esc(d.date or "-")), ("Total", ui.esc(money)),
                                 ("Confidence", f"{d.confidence:.2f}"),
                                 ("Source", ui.tag("OCR", "") if r.get("source") == "ocr"
                                  else ui.esc(SOURCE_NAMES.get(r.get("source", ""), "-") or "-"))]),
                       unsafe_allow_html=True)
        if r.get("source") == "ocr":
            right.caption(f"Read from OCR text, so confidence is capped at {core.OCR_CONFIDENCE_CAP:.2f}. "
                          "Check the digits against the original on the left.")
        with right.expander("Extracted JSON"):
            st.json(d.model_dump())

    with st.container(border=True, key="download-card"):
        st.markdown('<p class="dx-card-title">Download</p><p class="dx-hint">CSV for quick imports. The XLSX has '
                    'three sheets: documents, needs_review (flagged rows highlighted) and line_items.</p>',
                    unsafe_allow_html=True)
        sheet_on = bool(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") and os.getenv("SHEET_ID"))
        d1, d2, *d3 = st.columns(3 if sheet_on else 2)
        d1.download_button("Download CSV", df.to_csv(index=False).encode(), "docextract.csv", "text/csv", key="dl_csv",
                           use_container_width=True, icon=":material/download:")
        d2.download_button("Download XLSX", core.xlsx_bytes(df, items), "docextract.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_xlsx",
                           use_container_width=True, icon=":material/table_view:")
        if sheet_on and d3[0].button("Push to Google Sheet", key="push_btn", use_container_width=True,
                                     icon=":material/cloud_upload:"):
            try:
                st.info(core.push_to_sheet(df))
            except Exception as e:
                st.error(f"Sheet error: {e}")

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
st.divider()
st.caption(f"Reads the first {core.MAX_PAGES} pages of each document, up to {core.MAX_FILES} files per batch. "
           "Always review flagged rows before booking them.")
st.caption(f"AI provider: {core.provider_label()}")
