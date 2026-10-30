# DocExtract: invoices and receipts to clean, validated Excel

Drop in a pile of invoice and receipt PDFs, scans or phone photos (or one ZIP). Get one validated row per document,
every line item, and a separate **Needs review** sheet for anything that does not add up.

**Live demo:** <https://docextract-9vrp.onrender.com> *(free Render instance: it sleeps after about 15 minutes idle, so the first load can take about a minute; click "Try the sample documents")*

## The problem
Small businesses, bookkeepers and agencies still retype vendor, number, date, tax and total from hundreds of
documents into spreadsheets. It is slow (3-5 minutes per document by hand is a fair estimate), and one mistyped total
quietly corrupts the books. Generic OCR tools hand you raw text and no way to know which numbers to distrust.

## What it does
- **Invoices and receipts**, auto-detected per document (`invoice` / `receipt` / `other`).
- **Batch intake**: many files at once, or a single `.zip`. PDF (text or scanned), PNG, JPG, phone photos.
- **Scans and photos are read**: a lightweight CPU OCR (RapidOCR, about 16 MB of models) turns them into text for the model, so a photographed receipt works even on the free 512 MB demo. OCR rows are marked `source: ocr` and their confidence is capped at 0.85.
- **Structured output**: vendor / merchant, document number, date (ISO), currency, line items, subtotal, tax, tip, total, payment method, confidence, source.
- **Summary cards**: files processed, clean, flagged, and total amount per currency (`USD 2,259.22`; USD, GBP and EUR are never added together).
- **Validation**: arithmetic cross-checks; failures land in **Needs review** with the reason in plain English.
- **Exports**: CSV and XLSX (sheets `documents`, `needs_review`, `line_items`; flagged rows highlighted), optional Google Sheets append.
- **Works with no API key** in a clearly labelled demo mode (amber status pill), so anyone can try it instantly.
- **AI provider of your choice**: Groq (free-tier key, text) by default, Gemini optional (reads page images directly).

## Screenshots
Captured from the running app with a Groq key: the status pill is green (`AI mode: Groq gpt-oss-120b | OCR: RapidOCR`),
and the PNG phone-style receipt in the sample set is read by OCR (marked `source: OCR`) instead of being flagged. Without a
key the pill is amber (`Demo mode`) and a heuristic parser reads the same OCR text with lower confidence.

| Home screen: status pill, uploader, sample button, the three steps | Summary cards and all documents (flagged rows in red) |
|---|---|
| ![Home screen](docs/screenshot-upload.png) | ![Results](docs/screenshot-results.png) |

**Needs review tab**: only the Greenleaf invoice is flagged (`subtotal+tax 1158.84 != total 1196.34`); the OCR'd receipt reads
`HARBOR STREET GRILL`, total 90.68, and its sums agree.

![Needs review tab](docs/screenshot-needs-review.png)

