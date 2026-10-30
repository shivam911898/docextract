"""DocExtract look and feel: the shared portfolio design system as one stylesheet plus a few HTML helpers.

Tokens (same in all four portfolio apps): Inter, background #F8FAFC, surface #FFFFFF, text #0F172A, muted #64748B,
border #E2E8F0, primary #4F46E5 (hover #4338CA, soft #EEF2FF), accent #14B8A6, success #16A34A / #DCFCE7, warning
#D97706 / #FEF3C7, danger #DC2626 / #FEE2E2, radius 12px, 8px spacing grid. The Streamlit theme itself lives in
.streamlit/config.toml; this file covers what a theme cannot (cards, pills, step cards, hidden chrome).

Every helper returns an HTML string for st.markdown(..., unsafe_allow_html=True). Anything that can come from an
uploaded document (file names, vendors, review reasons) must go through esc() first.
"""
from __future__ import annotations

import html
from typing import Iterable, Optional

import streamlit as st

COLORS = {"bg": "#F8FAFC", "surface": "#FFFFFF", "text": "#0F172A", "muted": "#64748B", "border": "#E2E8F0",
          "primary": "#4F46E5", "primary_hover": "#4338CA", "primary_soft": "#EEF2FF", "accent": "#14B8A6",
          "ok": "#16A34A", "ok_soft": "#DCFCE7", "warn": "#D97706", "warn_soft": "#FEF3C7",
          "danger": "#DC2626", "danger_soft": "#FEE2E2"}

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
  --dx-bg: #F8FAFC; --dx-surface: #FFFFFF; --dx-text: #0F172A; --dx-muted: #64748B; --dx-border: #E2E8F0;
  --dx-primary: #4F46E5; --dx-primary-hover: #4338CA; --dx-primary-soft: #EEF2FF; --dx-accent: #14B8A6;
  --dx-ok: #16A34A; --dx-ok-soft: #DCFCE7; --dx-warn: #D97706; --dx-warn-soft: #FEF3C7;
  --dx-danger: #DC2626; --dx-danger-soft: #FEE2E2;
  --dx-radius: 12px;
  --dx-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 4px 16px rgba(15, 23, 42, 0.06);
}

/* ---- chrome: no menu, no deploy button, no footer; the sidebar is not used ---- */
#MainMenu, footer, .stDeployButton, [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] { display: none !important; }
[data-testid="stHeader"] { background: transparent; height: 2rem; }
.stApp { background: var(--dx-bg); color: var(--dx-text); }
[data-testid="stMainBlockContainer"], .block-container { max-width: 1120px; padding: 1.5rem 1.5rem 4rem; }
h1, h2, h3 { letter-spacing: -0.02em; }

/* ---- header ---- */
.dx-header { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin: 8px 0 0; }
.dx-brand { display: flex; align-items: center; gap: 12px; }
.dx-logo { width: 40px; height: 40px; border-radius: 12px; background: var(--dx-primary); display: grid; place-items: center; box-shadow: var(--dx-shadow); }
.dx-logo svg { width: 22px; height: 22px; }
.dx-title { font-size: 1.75rem; font-weight: 700; line-height: 1.15; letter-spacing: -0.025em; margin: 0; }
.dx-sub { color: var(--dx-muted); font-size: 1rem; line-height: 1.5; margin: 12px 0 16px; max-width: 46rem; }
.dx-pill { display: inline-flex; align-items: center; flex-wrap: wrap; gap: 8px; padding: 8px 16px; border-radius: 999px; font-size: 0.8125rem; font-weight: 600; line-height: 1.2; border: 1px solid transparent; white-space: normal; }
.dx-pill--ok { background: var(--dx-ok-soft); color: #166534; border-color: #BBF7D0; }
.dx-pill--warn { background: var(--dx-warn-soft); color: #92400E; border-color: #FDE68A; }
.dx-dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; flex: none; }
.dx-sep { width: 1px; height: 14px; background: currentColor; opacity: 0.3; }
.dx-pill-off { text-decoration: underline dotted; }

/* ---- cards (bordered containers, expanders, metrics) ---- */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) { border-radius: var(--dx-radius); }
div[data-testid="stVerticalBlockBorderWrapper"][class*="st-emotion"], .st-key-input-card, .st-key-download-card {
  background: var(--dx-surface); border: 1px solid var(--dx-border); border-radius: var(--dx-radius); box-shadow: var(--dx-shadow);
}
.st-key-input-card, .st-key-download-card { padding: 24px; }
[data-testid="stExpander"] { background: var(--dx-surface); border: 1px solid var(--dx-border); border-radius: var(--dx-radius); box-shadow: none; }
[data-testid="stExpander"] details, [data-testid="stExpander"] summary { border-radius: var(--dx-radius); }
[data-testid="stExpander"] summary { font-weight: 600; }
[data-testid="stMetric"] { background: var(--dx-surface); border: 1px solid var(--dx-border); border-radius: var(--dx-radius);
  box-shadow: var(--dx-shadow); padding: 16px 20px; }
