"""DocExtract - Streamlit UI. Run: streamlit run app.py"""
import os
from pathlib import Path

import streamlit as st

import core
import llm

SAMPLES = Path(__file__).parent / "samples"
VIEW_COLS = ["file", "doc_type", "vendor", "document_number", "date", "currency", "subtotal", "tax", "tip",
             "total", "payment_method", "confidence", "needs_review", "review_reason"]

st.set_page_config(page_title="DocExtract", page_icon=":material/receipt_long:", layout="wide")


def sample_docs():
    """Bundled demo files (regenerated on the fly if the folder is missing)."""
    if not any(SAMPLES.glob("*")):
        try:
            import make_samples
            make_samples.main()
        except Exception:
            return []
    return [(p.name, p.read_bytes()) for p in sorted(SAMPLES.iterdir()) if p.suffix.lower() in core.EXTS]


def run_batch(docs):
    """Process documents one by one with a live progress bar; returns result dicts."""
    bar = st.progress(0.0, text="Starting...")
    results = []
    for n, (name, data) in enumerate(docs, 1):
        bar.progress((n - 1) / len(docs), text=f"Reading {name}  ({n} of {len(docs)})")
        results.append(core.process_file(name, data))
    bar.progress(1.0, text=f"Done - {len(docs)} document(s) processed")
    return results


def highlight(row):
    return ["background-color: #fde2e1"] * len(row) if row["needs_review"] else [""] * len(row)


# ------------------------------------------------------------------ header
st.title("DocExtract")
st.caption("Invoices and receipts in, clean validated spreadsheet rows out. Anything suspicious is routed to "
           "**Needs review** instead of being silently trusted.")

PROVIDER = core.active_provider()
if PROVIDER == "groq":
    scans = ("Scans and photos are OCR'd locally with Docling first." if core.docling_available() else
             "Scans and photos have no text to read, so they go to Needs review (they need a Gemini key or the "
             "Docling OCR backend).")
    st.success(f"AI mode: Groq ({llm.groq_text_model()}) reads text-layer PDFs. {scans}", icon=":material/auto_awesome:")
elif PROVIDER == "gemini":
    st.success(f"AI mode: Gemini vision ({core.GEMINI_MODEL}) reads PDFs, scans and photos.", icon=":material/auto_awesome:")
else:
    st.warning("**No-key demo mode.** No GROQ_API_KEY or GEMINI_API_KEY is set, so a regex/heuristic extractor reads "
               "text-layer PDFs only (lower confidence). Images and scans are flagged as needing review. Add a Groq "
               "key for AI extraction of text PDFs with unusual layouts; scans and photos need a Gemini key or the "
               "Docling OCR backend.", icon=":material/info:")

# ------------------------------------------------------------------ input
files = st.file_uploader("Upload invoices and receipts (PDF, PNG, JPG), several at once or one .zip",
                         type=["pdf", "png", "jpg", "jpeg", "zip"], accept_multiple_files=True)
b1, b2, _ = st.columns([1, 1, 4])
run_clicked = b1.button("Extract data", type="primary", disabled=not files, key="run_btn")
sample_clicked = b2.button("Try the sample documents", key="sample_btn",
                           help="9 fake invoices and receipts (USD/GBP/EUR); one has a wrong total on purpose.")

if run_clicked or sample_clicked:
    raw = sample_docs() if sample_clicked else [(f.name, f.getvalue()) for f in files]
    docs, notes = core.expand_uploads(raw, max_files=core.MAX_FILES)
    if not docs:
        st.error("No PDF, PNG or JPG files found in that upload.")
    else:
        st.session_state.update(results=run_batch(docs), docs=dict(docs), notes=notes)

# ------------------------------------------------------------------ results
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

    totals = list(s["totals"].items())[:3]
    cols = st.columns(3 + len(totals))
    cols[0].metric("Files processed", s["files"], border=True)
    cols[1].metric("Clean", s["clean"], border=True)
    cols[2].metric("Needs review", s["flagged"], border=True)
    for col, (cur, amt) in zip(cols[3:], totals):
        col.metric(f"Total amount ({cur})", f"{amt:,.2f}", border=True)
    kinds = df.doc_type.fillna("unreadable").value_counts()
    st.caption(" | ".join(f"{n} {k}" for k, n in kinds.items()) + ".  Totals include flagged documents.")

    t_all, t_rev, t_items, t_prev = st.tabs(["All documents", f"Needs review ({len(review)})", "Line items", "Preview"])
    cfg = {"confidence": st.column_config.ProgressColumn("confidence", min_value=0, max_value=1, format="%.2f"),
           "needs_review": st.column_config.CheckboxColumn("needs review"),
           "review_reason": st.column_config.TextColumn("review_reason", width=640)}
    with t_all:
        st.dataframe(df[VIEW_COLS].style.apply(highlight, axis=1), column_config=cfg, hide_index=True)
    with t_rev:
        if review.empty:
            st.success("Nothing needs review.")
        else:
            st.dataframe(review[["file", "vendor", "document_number", "total", "confidence", "review_reason"]],
                         column_config=cfg, hide_index=True)
    with t_items:
        st.dataframe(items, hide_index=True)
    with t_prev:
        pick = st.selectbox("Document", [r["file"] for r in results], key="preview_pick")
        r = next(x for x in results if x["file"] == pick)
        left, right = st.columns(2)
        try:
            left.image(core.render_first_page(st.session_state["docs"][pick], pick), width=480)
        except Exception as e:
            left.write(f"No preview: {e}")
        if r["reasons"]:
            right.error(r["reasons"], icon=":material/flag:")
        right.json(r["document"].model_dump())

    d1, d2, d3 = st.columns([1, 1, 4])
    d1.download_button("Download CSV", df.to_csv(index=False).encode(), "docextract.csv", "text/csv", key="dl_csv")
    d2.download_button("Download XLSX", core.xlsx_bytes(df, items), "docextract.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dl_xlsx")
    if os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") and os.getenv("SHEET_ID"):
        if d3.button("Push to Google Sheet", key="push_btn"):
            try:
                st.info(core.push_to_sheet(df))
            except Exception as e:
                st.error(f"Sheet error: {e}")
else:
    st.info("Drop files above and click **Extract data**, or press **Try the sample documents** to see it work.")

st.divider()
st.caption(f"Reads the first {core.MAX_PAGES} pages of each document, up to {core.MAX_FILES} files per batch. "
           "Always review flagged rows before booking them.")
st.caption(f"AI provider: {core.provider_label()}")
