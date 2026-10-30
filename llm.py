"""LLM provider selection and the Groq client (OpenAI-compatible chat completions over plain httpx, no SDK).

    LLM_PROVIDER = groq | gemini | none     default: groq if GROQ_API_KEY is set, else gemini if GEMINI_API_KEY is
                                            set, else none (offline regex / heuristic extractor)

Groq is used as a TEXT provider only (no vision-capable model is served on Groq at the moment): text-layer PDFs go
straight to it, scans and photos are OCR'd first (ocr.py: RapidOCR / Tesseract, or Docling) or read by Gemini vision.

Only provider selection and HTTP live here. Prompts, parsing into the pydantic `Document` and validation stay in
core.py. Everything is read from the environment at call time, so tests can point GROQ_BASE_URL at a local fake server.
"""
from __future__ import annotations

import os
import sys
import time
from typing import List, Optional, Tuple

import httpx

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # pragma: no cover
    pass

PROVIDERS = ("groq", "gemini", "none")
GROQ_DEFAULT_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_DEFAULT_TEXT_MODEL = "openai/gpt-oss-120b"   # openai/gpt-oss-20b is the faster / cheaper alternative
GROQ_DEFAULT_FALLBACK_MODEL = "openai/gpt-oss-20b"   # Groq caps tokens per day PER MODEL, so this one still works when the primary is spent
GROQ_RETRY_ATTEMPTS = 5
GROQ_RETRY_DELAY = 2.0          # seconds; doubles after every failed attempt (2, 4, 8, 16)
GROQ_MAX_RETRY_AFTER = 60       # a 429 asking us to wait longer than this (daily quota) fails fast instead
GROQ_TIMEOUT = 90.0
GROQ_MAX_TOKENS = 3072          # reasoning models (gpt-oss) spend ~200 tokens thinking before the JSON; keep headroom
RETRY_STATUS = {429, 500, 502, 503, 504}


# ---------------------------------------------------------------- provider selection
def _has(var: str) -> bool:
    return bool(os.getenv(var, "").strip())


def provider() -> str:
    """Active provider: 'groq', 'gemini' or 'none'. An explicit LLM_PROVIDER wins, but a provider without its key
    degrades to 'none' (the offline demo mode) instead of failing on every document."""
    want = os.getenv("LLM_PROVIDER", "").strip().lower()
    keys = {"groq": _has("GROQ_API_KEY"), "gemini": _has("GEMINI_API_KEY")}
    if want == "none":
        return "none"
    if want in keys:
        return want if keys[want] else "none"
    return next((p for p in ("groq", "gemini") if keys[p]), "none")


def groq_base_url() -> str:
    return (os.getenv("GROQ_BASE_URL") or GROQ_DEFAULT_BASE_URL).rstrip("/")


def groq_text_model() -> str:
    return os.getenv("GROQ_TEXT_MODEL") or GROQ_DEFAULT_TEXT_MODEL


def groq_fallback_model() -> str:
    """Model retried once when the primary one is rate limited. Unset = default; an empty value disables the fallback."""
    v = os.getenv("GROQ_FALLBACK_MODEL")
    return GROQ_DEFAULT_FALLBACK_MODEL if v is None else v.strip()


class GroqRateLimited(RuntimeError):
    """A 429 another model can probably serve: the daily token cap, or still rate limited after all the retries."""


# ---------------------------------------------------------------- Groq chat completions
def _error_text(r: httpx.Response) -> str:
    try:
        e = r.json().get("error")
        msg = e.get("message") if isinstance(e, dict) else e
    except Exception:
        msg = None
    return " ".join(str(msg or r.text or "").split())[:300]


def _retry_after(r: httpx.Response) -> Optional[float]:
    try:
        return max(0.0, float(r.headers.get("retry-after", "")))
    except ValueError:
        return None


def groq_chat_json(messages: List[dict], model: str) -> str:
    """The assistant message text only; see groq_chat_json_model."""
    return groq_chat_json_model(messages, model)[0]


def groq_chat_json_model(messages: List[dict], model: str) -> Tuple[str, str]:
    """Return (assistant message text, model that answered).

    A 429 that says the daily token cap is spent, or that survives all the retries, is retried ONCE with
    GROQ_FALLBACK_MODEL (Groq caps are per model); if that fails too the original error is raised."""
    try:
        return _groq_call(messages, model), model
    except GroqRateLimited as e:
        fallback = groq_fallback_model()
        if not fallback or fallback == model:
            raise
        print(f"[llm] Groq {model} rate limited; retrying once with fallback model {fallback}", file=sys.stderr, flush=True)
        try:
            return _groq_call(messages, fallback), fallback
        except RuntimeError as e2:
            raise RuntimeError(f"{e}; fallback model {fallback} also failed: {e2}") from None


def _groq_call(messages: List[dict], model: str) -> str:
    """POST /chat/completions in JSON mode and return the assistant message text.

    Retries 429/5xx and network errors with exponential backoff (honouring Retry-After); other 4xx fail at once.
    Raises RuntimeError when the API cannot be used, so core.process_file turns it into a Needs review row;
    GroqRateLimited (a RuntimeError) when the cause is a 429."""
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set")
    url = groq_base_url() + "/chat/completions"
    body = {"model": model, "messages": messages, "temperature": 0, "max_tokens": GROQ_MAX_TOKENS,
            "response_format": {"type": "json_object"}}
    headers = {"Authorization": f"Bearer {key}"}
    last, last_status = "no response", None
    with httpx.Client(timeout=GROQ_TIMEOUT) as client:
        for attempt in range(1, GROQ_RETRY_ATTEMPTS + 1):
            delay = GROQ_RETRY_DELAY * 2 ** (attempt - 1)
            try:
                r = client.post(url, json=body, headers=headers)
            except httpx.TransportError as e:                       # timeout, connection reset, DNS ...
                last, last_status = f"{type(e).__name__}: {e}", None
            else:
                if r.status_code == 200:
                    return _message_text(r)
                last, last_status = f"HTTP {r.status_code}: {_error_text(r)}", r.status_code
                if r.status_code == 429 and _daily_cap(r):
                    raise GroqRateLimited(f"Groq {last} (daily token cap; quota exhausted, try later)")
                if r.status_code == 400 and "response_format" in r.text.lower() and "response_format" in body:
                    del body["response_format"]                      # model without JSON mode: the prompt still asks for JSON
                    continue
                if r.status_code not in RETRY_STATUS:
                    raise RuntimeError(f"Groq {last}")
                wait = _retry_after(r)
                if wait is not None:
                    if wait > GROQ_MAX_RETRY_AFTER:
                        raise (GroqRateLimited if r.status_code == 429 else RuntimeError)(
                            f"Groq {last} (asked to wait {wait:.0f}s; quota exhausted, try later)")
                    delay = wait
            if attempt < GROQ_RETRY_ATTEMPTS:
                time.sleep(delay)
    raise (GroqRateLimited if last_status == 429 else RuntimeError)(
        f"Groq API failed after {GROQ_RETRY_ATTEMPTS} attempts ({last})")


def _daily_cap(r: httpx.Response) -> bool:
    t = r.text.lower()
    return "tokens per day" in t or "tpd" in t


def _message_text(r: httpx.Response) -> str:
    try:
        choice = r.json()["choices"][0]
        text = choice["message"]["content"]
    except Exception:
        raise ValueError(f"unexpected Groq reply: {r.text[:200]!r}") from None
    if not text or not str(text).strip():
        raise ValueError(f"Groq returned an empty reply (finish_reason={choice.get('finish_reason')})")
    return str(text)
