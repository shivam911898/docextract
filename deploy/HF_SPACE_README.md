---
title: DocExtract
emoji: 🧾
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8501
pinned: false
license: mit
short_description: AI invoice and receipt data extraction to Excel
---

> Hugging Face Spaces requires a PRO subscription for Docker/Gradio Spaces as of Oct 2026, and the old `sdk: streamlit` is rejected,
> so the free public demo lives on Render (see `DEPLOY.md`). This file is only for someone with a PRO account: copy it to the
> Space repo as `README.md`. It replaces the front-matter that used to sit at the top of the project README
> (`sdk: streamlit`, `sdk_version: 1.66.1`, `python_version: "3.12"`, `app_file: app.py`); a Docker Space builds the project
> `Dockerfile` and serves Streamlit on port 8501.

# DocExtract - live demo

Drop in invoice and receipt PDFs, scans or phone photos (or one ZIP) and get one validated row per document, every line item,
and a separate **Needs review** sheet for anything that does not add up. Press **Try the sample documents** to see it work.

Source code and docs: see the project README.