## How it works
```
 PDF / PNG / JPG / ZIP
        |  ingest: unzip in memory, read the text layer (pypdf), render pages (pypdfium2)
        v
 extract
   text-layer PDF -- GROQ_API_KEY -----> Groq text model (openai/gpt-oss-120b), JSON mode, schema in the prompt
   scan or photo --- GEMINI_API_KEY ---> Gemini vision (gemini-3.1-flash-lite), JSON constrained to the Document schema
   scan or photo --- Groq --------------> OCR (Docling if installed, else RapidOCR / Tesseract) -> text -> Groq text model
   no key ---------------------------> regex / heuristic parser over the text layer, or over the OCR text of a scan or photo (lower confidence)
   scan or photo with no OCR / vision route -> Needs review row, never a guess
        v
 validate: totals cross-checks, missing fields, confidence   ->  needs_review + reason
        v
 table in the UI  ->  CSV / XLSX / optional Google Sheet
```
- **Ingest**: up to 3 pages per document are read (`MAX_PAGES`); zip members are read in memory, never written to disk, and path tricks are stripped.
- **Extract (Groq)**: the PDF text goes to the Groq text model through plain `httpx` (OpenAI-compatible `/chat/completions`, JSON mode, `temperature=0`) with the schema spelled out in the prompt, and the reply is parsed into the same typed `Document`. Rate-limit and overload responses (HTTP 429/500/502/503/504) and network errors are retried with exponential backoff (a `Retry-After` is honoured); a bad key or a model that no longer exists fails at once. Anything unparseable becomes a Needs review row.
- **Extract (Gemini)**: the page images and the PDF text go to `gemini-3.1-flash-lite` through `google-genai` with a pydantic response schema (`temperature=0`), with the same retry rules.
- **Extract (no-key mode)**: layout-preserving text from `pypdf`, then regex rules for labels (`Subtotal`, `VAT (20%)`, `Total Due`, `Includes VAT`, `Tip`), five date styles (ISO, `03/14/2025`, `07.06.2025`, `09 June 2025`, `Jun 21, 2025`; ambiguous day/month order is decided by currency), currency symbols and codes, and four line-item layouts (qty/unit/amount columns, `2 @ 3.49`, `2 x item`, price-only). Confidence is capped at 0.72 on purpose.
- **Lightweight OCR for scans and photos** (`ocr.py`, `OCR_BACKEND`): a file with no text layer (image, phone photo, scanned PDF page) is OCR'd and the text is handled like any text PDF (Groq text model, or the heuristic parser without a key). Precedence: Docling if installed, else **RapidOCR** (PaddleOCR PP-OCRv4 models on onnxruntime, CPU only, `requirements-ocr.txt`), else Tesseract (`pytesseract` plus the `tesseract` binary), else the Needs review row. PDF pages are rendered with pypdfium2, photos honour their EXIF rotation, and anything above about 1 megapixel is shrunk first because the detector's memory grows with pixels. The engine loads on first use and processes one page at a time. The OCR step is told the text is OCR output (it restores run-together words but copies digits exactly); rows read this way carry `source: ocr`, their confidence is capped at 0.85 and never exceeds the engine's own average confidence, and validation is unchanged.
- **Optional Docling backend** (`pip install -r requirements-docling.txt`): IBM's [Docling](https://github.com/docling-project/docling) layout/table model plus OCR. If it is installed it is used instead of the lightweight OCR for scans and photos. With `EXTRACT_BACKEND=docling` and no key, text PDFs are parsed from both the Docling and the pypdf text and the parse that validates cleaner wins. It is heavy (about 1.6 GB of packages, about 650 MB of models downloaded on first use; roughly 3-5 s per PDF and 15-30 s per image on a laptop CPU), so it is off by default and not installed on the free Render demo.
- **Document model**: `core.py` -> `Document` (doc type, vendor, number, date, currency, line items, subtotal, tax, tip, total, payment method, confidence).

## AI provider
Pick the provider with `LLM_PROVIDER` (`groq` | `gemini` | `none`). If it is unset: Groq when `GROQ_API_KEY` is set, else Gemini when `GEMINI_API_KEY` is set, else `none` (the offline demo mode). A provider whose key is missing falls back to `none`.

