# Deploying DocExtract

Primary target for the public demo: **Render** (free web service, Docker runtime). Other options: **Railway / Fly / any VPS**
with the same `Dockerfile`. Hugging Face Spaces is no longer a free path (see the note at the end of section A).

Nothing below was executed from the dev machine (no Render account was available while building). The app itself
is verified locally with `python verify.py`; treat the steps as a checklist and fix the first build error you hit.

**Render blueprint:** `render.yaml` in the project root describes the same service (New -> Blueprint), as a shortcut for steps 2-3 below.

---

## A. Render (free, recommended for the demo)

The `Dockerfile` installs `requirements.txt` and the lightweight OCR (`requirements-ocr.txt` plus
`rapidocr-onnxruntime==1.4.4` with `--no-deps`, which keeps the image free of system GUI libraries), regenerates the
sample documents inside the image, and starts Streamlit on `$PORT` (Render injects it; default 8501 locally). It runs as a
non-root user and sets `OCR_THREADS=1` for the 0.1 CPU free instance.

Free-tier facts: the instance spins down after about 15 minutes without traffic and cold-starts in about a minute;
512 MB RAM (the app plus RapidOCR peaked at about 310-330 MB RSS in local measurements; do not install Docling there);
no persistent disk (not needed, files are processed in memory). With 0.1 CPU, OCR of one photo can take tens of seconds
(an estimate: it was 1-3 s on a laptop core); the progress bar shows each file as it is read. The image grows by roughly
150-200 MB (onnxruntime, headless OpenCV, the 16 MB of models). Rebuild and redeploy after changing the Dockerfile.

### 1. Push the code to GitHub
The repo is `shivam911898/docextract`, with the `Dockerfile` in the repo root.
```powershell
cd C:\Users\shiva\Desktop\pro\freelance_biz\portfolio\doc-extractor
git init -b main
git add .
git commit -m "DocExtract"
git remote add origin https://github.com/shivam911898/docextract.git
git push -u origin main
```
`.env`, `.venv` and output files are already in `.gitignore`; `git status` should not list them. The `.gitattributes` file
only matters for Hugging Face (it routes PDFs/PNGs through LFS). Render does not need it: the image rebuilds `samples/`
itself, so skip `git lfs install` (or delete `.gitattributes`) and plain binaries are fine.

### 2. Create the web service
1. Sign in at <https://dashboard.render.com> (signing in with GitHub is the simplest).
2. **New** -> **Web Service**.
3. Source: connect the GitHub repo `shivam911898/docextract`, **or** use the **Public Git Repository** tab and paste
   `https://github.com/shivam911898/docextract` (no GitHub connection needed for a public repo).