[data-testid="stMetricLabel"] { color: var(--dx-muted); font-size: 0.8125rem; font-weight: 500; }
[data-testid="stMetricValue"] { font-weight: 650; letter-spacing: -0.02em; font-size: 1.625rem; }

/* ---- uploader ---- */
[data-testid="stFileUploaderDropzone"] { background: var(--dx-primary-soft); border: 1.5px dashed #A5B4FC; border-radius: var(--dx-radius); padding: 24px; }
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--dx-primary); }
[data-testid="stFileUploaderDropzone"] button { border-radius: 10px; }

/* ---- buttons ---- */
.stButton > button, .stDownloadButton > button, [data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-primary"] {
  border-radius: var(--dx-radius); min-height: 2.75rem; font-weight: 600; transition: background-color .15s, border-color .15s, color .15s, box-shadow .15s; }
[data-testid="stBaseButton-primary"] { background: var(--dx-primary); border-color: var(--dx-primary); color: #fff; box-shadow: 0 1px 2px rgba(79, 70, 229, 0.3); }
[data-testid="stBaseButton-primary"]:hover:not(:disabled) { background: var(--dx-primary-hover); border-color: var(--dx-primary-hover); color: #fff; }
[data-testid="stBaseButton-primary"]:disabled { background: #C7D2FE; border-color: #C7D2FE; color: #fff; box-shadow: none; }
[data-testid="stBaseButton-secondary"] { background: var(--dx-surface); border: 1px solid var(--dx-border); color: var(--dx-text); }
[data-testid="stBaseButton-secondary"]:hover:not(:disabled) { background: var(--dx-primary-soft); border-color: #A5B4FC; color: var(--dx-primary-hover); }
button:focus-visible { outline: 2px solid var(--dx-primary); outline-offset: 2px; }

/* ---- tabs ---- */
[data-baseweb="tab-list"] { gap: 8px; }
[data-baseweb="tab"] { height: 2.75rem; padding: 0 12px; font-weight: 500; color: var(--dx-muted); }
[data-baseweb="tab"][aria-selected="true"] { color: var(--dx-primary); font-weight: 600; }
[data-baseweb="tab-highlight"] { background-color: var(--dx-primary) !important; height: 2px; }
[data-baseweb="tab-border"] { background-color: var(--dx-border); }

/* ---- tables and progress ---- */
[data-testid="stDataFrame"] { border: 1px solid var(--dx-border); border-radius: var(--dx-radius); overflow: hidden; box-shadow: var(--dx-shadow); }
[data-testid="stProgress"] [role="progressbar"] > div { background-color: var(--dx-primary); }

/* ---- text helpers ---- */
.dx-section { font-size: 1.125rem; font-weight: 650; letter-spacing: -0.01em; margin: 32px 0 8px; }
.dx-card-title { font-size: 1rem; font-weight: 650; margin: 0 0 4px; }
.dx-muted { color: var(--dx-muted); font-size: 0.875rem; line-height: 1.5; margin: 0; }
.dx-hint { color: var(--dx-muted); font-size: 0.875rem; line-height: 1.5; margin: 8px 0 16px; }
.st-key-input-card [data-testid="stProgress"] { margin-top: 16px; }
.dx-next { color: var(--dx-muted); font-size: 0.8125rem; line-height: 1.5; margin: 12px 0 0; }
.dx-next b { color: var(--dx-text); font-weight: 600; }
.dx-warn-text { color: #92400E; }

/* ---- empty state: three steps ---- */
.dx-steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin: 24px 0 16px; }
.dx-step { position: relative; background: var(--dx-surface); border: 1px solid var(--dx-border); border-radius: var(--dx-radius); padding: 24px; box-shadow: var(--dx-shadow); }
.dx-step-num { width: 32px; height: 32px; border-radius: 50%; background: var(--dx-primary-soft); color: var(--dx-primary); font-weight: 700; display: grid; place-items: center; margin-bottom: 16px; }
.dx-step-title { font-weight: 650; font-size: 1rem; margin: 0 0 4px; }
.dx-step-body { color: var(--dx-muted); font-size: 0.875rem; line-height: 1.5; margin: 0; }
.dx-step:not(:last-child)::after { content: ""; position: absolute; top: 40px; right: -13px; width: 10px; height: 10px; border-top: 2px solid #94A3B8; border-right: 2px solid #94A3B8; transform: rotate(45deg); background: transparent; }

/* ---- callouts, key facts ---- */
.dx-callout { border-radius: var(--dx-radius); padding: 16px 20px; font-size: 0.9375rem; line-height: 1.5; margin: 16px 0; border: 1px solid transparent; }
.dx-callout b { font-weight: 650; }
.dx-callout--bad { background: var(--dx-danger-soft); border-color: #FECACA; color: #991B1B; }
.dx-callout--ok { background: var(--dx-ok-soft); border-color: #BBF7D0; color: #166534; }
.dx-callout--info { background: var(--dx-primary-soft); border-color: #C7D2FE; color: #3730A3; }
.dx-facts { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 16px; margin: 16px 0; }
.dx-fact-k { color: var(--dx-muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em; }
.dx-fact-v { font-weight: 600; font-size: 0.9375rem; word-break: break-word; }
.dx-tag { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 0.75rem; font-weight: 600; background: #CCFBF1; color: #0F766E; }
.dx-tag--bad { background: var(--dx-danger-soft); color: #991B1B; }
.dx-tag--ok { background: var(--dx-ok-soft); color: #166534; }

/* ---- small screens ---- */
@media (max-width: 640px) {
  [data-testid="stMainBlockContainer"], .block-container { padding: 1rem 1rem 3rem; }
  .dx-title { font-size: 1.5rem; }
  .dx-steps { grid-template-columns: 1fr; }
  .dx-step:not(:last-child)::after { display: none; }
  .st-key-input-card, .st-key-download-card { padding: 16px; }
  [data-testid="stFileUploaderDropzone"] { padding: 16px; }
  .st-key-metrics-counts [data-testid="stHorizontalBlock"], .st-key-metrics-totals [data-testid="stHorizontalBlock"] { flex-wrap: wrap; gap: 8px; }
  .st-key-metrics-counts [data-testid="stColumn"] { min-width: calc(50% - 8px) !important; flex: 1 1 calc(50% - 8px) !important; width: calc(50% - 8px) !important; }
  .st-key-metrics-totals [data-testid="stColumn"] { min-width: 100% !important; flex: 1 1 100% !important; width: 100% !important; }
  [data-testid="stMetric"] { padding: 12px 16px; }
  [data-testid="stMetricValue"] { font-size: 1.375rem; }
  .dx-facts { grid-template-columns: 1fr; }
}
"""

LOGO = ('<svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>'
        '<path d="M9 13h6M9 17h4"/></svg>')


def esc(value) -> str:
    """HTML-escape anything that may come from an uploaded document."""
    return html.escape("" if value is None else str(value), quote=True)


def inject_css() -> None:
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def style(css: str) -> None:
    """Extra one-off rules, e.g. colouring the Needs review tab only when something is flagged."""
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def header(kind: str, status: str, ocr: Optional[str], ocr_ok: bool, tooltip: str) -> str:
    """Product name, one-line value proposition and the compact status pill (green = AI, amber = demo mode)."""
    ocr_html = ""
    if ocr:
        ocr_html = (f'<span class="dx-sep"></span><span class="{"" if ocr_ok else "dx-pill-off"}">{esc(ocr)}</span>')
    return (
        '<div class="dx-header">'
        f'<div class="dx-brand"><div class="dx-logo">{LOGO}</div><h1 class="dx-title">DocExtract</h1></div>'
        f'<div class="dx-pill dx-pill--{kind}" title="{esc(tooltip)}"><span class="dx-dot"></span>'
        f'<span>{esc(status)}</span>{ocr_html}</div></div>'
        '<p class="dx-sub">Invoices and receipts in, clean validated spreadsheet rows out. Anything that does not '
        'add up goes to Needs review instead of being silently trusted.</p>')


def steps(items: Iterable[tuple]) -> str:
    cards = "".join(f'<div class="dx-step"><div class="dx-step-num">{n}</div><p class="dx-step-title">{esc(t)}</p>'
                    f'<p class="dx-step-body">{esc(b)}</p></div>' for n, (t, b) in enumerate(items, 1))
    return f'<div class="dx-steps">{cards}</div>'


def callout(kind: str, text_html: str) -> str:
    return f'<div class="dx-callout dx-callout--{kind}">{text_html}</div>'


def facts(pairs: Iterable[tuple]) -> str:
    cells = "".join(f'<div><div class="dx-fact-k">{esc(k)}</div><div class="dx-fact-v">{v}</div></div>' for k, v in pairs)
    return f'<div class="dx-facts">{cells}</div>'


def tag(text: str, kind: str = "") -> str:
    return f'<span class="dx-tag{" dx-tag--" + kind if kind else ""}">{esc(text)}</span>'