| Provider | Reads | Needs | Notes |
|----------|-------|-------|-------|
| **Groq** (default when its key is set) | text-layer PDFs; scans and photos through OCR (RapidOCR in the Docker image, or Docling / Tesseract) | free key from <https://console.groq.com/keys> | default model `openai/gpt-oss-120b` (`GROQ_TEXT_MODEL=openai/gpt-oss-20b` is the faster, cheaper option). Groq currently serves **no vision-capable model**, so it never sees page images: it reads the OCR text instead. With no OCR backend installed a scan or photo becomes a Needs review row: `scanned image: needs a vision provider (Gemini) or an OCR backend (RapidOCR, Tesseract or Docling)`. |
| **Gemini** (optional) | PDFs, scans and photos with vision | free key from <https://aistudio.google.com/apikey> | `gemini-3.1-flash-lite`; Gemini 2.x Flash models return 404 on the free tier. Set `LLM_PROVIDER=gemini` when both keys exist and you have scans you want read from the image itself. |
| **none** | text-layer PDFs with regex rules; scans and photos via OCR text | nothing (OCR optional) | lower confidence (capped at 0.72, and at 0.85 for anything OCR'd); without an OCR backend images and scans are flagged |

The status pill at the top of the app shows which of these is active and which OCR is installed (`AI mode: Groq gpt-oss-120b | OCR: RapidOCR`, green; `Demo mode: no AI key`, amber; `OCR: not installed` when the package is missing, in which case the app still works and says scans will be flagged). `core.provider_label()` and the footer print the same.

### OCR (`OCR_BACKEND`)
| Value | Meaning |
|-------|---------|
| `auto` (default) | RapidOCR if `rapidocr_onnxruntime` imports, else Tesseract if `pytesseract` and the `tesseract` binary exist, else off. An installed Docling is always preferred for scans and photos. |
| `rapidocr` / `tesseract` | use only that engine (off if it is not installed) |
| `none` | switch the lightweight OCR off (the Needs review row for scans comes back) |

Install: `pip install -r requirements-ocr.txt` then `pip install --no-deps rapidocr-onnxruntime==1.4.4` (the Dockerfile does both; the two-step install swaps the full OpenCV for the headless build so no system libraries are needed). Needs Python below 3.13. Measured on this repo (Windows, CPU, 1 thread): the engine loads in about 0.5 s on first use, the sample PNG takes about 1-3 s, and the Streamlit server process peaked at about 310-330 MB RSS after reading the whole sample batch (about 110 MB of that is Streamlit and pandas, about 70 MB the loaded OCR models, the rest transient detector memory). A 12-megapixel phone photo is shrunk to the pixel budget first (`OCR_MAX_PIXELS`, default 1,000,000); without that its peak was about 490 MB. On the free Render instance (0.1 CPU) expect OCR to be several times slower than on a laptop (an estimate, not measured there).

Groq retires and renames models; confirm the current ids with `GET https://api.groq.com/openai/v1/models` (header `Authorization: Bearer $GROQ_API_KEY`). A Needs review row mentioning `model_not_found` means the id in `GROQ_TEXT_MODEL` changed. `GROQ_BASE_URL` points the client at any OpenAI-compatible endpoint (the offline tests use a local fake server).

**Live check with your own key:** `python smoke_groq.py` runs the 9 samples through Groq and prints a table (file, type, vendor, total, needs_review, model used, match against the generator's ground truth). It is the only script that calls the real API.

## Accuracy and validation approach
The design assumption is that extraction will sometimes be wrong, so wrong values must be *visible* instead of trusted.

| Check | Flags the row when |
|-------|--------------------|
| Line items vs subtotal | sum of line amounts differs from the subtotal |
| Subtotal + tax (+ tip) vs total | the printed total does not equal subtotal + tax + tip |
| Tax-inclusive receipts | no subtotal printed: items (+ tax / tip) must equal the total, whether prices include tax or not |
| Completeness | total, line items, vendor or date missing |
| Document type | the file is neither an invoice nor a receipt |
| Confidence | model (or heuristic) confidence is below 0.70 |
| Extraction error | unreadable file, scan or photo with no vision / OCR route, malformed model reply, API failure after retries |

Tolerance is 0.5% of the amount or 5 cents, whichever is larger (rounding noise only). Only amounts that actually contradict
each other are flagged; a document whose arithmetic is consistent but whose digits were misread can still pass, which is why
the Preview tab shows the original next to the extracted fields and why a human should skim totals on high-value documents.

**What is tested** (`python verify.py`, offline, no API key, about a minute with the OCR stages):
1. CLI on the 9 bundled samples in no-key mode: 9 processed, the deliberately wrong invoice is flagged, and the 8 text-layer documents match the generator's ground truth on type, vendor, number, date, currency, tax and total; XLSX has the three sheets; the CLI is not capped by `MAX_FILES`.
2. ZIP intake: nested zips, junk files and `../` paths are handled.
3. Gemini code path against a **local fake Gemini server**: two 503s are retried then succeed, JSON parses, and a permanently failing API becomes a Needs review row instead of a crash.
4. Groq code path against a **local fake OpenAI-compatible server**: the text PDF reaches the text model with JSON mode and the schema in the prompt and parses clean; a 429 is retried; a persistent 500, malformed JSON, a schema-breaking reply, a 401 and an exhausted quota each become a Needs review row; scans and photos make no API call and are flagged when no OCR backend exists, and with OCR (stubbed) the OCR text goes to the text model, the row is marked `source: ocr` and its confidence is capped (Docling beats the lightweight OCR; an unsure OCR engine flags the row); provider-selection rules; the CLI and `smoke_groq.py` run end to end against the fake.
5. The Streamlit app via `AppTest`: the status pill (amber demo, green Groq, "OCR: not installed" with `OCR_BACKEND=none`), the explanation expander, the `MAX_FILES` cap warning, the sample batch, the Needs review tab count and `USD 2,259.22`-style total cards.
6. OCR: row grouping, spacing repair, `OCR_BACKEND` selection and the Tesseract adapter (stubbed); and, **when RapidOCR is installed** (skipped with a message otherwise), the real engine: the PNG receipt is read in no-key mode (vendor contains `HARBOR`, total 90.68) and through the fake Groq server, an image-only PDF is rendered and OCR'd, and the wrong-total Greenleaf invoice is still flagged (also as an image-only scan).
7. If Docling is installed: the optional backend reads all 9 samples, including the PNG, and flags only the wrong-total invoice (skipped otherwise).

The fake servers prove the wiring, not the models. **Not verified here:** a real Gemini call, OCR speed on the 0.1 CPU Render instance, and the Docker build itself (no Docker on the dev laptop; the pinned Linux wheels were checked to exist on PyPI). `python smoke_groq.py` is the live Groq check. The bundled samples are synthetic: real accuracy depends on scan quality and layout (blurry or skewed photos read worse, and the OCR model is tuned for English and Chinese, so accented or non-Latin text may be misread), so send a handful of your own documents to see it on yours.

## Run it
```powershell
python -m venv .venv
.venv\Scripts\activate                # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-ocr.txt   # optional but recommended: reads scans and phone photos (RapidOCR, CPU)
pip install --no-deps rapidocr-onnxruntime==1.4.4
copy .env.example .env                # optional: add GROQ_API_KEY (or GEMINI_API_KEY) for AI mode
python make_samples.py                # optional: regenerates samples/ (9 files)
streamlit run app.py                  # web UI
python extract.py samples --out out.csv --xlsx out.xlsx     # CLI (folders, files, zips; add --sheet, --no-key)
python verify.py                      # one-command offline self-check
python smoke_groq.py                  # live Groq check (needs GROQ_API_KEY)
# optional heavier OCR / table backend (on Windows use a short venv path such as C:\dl\v):
#   pip install -r requirements-docling.txt
```

Google Sheets (optional): set `GOOGLE_SERVICE_ACCOUNT_JSON` (path to the key file) and `SHEET_ID` in `.env` and share the sheet with the
service account's email. The **Push to Google Sheet** button appears only when both are set; leave them unset on a public demo.

## Deploy
The live demo runs on **Render's free web service** (Docker runtime): the `Dockerfile` binds to `$PORT`, `render.yaml` is a one-file
blueprint, and `GROQ_API_KEY` is set as an environment variable in the Render dashboard. Free instances sleep after about
15 minutes idle and take about a minute to wake up. The same `Dockerfile` runs on Railway, Fly or any VPS. Hugging Face Spaces
now needs a PRO subscription, so it is no longer the free path. Step-by-step: [`DEPLOY.md`](DEPLOY.md).

## Settings (environment variables)
| Variable | Default | Purpose |
|----------|---------|---------|
| `LLM_PROVIDER` | auto | `groq`, `gemini` or `none`; auto = Groq if its key is set, else Gemini if its key is set, else none |
| `GROQ_API_KEY` | unset | enables Groq (text-layer PDFs) |
| `GROQ_TEXT_MODEL` | `openai/gpt-oss-120b` | Groq model id (`openai/gpt-oss-20b` = faster, cheaper) |
| `GROQ_BASE_URL` | `https://api.groq.com/openai/v1` | any OpenAI-compatible endpoint (tests point it at a local fake) |
| `GEMINI_API_KEY` | unset | enables Gemini vision (scans and photos) |
| `GEMINI_MODEL` | `gemini-3.1-flash-lite` | Gemini model id |
| `OCR_BACKEND` | `auto` | `auto`, `rapidocr`, `tesseract` or `none`: the lightweight OCR for scans and photos (see [OCR](#ocr-ocr_backend)) |
| `OCR_THREADS` | up to 4 | onnxruntime threads for RapidOCR (the Docker image sets 1 for the 0.1 CPU free instance) |
| `OCR_MAX_PIXELS` | 1000000 | pages and photos above this pixel count are shrunk before OCR (memory grows with pixels); also `OCR_MAX_SIDE` (1800) |
| `OCR_LANG` | `eng` | Tesseract language code (Tesseract backend only) |
| `EXTRACT_BACKEND` | `pypdf` | `docling` = optional table backend for no-key mode (an installed Docling is used for scans and photos regardless) |
| `MAX_FILES` | 10 | documents per batch in the web UI, to protect a public demo's free quota (the CLI is uncapped) |
| `MAX_PAGES` | 3 | pages per document read |
| `MAX_FILE_MB` | 15 | per-file size cap |
| `GOOGLE_SERVICE_ACCOUNT_JSON`, `SHEET_ID` | unset | optional Sheets push |

## Limits
- Groq reads text only, so **scans and phone photos go through OCR first** (RapidOCR in the Docker image; Docling or Tesseract if you prefer). OCR can misread digits and run words together on blurry, skewed or low-contrast photos, so OCR'd rows are marked `source: ocr`, capped at confidence 0.85, and still flagged whenever the sums disagree; the Preview tab shows the original next to the extracted fields. Without any OCR backend (and without Gemini) scans and photos are flagged, not guessed. The bundled OCR model is English/Chinese: accented European names may come out approximated. No-key mode understands `1,234.56` number format (comma-decimal documents need an AI provider).
- OCR reads at most `MAX_PAGES` pages and shrinks big pages to about 1 megapixel to stay inside 512 MB, so very small print on a full A4 scan can be lost; raise `OCR_MAX_PIXELS` on a bigger host.
- Only the first 3 pages of each document are read; a long multi-page statement needs an extension.
- Uploaded files are processed in memory, but in AI mode their text (Groq) or page images (Gemini) are sent to that provider's API. Use sample data on a public demo.
- One bill per file: a PDF containing several invoices is treated as one document.
- Free tier APIs are rate-limited; large batches on a shared key will slow down or fail rows (flagged, never silent). The web UI caps a batch at `MAX_FILES`.
- Estimated saving: about 3-4 minutes per document versus manual entry, roughly 6 hours per 100 documents (estimate, varies by document).
- Always keep a human in the loop for flagged rows.

## Files
`app.py` Streamlit UI | `ui.py` design system CSS + HTML helpers | `.streamlit/config.toml` theme | `core.py` extraction + validation + exports | `llm.py` provider selection + Groq client |
`ocr.py` lightweight OCR (RapidOCR / Tesseract) | `extract.py` CLI | `make_samples.py` sample generator | `verify.py` offline self-check | `smoke_groq.py` live Groq check |
`requirements-ocr.txt` OCR packages | `requirements-docling.txt` optional heavy backend |
`DEPLOY.md` | `render.yaml` Render blueprint | `deploy/HF_SPACE_README.md` HF Space config (PRO only) | `DEMO_SCRIPT.md` | `GIG.md` | `Dockerfile` | MIT licensed.

---
Built by Shivam Kumar Yadav · sak23571113@gmail.com · github.com/shivam911898