4. Name: `docextract`. Branch: `main`. Leave Root Directory blank.
5. **Runtime: Docker** (Render finds the `Dockerfile`). **Instance Type: Free**.
6. **Environment Variables** (add them before the first deploy, or add later and Render redeploys):

   | Name | Value |
   |------|-------|
   | `GROQ_API_KEY` | free key from <https://console.groq.com/keys>. Treat it as a secret: enter it only here (or at the blueprint prompt), never in the repo |
   | `MAX_FILES` | `10` (already the default; lower it, e.g. `5`, to protect a busy public demo's free quota) |
   | `GROQ_TEXT_MODEL` (optional) | leave unset (default `openai/gpt-oss-120b`); `openai/gpt-oss-20b` is faster and cheaper. Confirm live ids with `GET https://api.groq.com/openai/v1/models` |
   | `GEMINI_API_KEY` (optional) | only if the demo must read scans and photos: also add `LLM_PROVIDER` = `gemini` (Groq reads text only, and wins by default when both keys exist) |

7. **Advanced** -> **Health Check Path**: `/_stcore/health` (Streamlit's built-in health endpoint).
8. **Create Web Service**. Render builds the image and deploys.

Do **not** set `GOOGLE_SERVICE_ACCOUNT_JSON` / `SHEET_ID` on a public demo: anyone could then append rows to your sheet.
If you skip the API key, the app still works in no-key demo mode (amber status pill; a heuristic parser reads text PDFs and
the OCR text of scans and photos at lower confidence).

Groq has no vision model, so scans and photos are read by the RapidOCR step baked into the image and the OCR text goes to
the Groq text model. On a Groq-only demo the sample run therefore shows 1 flagged document (the deliberately wrong
Greenleaf total) and the PNG receipt reads `HARBOR STREET GRILL`, total 90.68, marked `source: OCR`. If the OCR packages
are missing from an image, the pill says `OCR: not installed` and the PNG is flagged (`scanned image: needs a vision
provider (Gemini) or an OCR backend ...`). Set `OCR_BACKEND=none` to switch the OCR off on purpose. Docling (about 1.6 GB)
is not installed on the free instance.

### 3. Watch the build and test
1. Service page -> **Logs**. The first build takes a few minutes (installs `requirements.txt`).
2. Open `https://docextract.onrender.com` (the URL is shown at the top of the service page; if the name was taken Render
   adds a suffix, e.g. `docextract-ab12.onrender.com`).
3. Check: no-key banner is **gone** (green "AI mode: Groq" banner instead, footer shows the model) -> press **Try the sample documents** -> 9 processed,
   2 flagged on Groq (the Greenleaf invoice with the wrong total, plus the image-only PNG receipt, which Groq cannot read);
   1 flagged with a Gemini key and `LLM_PROVIDER=gemini`.
4. Upload a `.zip` of a few of your own PDFs/photos to confirm uploads work.
5. Use the URL in the Fiverr/Upwork gig, the README and the Loom.

### 4. Things to know
- **Free instances sleep** after about 15 minutes of inactivity; the first visitor waits about a minute for the cold start.
  Open the URL a few minutes before recording the Loom or sending it to a buyer.
- **Quota:** Groq's free tier is rate-limited (requests and tokens per minute and per day). `MAX_FILES` bounds a batch (the UI
  warns visitors and processes only the first N files) and the app retries 429/5xx with backoff, but a popular demo can still
  exhaust the daily quota. If that happens rows show "extraction error" and are flagged, nothing crashes. Watch usage in the
  Groq console.
- **Privacy:** uploaded files are processed in memory and never written to disk, but the extracted text is sent to Groq's API
  when a key is set (page images go to Google's Gemini API if you use Gemini). Say so in the demo and tell visitors to upload
  sample files only.
- **XSRF / CORS:** `.streamlit/config.toml` sets `enableXsrfProtection = false` and `enableCORS = false` (originally so uploads
  work inside an iframe). That is acceptable for this public demo, which has no login or per-user state. For a private
  deployment that enables the Google Sheets push, set both to `true`.
- **Updating:** `git push` to `main`; Render rebuilds and redeploys automatically.

### 5. Troubleshooting
| Symptom | Fix |
|---------|-----|
| Build fails while installing requirements | Read the **Logs** tab for the failing package; the `streamlit==` line in `requirements.txt` is the pin to check first. |
| Service stays "deploying" / health check fails | Confirm **Health Check Path** is exactly `/_stcore/health` and the service is the Docker runtime (the `CMD` binds `0.0.0.0:$PORT`). |
| Out of memory / instance restarts | The free tier has 512 MB. Do not install Docling there; lower `MAX_FILES`, set `OCR_MAX_PIXELS=700000` (smaller pages, less OCR memory), or `OCR_BACKEND=none` to drop OCR. |
| Build fails at the `rapidocr` step | The two-step OCR install in the `Dockerfile` needs Python below 3.13 (rapidocr-onnxruntime 1.4.4) and the pins in `requirements-ocr.txt`; the app runs without OCR, so you can also delete those lines. |
| Very slow first page load | Normal cold start after the free instance slept (about a minute). |
| Pill says "Demo mode" | Variable name must be exactly `GROQ_API_KEY` (or `GEMINI_API_KEY`); save and let Render redeploy. |
| Rows say `extraction error: Groq HTTP 404 ... model_not_found` | Groq retired the model id. List live ids with `GET https://api.groq.com/openai/v1/models` and set `GROQ_TEXT_MODEL`. |
| Rows say `extraction error: Groq HTTP 401` | The `GROQ_API_KEY` value is wrong or revoked. |
| Rows say `extraction error: ... 404` on Gemini | `GEMINI_MODEL` is set to a Gemini 2.x model. Unset it. |
| Images / scans say `scanned image: needs a vision provider` | No OCR backend is installed in that image (the pill shows `OCR: not installed`) or `OCR_BACKEND=none` is set. Rebuild with the OCR install from the `Dockerfile`, or use a Gemini key with `LLM_PROVIDER=gemini`. |
| An OCR'd row has a wrong digit | OCR can misread blurry photos. The row is capped at confidence 0.85 and flagged when sums disagree; compare with the original in the Preview tab. |

### Hugging Face Spaces (PRO only now)
Hugging Face Spaces is no longer a free host for server apps (checked 2026-10-30): the Space SDK choices are only
`gradio`, `docker` and `static`, creating a Docker or Gradio Space returns HTTP 402 ("requires a PRO subscription"), and the
`streamlit` SDK value is rejected. That is why the demo moved to Render. If you ever have a PRO account, use a Docker Space:
copy `deploy/HF_SPACE_README.md` to the Space repo as `README.md` (it sets `sdk: docker` and `app_port: 8501`) and push the
project with the `Dockerfile`; PDFs and PNGs must go through LFS or `hf upload`, which is what `.gitattributes` is for.

---

## B. Other Docker hosts (Railway, Fly, any VPS)

**Test the image locally**
```powershell
docker build -t docextract .
docker run --rm -p 8501:8501 -e GROQ_API_KEY=your-key docextract
# open http://localhost:8501
```

**Railway:** New Project -> Deploy from GitHub repo (it detects the Dockerfile) -> Variables: add `GROQ_API_KEY` ->
Settings -> Networking -> Generate Domain.

**VPS:** run the image behind HTTPS (Caddy, Nginx, Cloudflare): `docker run -d --restart unless-stopped -p 8501:8501 -e GROQ_API_KEY=... docextract`.

For a private deployment, enable XSRF protection again: set `enableXsrfProtection = true` and `enableCORS = true` in
`.streamlit/config.toml`.

---

## C. Updating after changes
```powershell
python verify.py          # must end with ALL CHECKS PASSED
git add -A; git commit -m "update"; git push origin main      # Render redeploys automatically
```
