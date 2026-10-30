# Deployment image for Render (free tier) / Railway / Fly / any Docker host. See DEPLOY.md.
FROM python:3.12-slim

# OCR_THREADS=1: the free Render instance has 0.1 CPU, more onnxruntime threads would only fight over it.
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    OCR_THREADS=1

WORKDIR /app
COPY requirements.txt requirements-ocr.txt ./
# Lightweight OCR (RapidOCR on onnxruntime, about 16 MB of models, CPU only) so scans and phone photos are read even
# with a text-only provider such as Groq. Headless OpenCV avoids the libGL system dependency; see requirements-ocr.txt.
RUN pip install -r requirements.txt -r requirements-ocr.txt \
    && pip install --no-deps rapidocr-onnxruntime==1.4.4

COPY . .
# Regenerate the demo documents inside the image so the build never depends on binary files in git / LFS.
RUN useradd -m appuser && python make_samples.py && chown -R appuser /app
USER appuser

EXPOSE 8501
# Render / Railway inject $PORT; locally it falls back to 8501. GROQ_API_KEY (or GEMINI_API_KEY) comes from the host's env settings.
CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT:-8501} --server.address=0.0.0.0"]
